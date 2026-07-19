"""Tests for the Bonial flyer parser, run against a saved meinprospekt fixture
(a trimmed real /pages response) so we don't hit the live, throttled API."""
import json
import os
from datetime import date, datetime, timezone

import pytest

from app.scrapers.bonial import (
    BonialScraper,
    _app_price,
    _deal,
    _loyalty_note,
    _offer_validity,
    _parse_dt,
    _regular_from_label,
    _select_brochures,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "bonial_pages.json")
VALID_FROM, VALID_TO = date(2026, 6, 14), date(2026, 6, 20)


def _offers():
    with open(FIXTURE, encoding="utf-8") as f:
        data = json.load(f)
    return BonialScraper._offers_from_pages(data, VALID_FROM, VALID_TO)


def test_parses_all_priced_offers():
    offers = _offers()
    assert len(offers) == 4
    assert all(o.price_cents > 0 for o in offers)
    # offers carry their own validity window (from publicationProfiles), clamped within
    # the brochure — these fixture offers are the Mon–Sat trading week inside a Sun–Sat brochure.
    assert all(VALID_FROM <= o.valid_from and o.valid_to <= VALID_TO for o in offers)


def test_maps_name_brand_price_and_regular():
    o = next(o for o in _offers() if "Rostbratwurst" in o.name)
    assert o.name == "Eberswalder Rostbratwurst"
    assert o.brand == "Eberswalder"
    assert o.price_cents == 199
    assert o.regular_price_cents == 249  # SALES vs REGULAR -> 20% off
    assert o.unit == "Ohne Darm 300 g"
    assert o.image_url and o.image_url.startswith("https://")


def test_price_only_offer_has_no_regular():
    o = next(o for o in _offers() if "Rondo" in o.name)
    assert o.price_cents == 549
    assert o.regular_price_cents is None  # no regular, no badge -> no discount


def test_missing_brand_uses_product_name_only():
    o = next(o for o in _offers() if "Hexenkerze" in o.name)
    assert o.brand is None
    assert o.name == "Hexenkerze Vanille"


# Real Lidl shape (McCain Golden Longs): branded items print the struck-through price
# as an RRP/UVP deal, not REGULAR_PRICE — ~21% of flyer offers carry ONLY this.
_MCCAIN = {
    "id": "mc1",
    "image": "https://content-media.example/mccain.jpg",
    "deals": [
        {"type": "SALES_PRICE", "conditions": [{"other": "Je"}], "max": 2.99, "min": 2.99,
         "priceByBaseUnit": "", "description": ""},
        {"type": "RECOMMENDED_RETAIL_PRICE", "conditions": [], "max": 4.89, "min": 4.89,
         "priceByBaseUnit": "", "description": ""},
    ],
    "products": [{"brandName": "McCain", "name": "Golden Longs",
                  "description": [{"paragraph": "Tiefgefroren. 1 kg"}], "categoryPaths": []}],
}


def test_rrp_recovers_regular_price():
    o = BonialScraper._parse_offer(_MCCAIN, VALID_FROM, VALID_TO)
    assert o.price_cents == 299
    assert o.regular_price_cents == 489  # UVP -> the "statt" price -> ~39% badge


def test_regular_price_beats_rrp_when_both_present():
    both = json.loads(json.dumps(_MCCAIN))
    both["deals"].append({"type": "REGULAR_PRICE", "max": 3.99, "min": 3.99})
    o = BonialScraper._parse_offer(both, VALID_FROM, VALID_TO)
    assert o.regular_price_cents == 399  # the actual previous price wins over UVP


def test_inverted_rrp_is_ignored():
    # An RRP at/below the sale price would render a nonsense strike-through — fail closed.
    bad = json.loads(json.dumps(_MCCAIN))
    bad["deals"][1]["max"] = bad["deals"][1]["min"] = 2.99
    assert BonialScraper._parse_offer(bad, VALID_FROM, VALID_TO).regular_price_cents is None


