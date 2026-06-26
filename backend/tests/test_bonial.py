"""Tests for the Bonial flyer parser, run against a saved meinprospekt fixture
(a trimmed real /pages response) so we don't hit the live, throttled API."""
import json
import os
from datetime import date

from app.scrapers.bonial import (
    BonialScraper,
    _app_price,
    _loyalty_note,
    _offer_validity,
    _parse_dt,
    _regular_from_label,
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
