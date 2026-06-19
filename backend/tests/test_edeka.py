"""Tests for the EDEKA flyer scraper (the meinprospekt engine for publisher
DE-220164), run against a saved, trimmed /pages fixture so we don't hit the live,
throttled API."""
import json
import os
from datetime import date

from app.scrapers.bonial import EdekaScraper

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "edeka_pages.json")
VALID_FROM, VALID_TO = date(2026, 6, 14), date(2026, 6, 20)


def _offers():
    with open(FIXTURE, encoding="utf-8") as f:
        data = json.load(f)
    return EdekaScraper._offers_from_pages(data, VALID_FROM, VALID_TO)


def test_edeka_publisher_config():
    e = EdekaScraper()
    assert e.publisher_id == "DE-220164"
    assert e.chain == "edeka"
    assert e.store_label == "Edeka"
    assert e.source == "flyer"
    assert e.publisher_page.endswith("/edeka")


def test_parses_priced_offers_with_paths():
    offers = _offers()
    assert len(offers) == 6
    assert all(o.price_cents > 0 for o in offers)
    assert all(o.category_path for o in offers)  # EDEKA flyer carries categoryPaths
    assert all(o.valid_from == VALID_FROM and o.valid_to == VALID_TO for o in offers)


def test_maps_brand_and_name():
    o = next(o for o in _offers() if "Schweinenackensteaks" in o.name)
    assert o.brand == "Bauern Gut"
    assert o.price_cents == 699


def test_collect_brochures_filters_to_edeka_publisher():
    """Only EDEKA (DE-220164) brochures are collected; a REWE one is skipped, and a
    node whose `publisher` is a list (not a dict) must not crash."""
    edeka = EdekaScraper()
    out: dict = {}
    node = {
        "edeka": {"id": 11, "pageCount": 30, "validUntil": "x", "publisher": {"id": "DE-220164"}},
        "rewe": {"id": 22, "pageCount": 10, "validUntil": "x", "publisher": {"id": "DE-1062"}},
        "weird": {"id": 33, "pageCount": 5, "validUntil": "x", "publisher": [{"id": "DE-220164"}]},
    }
    edeka._collect_brochures(node, out)
    assert "11" in out and "22" not in out and "33" not in out


def test_sample_fallback_has_offers():
    assert len(EdekaScraper()._sample()) >= 4