# Real Lidl shape (Honigmelone): by-weight items flag the SALES_PRICE with a "kg-Preis"
# condition — the advertised price IS per kg — while priceByBaseUnit stays empty.
_MELONE = {
    "id": "hm1",
    "image": "https://content-media.example/melone.jpg",
    "deals": [
        {"type": "SALES_PRICE", "conditions": [{"other": "kg-Preis"}], "max": 1.19,
         "min": 1.19, "priceByBaseUnit": "", "description": "Deutschlands günstigster Preis"},
    ],
    "products": [{"name": "Honigmelone",
                  "description": [{"paragraph": "Spanien Ursprung: Spanien, Klasse I"}],
                  "categoryPaths": []}],
}


def test_kg_preis_condition_becomes_price_per_unit():
    o = BonialScraper._parse_offer(_MELONE, VALID_FROM, VALID_TO)
    # Grundpreis emitted in the Lidl-coupon shape unit_price_cents already parses.
    assert o.price_per_unit == "1 kg = 1.19"


def test_explicit_price_by_base_unit_beats_kg_preis():
    both = json.loads(json.dumps(_MELONE))
    both["deals"][0]["priceByBaseUnit"] = "1 kg = 1.19"
    o = BonialScraper._parse_offer(both, VALID_FROM, VALID_TO)
    assert o.price_per_unit == "1 kg = 1.19"  # the source's own string, not the synthesized one


def test_kg_preis_requires_exact_condition_not_substring():
    # A REWE travel offer carries "Festpreis" inside a long condition — must NOT match.
    hotel = json.loads(json.dumps(_MELONE))
    hotel["deals"][0]["conditions"] = [{"other": "Buchungscode: X, Ermäßigung/Festpreis "
                                        "und Vierbettzimmer ohne Zuschlag buchbar"}]
    assert BonialScraper._parse_offer(hotel, VALID_FROM, VALID_TO).price_per_unit is None
    # The trailing-asterisk variant ("kg-Preis*") still matches.
    star = json.loads(json.dumps(_MELONE))
    star["deals"][0]["conditions"] = [{"other": "kg-Preis*"}]
    assert BonialScraper._parse_offer(star, VALID_FROM, VALID_TO).price_per_unit == "1 kg = 1.19"


def test_regular_recovered_from_discount_badge():
    # "-0.50 €" off a 1.99 sale price implies a 2.49 regular price
    assert _regular_from_label(1.99, {"value": "0.50", "type": "DISCOUNT_AMOUNT"}) == 2.49
    # "-20 %" off 1.60 implies 2.00
    assert _regular_from_label(1.60, {"value": "20", "type": "DISCOUNT_PERCENTAGE"}) == 2.0
    assert _regular_from_label(1.99, None) is None
    assert _regular_from_label(1.99, {"value": "x", "type": "DISCOUNT_AMOUNT"}) is None


def test_parse_dt_handles_bonial_offset_format():
    dt = _parse_dt("2026-06-14T22:00:00.000+0000")
    assert dt is not None and dt.year == 2026 and dt.month == 6 and dt.day == 14
    assert _parse_dt(None) is None


# Real REWE shape: a card-bonus OTHER deal + a SALES_PRICE with priceByBaseUnit.
_BACARDI = {
    "id": "abc",
    "image": "https://content-media.example/main.jpg",
    "deals": [
        {"type": "OTHER", "conditions": [{"loyaltyProgram": {"isCard": True, "name": None}}],
         "max": 0, "min": 0, "description": "Carta Blanca Superior\n1,00 € Bonus"},
        {"type": "SALES_PRICE", "conditions": [], "max": 10.99, "min": 10.99,
         "priceByBaseUnit": "1 l = 15.70", "description": "Carta Blanca Superior"},
    ],
    "products": [{"brandName": "Bacardi", "name": "Carta Blanca Superior",
                  "description": [{"paragraph": "37,5% Vol. 0,7-l-Fl."}], "categoryPaths": []}],
}


def test_parse_offer_extracts_price_per_unit_and_loyalty_bonus():
    o = BonialScraper._parse_offer(_BACARDI, VALID_FROM, VALID_TO)
    assert o.price_per_unit == "1 l = 15.70"   # from the SALES_PRICE deal
    assert o.loyalty_note == "1,00 € Bonus"     # the €-line of the OTHER deal


