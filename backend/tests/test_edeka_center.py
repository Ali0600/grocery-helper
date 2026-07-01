"""Tests for the E center (EDEKA Center) flyer scraper — its own meinprospekt
publisher DE-3443181, kept a distinct chain from regular EDEKA."""
from app.scrapers.bonial import EdekaCenterScraper


def test_ecenter_publisher_config():
    e = EdekaCenterScraper()
    assert e.publisher_id == "DE-3443181"
    assert e.chain == "edeka_center"
    assert e.store_label == "E center"
    assert e.source == "flyer"
    assert e.publisher_page.endswith("/edekacenter-de")


def test_collect_brochures_filters_to_ecenter_publisher():
    """Only E center (DE-3443181) brochures are collected; an EDEKA one is skipped."""
    ec = EdekaCenterScraper()
    out: dict = {}
    node = {
        "ec": {"id": 11, "pageCount": 31, "validUntil": "x", "publisher": {"id": "DE-3443181"}},
        "edeka": {"id": 22, "pageCount": 20, "validUntil": "x", "publisher": {"id": "DE-220164"}},
    }
    ec._collect_brochures(node, out)
    assert "11" in out and "22" not in out


def test_sample_fallback_has_offers():
    assert len(EdekaCenterScraper()._sample()) >= 4
