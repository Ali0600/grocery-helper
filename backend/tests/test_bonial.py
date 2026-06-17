"""Tests for the Bonial flyer parser, run against a saved meinprospekt fixture
(a trimmed real /pages response) so we don't hit the live, throttled API."""
import json
import os
from datetime import date

from app.scrapers.bonial import BonialScraper, _loyalty_note, _parse_dt, _regular_from_label

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
