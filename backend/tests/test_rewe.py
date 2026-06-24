"""Tests for the REWE flyer scraper (the meinprospekt engine for publisher
DE-1062), run against a saved, trimmed /pages fixture so we don't hit the live,
throttled API."""
import json
import os
from datetime import date

from app.scrapers.bonial import ReweScraper

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "rewe_pages.json")
VALID_FROM, VALID_TO = date(2026, 6, 14), date(2026, 6, 20)


def _offers():
    with open(FIXTURE, encoding="utf-8") as f:
        data = json.load(f)
    return ReweScraper._offers_from_pages(data, VALID_FROM, VALID_TO)


def test_rewe_publisher_config():
    r = ReweScraper()
    assert r.publisher_id == "DE-1062"
    assert r.chain == "rewe"
    assert r.store_label == "REWE"
    assert r.source == "flyer"
    assert r.publisher_page.endswith("/rewe-de")


def test_parses_priced_offers_with_paths():
    offers = _offers()
    assert len(offers) == 6
    assert all(o.price_cents > 0 for o in offers)
    assert all(o.category_path for o in offers)  # REWE always carries categoryPaths
    assert all(o.valid_from == VALID_FROM and o.valid_to == VALID_TO for o in offers)


def test_rewe_offers_have_no_regular_price():
    # REWE's "Dein Markt" flyer has no struck-through price -> no discount %.
    assert all(o.regular_price_cents is None for o in _offers())


def test_maps_brand_name_and_unit():
    o = next(o for o in _offers() if "Bacardi" in o.name)
    assert o.brand == "Bacardi"
    assert o.price_cents == 1099
    assert o.image_url and o.image_url.startswith("https://")


def test_collect_brochures_filters_publisher_and_guards_list():
    """Only REWE (DE-1062) brochures are collected; a Lidl one is skipped, and a
    node whose `publisher` is a list (not a dict) must not crash."""
    rewe = ReweScraper()
    out: dict = {}
    node = {
        "rewe": {"id": 111, "pageCount": 10, "validUntil": "x", "publisher": {"id": "DE-1062"}},
        "lidl": {"id": 222, "pageCount": 10, "validUntil": "x", "publisher": {"id": "DE-1013"}},
        "weird": {"id": 333, "pageCount": 10, "validUntil": "x", "publisher": [{"id": "DE-1062"}]},
    }
    rewe._collect_brochures(node, out)
    assert "111" in out          # REWE brochure collected
    assert "222" not in out      # Lidl brochure filtered out
    assert "333" not in out      # list-valued publisher guarded, not crashed


def test_dedup_across_brochures(monkeypatch):
    """Offers shared by two brochures collapse to one (keyed by external_id)."""
    with open(FIXTURE, encoding="utf-8") as f:
        pages = json.load(f)

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return pages

    class _FakeClient:
        def get(self, url, params=None, headers=None):
            return _FakeResp()

    rewe = ReweScraper(client=_FakeClient())
    monkeypatch.setattr(
        rewe, "_current_brochures",
        lambda client, cookie="": [
            {"id": "A", "valid_from": VALID_FROM, "valid_to": VALID_TO},
            {"id": "B", "valid_from": VALID_FROM, "valid_to": VALID_TO},
        ],
    )
    offers = rewe._fetch_live(52.52, 13.405, "10115")
    assert len(offers) == 6  # both "brochures" return the same 6 -> deduped


def test_sample_fallback_is_classifiable():
    from app import categories

    for o in ReweScraper()._sample():
        assert o.price_cents > 0
        assert categories.classify(o.name, o.brand, o.category_path) in categories.CATEGORIES
