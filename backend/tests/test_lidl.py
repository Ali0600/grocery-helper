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


# --- degrading must be loud, and it is not local to Lidl (2026-08-17) ------------------

def _failing_lidl(monkeypatch):
    from app.scrapers.lidl import LidlScraper

    s = LidlScraper()
    monkeypatch.setattr(s, "_fetch_live",
                        lambda plz: (_ for _ in ()).throw(RuntimeError("upstream down")))
    return s


def test_a_failed_lidl_scrape_serves_nothing_by_default(monkeypatch):
    """Sample prices are invented; an absent chain is at least honest about it."""
    result = _failing_lidl(monkeypatch).fetch("10713")
    assert result.offers == []
    assert "(sample)" not in result.store_name


def test_the_dev_flag_restores_lidl_samples(monkeypatch):
    monkeypatch.setattr("app.scrapers.lidl.settings.scrape_sample_fallback", True)
    result = _failing_lidl(monkeypatch).fetch("10713")
    assert len(result.offers) > 0
    assert result.store_name.endswith("(sample)"), "dev samples stay labelled as such"


def test_a_failed_lidl_scrape_says_that_it_also_costs_the_flyer_chains(monkeypatch, caplog):
    """The widest-blast-radius failure in the app, and it used to look local.

    The Lidl Plus lookup resolves the store COORDINATES, and `run_scrapers` gates every
    meinprospekt chain on `store.lat is not None` — so a Lidl failure silently skips all six
    flyer chains. That is true with or without sample data (this path has never returned
    lat/lng), which is exactly why the log has to say so: the symptom is six missing chains
    and the cause is one line about Lidl.
    """
    import logging

    with caplog.at_level(logging.WARNING, logger="app.scrapers.lidl"):
        result = _failing_lidl(monkeypatch).fetch("10713")

    assert result.lat is None and result.lng is None, "the cascade's precondition"
    rec = next(r for r in caplog.records if "Lidl live scrape failed" in r.getMessage())
    assert "coordinates" in rec.getMessage(), (
        "the log must name the knock-on, or six dark chains look like six separate faults"
    )
    assert rec.exc_info and rec.exc_info[0] is RuntimeError


def test_a_failed_lidl_scrape_is_counted(monkeypatch):
    from app import metrics

    before = metrics.snapshot()["scrape_failures"].get("lidl", 0)
    _failing_lidl(monkeypatch).fetch("10713")
    assert metrics.snapshot()["scrape_failures"].get("lidl", 0) == before + 1
