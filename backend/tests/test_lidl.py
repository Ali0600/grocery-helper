"""Tests for the Lidl Plus coupon parser (pure `_parse`, no live API)."""
from app.scrapers.lidl import LidlScraper


def test_parse_keeps_price_per_unit_separate_from_unit():
    offer = LidlScraper()._parse(
        {
            "id": "6f34",
            "title": "Ehrmann Almighurt",
            "brand": "EHRMANN",
            "priceBox": {"largePartNumeric": "0.29", "smallPartNumeric": "0.35"},
            "packaging": "Je 150 g (Max. 24 Stück)\nNormalpreis: 0.35\n1 kg = 2.33",
            "pricePerUnit": "1 kg = 1.93",
            "imageUrl": "https://static-coupons.example/x.jpg",
        }
    )
    assert offer.price_cents == 29
    assert offer.regular_price_cents == 35
    assert offer.unit == "Je 150 g (Max. 24 Stück)"  # packaging first line, unchanged
    assert offer.price_per_unit == "1 kg = 1.93"      # the sale per-unit, its own field
    assert offer.loyalty_note is None                  # coupons carry no card bonus here
