"""Tests for the Bonial flyer parser, run against a saved meinprospekt fixture
(a trimmed real /pages response) so we don't hit the live, throttled API."""
import json
import os
from datetime import date

from app.scrapers.bonial import BonialScraper, _parse_dt, _regular_from_label

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
    assert all(o.valid_from == VALID_FROM and o.valid_to == VALID_TO for o in offers)


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