def test_loyalty_note_extracts_clean_bonus_from_varied_shapes():
    # plain description, no conditions
    assert _loyalty_note({"deals": [{"type": "OTHER", "description": "0,10 € Bonus"}]}) == "0,10 € Bonus"
    # bonus carried in a condition's free-text `other`, blank description
    assert _loyalty_note({"deals": [{"type": "OTHER", "description": " ",
        "conditions": [{"other": "0,20 € Bonus"}]}]}) == "0,20 € Bonus"
    # noisy sentence -> just the canonical amount
    assert _loyalty_note({"deals": [{"type": "OTHER",
        "description": "Diesen Artikel zum Aktionspreis kaufen, 0,10 € Bonus in der REWE App sammeln"}]}) == "0,10 € Bonus"
    # amount on the same line as a variant name
    assert _loyalty_note({"deals": [{"type": "OTHER", "description": "2,00 € Bonus Espresso Martini"}]}) == "2,00 € Bonus"
    # no bonus present
    assert _loyalty_note({"deals": [{"type": "SALES_PRICE", "max": 1.99}]}) is None


def test_parse_offer_without_extras_is_none():
    content = {
        "id": "x",
        "deals": [{"type": "SALES_PRICE", "max": 1.99, "priceByBaseUnit": ""}],  # empty base unit
        "products": [{"name": "Plain Thing", "description": [], "categoryPaths": []}],
    }
    o = BonialScraper._parse_offer(content, VALID_FROM, VALID_TO)
    assert o.price_per_unit is None
    assert o.loyalty_note is None
    assert o.app_price_cents is None


# Real EDEKA shape: an app-coupon SPECIAL_PRICE alongside the regular SALES_PRICE.
_MILKA = {
    "id": "milka1",
    "image": "https://content-media.example/milka.jpg",
    "deals": [
        {"type": "SPECIAL_PRICE", "conditions": [{"other": "APP-PREIS"}],
         "max": 2.99, "min": 2.99, "priceByBaseUnit": "", "description": ""},
        {"type": "SALES_PRICE", "conditions": [], "max": 3.29, "min": 3.29,
         "priceByBaseUnit": "1 kg = 13.16-10.97", "description": ""},
    ],
    "products": [{"brandName": "Milka", "name": "Schokolade",
                  "description": [{"paragraph": "versch. Sorten 250/276/300 g"}], "categoryPaths": []}],
}


def test_parse_offer_extracts_app_price():
    o = BonialScraper._parse_offer(_MILKA, VALID_FROM, VALID_TO)
    assert o.price_cents == 329       # the regular SALES_PRICE stays the headline
    assert o.app_price_cents == 299   # the APP-PREIS SPECIAL_PRICE


# A day-limited (Thu–Sat) offer: its publicationProfiles window is narrower than the
# brochure. Timestamps are Berlin-midnight boundaries in UTC (summer = +0000 at 22:00);
# endDate is exclusive, so 06-27T22:00 -> last valid day Sat 06-27.
_WEEKEND = {
    "id": "wknd",
    "deals": [{"type": "SALES_PRICE", "max": 0.99, "min": 0.99}],
    "products": [{"name": "Avocado", "description": [], "categoryPaths": []}],
    "publicationProfiles": [{"validity": {
        "startDate": "2026-06-24T22:00:00.000+0000",  # Berlin Thu 06-25 00:00
        "endDate": "2026-06-27T22:00:00.000+0000",    # exclusive -> Sat 06-27
    }}],
}


def test_offer_validity_reads_publicationprofiles_in_berlin_dates():
    broc_from, broc_to = date(2026, 6, 22), date(2026, 6, 28)  # Mon..Sun brochure
    assert _offer_validity(_WEEKEND, broc_from, broc_to) == (date(2026, 6, 25), date(2026, 6, 27))
    # union of two overlapping profiles (Thu–Fri ∪ Fri–Sat = Thu–Sat), clamped to brochure
    content = {"publicationProfiles": [
        {"validity": {"startDate": "2026-06-24T22:00:00+0000", "endDate": "2026-06-26T22:00:00+0000"}},
        {"validity": {"startDate": "2026-06-25T22:00:00+0000", "endDate": "2026-06-27T22:00:00+0000"}},
    ]}
    assert _offer_validity(content, broc_from, broc_to) == (date(2026, 6, 25), date(2026, 6, 27))
    # no profiles -> None (caller keeps the brochure window)
    assert _offer_validity({"id": "x"}, broc_from, broc_to) is None


