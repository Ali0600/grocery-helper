"""Tests for the Rossmann flyer scraper — the DRUGSTORE vertical's first chain
(the meinprospekt engine for publisher DE-1064), against a saved, trimmed /pages
fixture cut from the real weekly brochure so we don't hit the live, throttled API."""
import json
import os
from datetime import date, datetime, timedelta, timezone

from app.scrapers.bonial import RossmannScraper, _select_brochures
from app.verticals import CHAIN_VERTICAL

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "rossmann_pages.json")
VALID_FROM, VALID_TO = date(2026, 7, 26), date(2026, 7, 31)


def _offers():
    with open(FIXTURE, encoding="utf-8") as f:
        data = json.load(f)
    return RossmannScraper._offers_from_pages(data, VALID_FROM, VALID_TO)


def test_rossmann_publisher_config():
    r = RossmannScraper()
    assert r.publisher_id == "DE-1064"
    assert r.chain == "rossmann"
    assert r.store_label == "Rossmann"
    assert r.source == "flyer"
    assert r.publisher_page.endswith("/rossmann-de")


def test_rossmann_belongs_to_the_drugstore_vertical():
    # The whole point of adding it: it must NOT land in grocery, which is already at
    # 1630 offers against the 2000 cap.
    assert CHAIN_VERTICAL["rossmann"] == "drugstore"


def test_parses_priced_offers_with_the_shipped_engine():
    """Rossmann needed no parser change at all — this pins that."""
    offers = _offers()
    assert len(offers) == 6
    assert all(o.price_cents > 0 for o in offers)
    assert all(o.image_url and o.image_url.startswith("https://") for o in offers)


def test_per_offer_validity_beats_the_brochure_window():
    """Every offer in this real brochure carries a `publicationProfiles` window starting a
    day AFTER the brochure's own validFrom (Mon 27th vs Sun 26th) — the source lists the
    brochure before its offers start. Taking the brochure dates would advertise them a day
    early, so the parser must prefer the per-offer window."""
    offers = _offers()
    assert all(o.valid_from == date(2026, 7, 27) for o in offers)  # not VALID_FROM (the 26th)
    assert all(o.valid_to == VALID_TO for o in offers)


def test_maps_brand_name_and_grundpreis():
    o = next(o for o in _offers() if "Schauma" in o.name)
    assert o.brand == "Schauma"
    assert o.price_cents == 159
    assert o.price_per_unit == "1 l = 3.98"  # the €/l axis, so it sorts by unit price


def test_weekly_brochure_wins_over_the_long_campaign():
    """Rossmann runs a ~2-month "Schulaktion" alongside the weekly "Mein Drogeriemarkt".
    MAX_FLYER_DAYS must keep the weekly one — measured live: 23 pages vs 18."""
    now = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
    weekly = {
        "id": 1, "validFrom": (now - timedelta(days=2)).isoformat(),
        "validUntil": (now + timedelta(days=3)).isoformat(),
    }
    campaign = {
        "id": 2, "validFrom": (now - timedelta(days=23)).isoformat(),
        "validUntil": (now + timedelta(days=35)).isoformat(),
    }
    chosen = _select_brochures({"1": weekly, "2": campaign}, now, "rossmann")
    assert [c["id"] for c in chosen] == ["1"]


def test_the_three_brochure_shape_that_took_the_chain_down_on_2026_08_09():
    """The real windows from the failed 2026-08-09 06:00 UTC refresh, which served
    **rossmann=2**. Rossmann ran three brochures at once and each needs a different
    verdict, which is why this is pinned as a whole shape rather than three unit cases:

      * ``schulaktion`` — 18 pages, 57 days: dropped, it is not a weekly flyer.
      * ``supplement``  — 6 pages, 11 days, mid-life: valid, and worth 2 offers. Kept,
        but it must not be mistaken for the week's flyer.
      * ``weekly``      — 26 pages, starts 22:00 UTC that evening: **300 offers**.

    Only the third is the week. Selecting on validity alone picked the supplement and
    left the chain looking dark until the next Sunday.
    """
    now = datetime(2026, 8, 9, 7, tzinfo=timezone.utc)  # when the weekly refresh runs
    weekly = {"validFrom": "2026-08-09T22:00:00.000+0000",
              "validUntil": "2026-08-14T20:00:00.000+0000"}
    supplement = {"validFrom": "2026-08-02T22:00:00.000+0000",
                  "validUntil": "2026-08-14T20:00:00.000+0000"}
    schulaktion = {"validFrom": "2026-07-05T22:00:00.000+0000",
                   "validUntil": "2026-09-01T20:00:00.000+0000"}
    chosen = _select_brochures(
        {"weekly": weekly, "supplement": supplement, "schulaktion": schulaktion},
        now, "rossmann",
    )
    assert sorted(c["id"] for c in chosen) == ["supplement", "weekly"], (
        "the 26-page weekly carries 300 of the chain's 302 offers — losing it empties the "
        "drugstore vertical for a week"
    )


def test_collect_brochures_filters_to_rossmanns_publisher():
    """The page embeds competitors' brochures (dm, Müller, budni) — only DE-1064 counts."""
    out: dict = {}
    RossmannScraper()._collect_brochures(
        {
            "ross": {"id": 111, "pageCount": 23, "validUntil": "x", "publisher": {"id": "DE-1064"}},
            "dm": {"id": 222, "pageCount": 1, "validUntil": "x", "publisher": {"id": "DE-909"}},
        },
        out,
    )
    assert "111" in out and "222" not in out


def test_sample_fallback_is_classifiable():
    from app import categories

    for o in RossmannScraper()._sample():
        assert o.price_cents > 0
        assert categories.classify(o.name, o.brand, o.category_path) in categories.CATEGORIES