def test_parse_offer_adopts_per_offer_window_over_brochure():
    o = BonialScraper._parse_offer(_WEEKEND, date(2026, 6, 22), date(2026, 6, 28))
    assert o.valid_from == date(2026, 6, 25)  # Thu, not the brochure's Monday
    assert o.valid_to == date(2026, 6, 27)    # Sat
    # an offer with no publicationProfiles keeps the brochure dates
    plain = {"id": "p", "deals": [{"type": "SALES_PRICE", "max": 1.0}], "products": [{"name": "X"}]}
    o2 = BonialScraper._parse_offer(plain, VALID_FROM, VALID_TO)
    assert o2.valid_from == VALID_FROM and o2.valid_to == VALID_TO


def test_app_price_only_for_app_markers():
    def sp(marker):
        return {"deals": [{"type": "SPECIAL_PRICE", "max": 2.49, "conditions": [{"other": marker}]}]}

    assert _app_price(sp("APP-PREIS")) == 249
    assert _app_price(sp("Nur mit App")) == 249               # case-insensitive
    assert _app_price(sp("Exklusiv mit der App")) == 249
    assert _app_price(sp("NUR MIT PAYBACK")) is None          # loyalty program, not the app
    assert _app_price(sp("6 FÜR")) is None                    # multibuy
    assert _app_price(sp("AB 2 KISTEN, JE KISTE")) is None    # bulk
    # no SPECIAL_PRICE deal, or one with no condition marker
    assert _app_price({"deals": [{"type": "SALES_PRICE", "max": 1.99}]}) is None
    assert _app_price({"deals": [{"type": "SPECIAL_PRICE", "max": 1.99, "conditions": []}]}) is None


def test_deal_reads_max_and_guards_malformed():
    # Happy path: the numeric `max` of the first matching deal type.
    assert _deal({"deals": [{"type": "SALES_PRICE", "max": 1.99}]}, "SALES_PRICE") == 1.99
    # A malformed `max` is skipped (degrade, don't 500) — parity with _app_price /
    # _regular_from_label; a later well-formed deal of the same type still wins.
    content = {"deals": [{"type": "SALES_PRICE", "max": "n/a"}, {"type": "SALES_PRICE", "max": 2.49}]}
    assert _deal(content, "SALES_PRICE") == 2.49
    # All malformed, or no matching deal type -> None.
    assert _deal({"deals": [{"type": "SALES_PRICE", "max": "x"}]}, "SALES_PRICE") is None
    assert _deal({"deals": [{"type": "REGULAR_PRICE", "max": 3.0}]}, "SALES_PRICE") is None


# -- brochure selection: which weekly brochure(s) to scrape ------------------
# Berlin-midnight boundaries are 22:00 UTC in summer; a weekly brochure runs Sun→Sat.
_WK1 = {"validFrom": "2026-07-05T22:00:00.000+0000", "validUntil": "2026-07-11T21:00:00.000+0000"}
_WK2 = {"validFrom": "2026-07-12T22:00:00.000+0000", "validUntil": "2026-07-18T21:00:00.000+0000"}
_SUNDAY = datetime(2026, 7, 5, 6, tzinfo=timezone.utc)  # before WK1 starts (between weeks)
_WEDNESDAY = datetime(2026, 7, 8, 10, tzinfo=timezone.utc)  # inside WK1


def test_select_prefers_the_currently_active_brochure():
    chosen = _select_brochures({"a": _WK1, "b": _WK2}, _WEDNESDAY, "edeka")
    assert [c["id"] for c in chosen] == ["a"]


def test_select_falls_back_to_nearest_upcoming_between_weeks():
    # Sunday: nothing active yet, so serve next week's (already published), not the week after.
    chosen = _select_brochures({"a": _WK1, "b": _WK2}, _SUNDAY, "edeka")
    assert [c["id"] for c in chosen] == ["a"]
    assert chosen[0]["valid_from"] == date(2026, 7, 5)


def test_select_ignores_long_running_non_weekly_brochure():
    perma = {"validFrom": "2026-07-04T22:00:00.000+0000", "validUntil": "2026-12-31T19:00:00.000+0000"}
    chosen = _select_brochures({"perma": perma, "a": _WK1}, _SUNDAY, "lidl")
    assert [c["id"] for c in chosen] == ["a"]


def test_select_raises_when_nothing_active_or_soon():
    old = {"validFrom": "2026-06-22T22:00:00.000+0000", "validUntil": "2026-06-28T21:00:00.000+0000"}
    far = {"validFrom": "2026-08-01T22:00:00.000+0000", "validUntil": "2026-08-07T21:00:00.000+0000"}
    with pytest.raises(RuntimeError, match="no active weekly brochure"):
        _select_brochures({"old": old, "far": far}, _SUNDAY, "rewe")


# --- thin-response retry ------------------------------------------------------
# The aggregators soft-throttle a burst by answering **HTTP 200 with less content** — an empty
# brochure list, or a brochure that parses to zero offers. Nothing "fails", so the transport
# retry in tracked_client never sees it and the chain silently degrades to sample data. Observed
# in production 2026-07-19: lidl/rewe/aldi fell back on one attempt, the identical request
# returned the full list ten minutes later. `fetch` therefore asks once more before believing an
# empty answer. (conftest sets SCRAPE_THIN_RETRY_S=0 so this never actually sleeps.)


class _CountingScraper(BonialScraper):
    """Drives `fetch` without any network: `_fetch_live` replays a scripted result per attempt."""

    def __init__(self, script):
        super().__init__()
        self.script = list(script)
        self.calls = 0

    def _fetch_live(self, lat, lng, plz=None):
        self.calls += 1
        outcome = self.script[min(self.calls - 1, len(self.script) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def _sample(self):
        return ["SAMPLE"]


def _fake_offer():
    return object()


def test_empty_brochure_list_is_retried_once_and_succeeds():
    real = [_fake_offer()]
    s = _CountingScraper([RuntimeError("no active weekly brochure for rewe"), real])

    result = s.fetch("10713", 52.5, 13.4)

    assert s.calls == 2, "an empty answer must be re-asked, not believed"
    assert result.offers == real
    assert result.offers != ["SAMPLE"]


def test_brochure_that_parses_to_zero_offers_is_also_retried():
    # The lidl shape: a brochure WAS found and fetched 200, but yielded no offers.
    real = [_fake_offer()]
    s = _CountingScraper([[], real])

    result = s.fetch("10713", 52.5, 13.4)

    assert s.calls == 2
    assert result.offers == real


def test_still_empty_on_the_retry_falls_back_to_samples():
    s = _CountingScraper([[], []])

    result = s.fetch("10713", 52.5, 13.4)

    assert s.calls == 2
    assert result.offers == ["SAMPLE"]


def test_http_error_is_NOT_retried():
    """A 403 is a hard block that retrying only worsens, and 5xx/429 already retried in
    tracked_client. Only our own 'came back empty' RuntimeError earns a second attempt."""
    import httpx

    err = httpx.HTTPStatusError("403", request=httpx.Request("GET", "https://x"),
                                response=httpx.Response(403))
    s = _CountingScraper([err, [_fake_offer()]])

    result = s.fetch("10713", 52.5, 13.4)

    assert s.calls == 1, "an HTTP error must go straight to samples, not re-hit a blocked host"
    assert result.offers == ["SAMPLE"]


def test_retry_waits_the_configured_pause(monkeypatch):
    slept = []
    monkeypatch.setattr("app.scrapers.bonial.time.sleep", lambda s: slept.append(s))
    monkeypatch.setattr("app.scrapers.bonial.settings.scrape_thin_retry_s", 8.0)
    s = _CountingScraper([[], [_fake_offer()]])

    s.fetch("10713", 52.5, 13.4)

    assert slept == [8.0], "re-asking instantly would just hit the same throttled response"
