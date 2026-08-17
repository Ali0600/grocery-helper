"""Tests for the dm clearance scraper — the DRUGSTORE vertical's second chain, and the
first source that isn't a flyer or a coupon.

Runs against a trimmed fixture cut from the real Ausverkauf feed (dm rate-limits hard and
returns a bare 429 with no Retry-After, so the live API is never touched here). The
fixture deliberately carries one product per trap the parser exists to avoid.
"""
import json
import os

from app.scrapers.dm import DmScraper, _base_unit_price, _money_cents
from app.unit_price import unit_price_cents
from app.verticals import CHAIN_VERTICAL

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "dm_sellout.json")


def _products():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)["products"]


def _offers():
    scraper = DmScraper()
    return [o for o in (scraper._parse(p) for p in _products()) if o is not None]


def _by_name(fragment):
    return next(o for o in _offers() if fragment in o.name)


def test_dm_config():
    d = DmScraper()
    assert d.chain == "dm"
    assert d.store_label == "dm"
    # A third source value beside coupon/flyer — both of those would be a lie, and
    # /api/offers' `source` query pattern accepts this one.
    assert d.source == "clearance"


def test_dm_belongs_to_the_drugstore_vertical():
    """Grocery is the vertical with no headroom; dm must not land there."""
    assert CHAIN_VERTICAL["dm"] == "drugstore"


def test_online_only_items_are_skipped():
    """37 of the real 251 are "Nur Online" — not stocked in a branch, so not a deal you
    can walk in and buy. The fixture holds 3 of them."""
    products = _products()
    online_only = [
        p
        for p in products
        if any(
            e.get("alt") == "Nur Online Grafik" for e in (p["tileData"].get("eyecatchers") or [])
        )
    ]
    assert len(online_only) == 3, "fixture should carry online-only products to filter"
    assert len(_offers()) == len(products) - 3


def test_price_is_gross_never_the_net_of_vat_block():
    """THE trap: every product carries `price` (gross) AND `netPrice` (ex-VAT, at a rate
    that varies by product class). Reading netPrice under-reports by 7-16% — here it
    would say 6,68/10,88 instead of 7,95/12,95."""
    o = _by_name("Scalp Serum ProGrowth")
    assert o.price_cents == 795
    assert o.regular_price_cents == 1295
    assert o.price_cents != 668 and o.regular_price_cents != 1088  # the netPrice values


def test_every_offer_carries_a_real_discount():
    """dm clearance is the only feed where 100% of items have a struck price."""
    offers = _offers()
    assert offers
    for o in offers:
        assert o.regular_price_cents is not None
        assert o.regular_price_cents > o.price_cents


def test_grundpreis_reads_the_parenthesised_unit_price_not_the_pack_size():
    """"0,036 kg (81,94 € je 1 kg)" — the leading number is how much is in the box; the
    per-unit price is inside the brackets. Reading the wrong one gives €0.036/kg."""
    o = _by_name("Immun + Nacht")
    assert o.price_per_unit == "1 kg = 81.94"
    assert unit_price_cents(o.price_per_unit) == 8194


def test_sub_units_fold_onto_the_kg_l_axis_so_they_sort():
    """g/ml are converted to kg/l; without it these never rank in "Cheapest €/kg"."""
    assert _base_unit_price({"price": {"tileInfos": ["3 g (0,65 € je 1 g)"]}}) == "1 kg = 650.00"
    assert _base_unit_price({"price": {"tileInfos": ["2,5 ml (0,70 € je 1 ml)"]}}) == "1 l = 700.00"
    assert unit_price_cents("1 kg = 650.00") == 65000


def test_non_convertible_units_stay_displayable_but_unsortable():
    """St/Wl aren't on the kg|l axis, so they must render ("1,95 €/St") while returning
    None from the sort key — and keep the source's capitalisation, not "/st"."""
    st = _base_unit_price({"price": {"tileInfos": ["1 St (1,95 € je 1 St)"]}})
    assert st == "1 St = 1.95"
    assert unit_price_cents(st) is None
    assert _base_unit_price({"price": {"tileInfos": ["20 Wl (0,15 € je 1 Wl)"]}}) == "1 Wl = 0.15"


def test_missing_grundpreis_is_none_not_a_junk_string():
    """A non-null junk value here would suppress the serve-time derive fallback."""
    assert _base_unit_price({"price": {"tileInfos": []}}) is None
    assert _base_unit_price({"price": {"tileInfos": ["ab 3 Jahren"]}}) is None


def test_money_parsing_handles_german_separators():
    assert _money_cents("7,95 €") == 795
    assert _money_cents("1.234,56 €") == 123456
    assert _money_cents(None) is None
    assert _money_cents("kein Preis") is None


def test_clearance_offers_carry_no_validity_window():
    """dm publishes no end date — an item runs until it's sold out. NULL passes every
    serve-time validity filter; the weekly reset is what clears what's gone."""
    for o in _offers():
        assert o.valid_from is None
        assert o.valid_to is None


def test_maps_identity_image_and_source_taxonomy():
    o = _by_name("Scalp Serum ProGrowth")
    assert o.brand == "OGX"
    assert o.external_id == "3121559"  # dm's article number (`dan`), stable + short
    assert o.image_url and o.image_url.startswith("https://")
    assert o.category_path == ["Haarkur & Haarmaske"]
    assert o.raw is not None  # persisted for "View payload"


def test_external_id_fits_the_column_with_its_source_prefix():
    """`Offer.external_id` is String(160) and run.py stores "{source}:{external_id}"."""
    for o in _offers():
        assert len(f"clearance:{o.external_id}") <= 160


def test_unit_is_left_empty_rather_than_filled_with_the_pack_size():
    """`unit` is the classifier's caption signal (layer 2b) and shows on the card. dm has
    no caption, and the Grundpreis' "0,036 kg" fragment is neither — passing it would feed
    the classifier junk and render oddly."""
    assert all(o.unit is None for o in _offers())


def test_malformed_products_are_skipped_not_raised():
    """One bad element must not take the whole chain down to sample data."""
    scraper = DmScraper()
    assert scraper._parse({}) is None
    assert scraper._parse({"tileData": None}) is None
    assert scraper._parse("not a dict") is None
    assert scraper._parse({"dan": 1, "tileData": {"price": {}}}) is None  # no price


def test_sample_fallback_is_classifiable():
    from app import categories

    for o in DmScraper()._sample():
        assert o.price_cents > 0
        assert o.regular_price_cents > o.price_cents
        assert categories.classify(o.name, o.brand, o.category_path) in categories.CATEGORIES


def test_dm_still_runs_when_the_lidl_lookup_yields_no_coordinates(monkeypatch):
    """The structural reason dm sits OUTSIDE `run_scrapers`' coordinate guard.

    Every flyer chain is gated on `store.lat/lng`, which only the Lidl Plus lookup
    produces — so when Lidl degrades to samples (no coordinates), all of them are skipped.
    dm needs no coordinates at all (national prices), and gating it there would make an
    entire chain vanish with no error on exactly the runs that are already degraded.

    Sabotage: move the dm block inside the `if store.lat is not None` branch and this
    fails with 0 dm offers.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.db import Base
    from app.models import Offer, Store
    from app.scrapers import run as run_mod
    from app.scrapers.base import ScrapedOffer, ScrapeResult

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = Session(bind=engine)

    # Lidl fell back to samples: a result with NO lat/lng, exactly as `_sample()` gives.
    monkeypatch.setattr(
        run_mod.LidlScraper,
        "fetch",
        lambda self, plz: ScrapeResult(chain="lidl", store_name="Lidl (sample)", plz=plz),
    )
    monkeypatch.setattr(
        run_mod.DmScraper,
        "fetch",
        lambda self, plz: ScrapeResult(
            chain="dm",
            store_name=f"dm {plz}",
            plz=plz,
            offers=[
                ScrapedOffer(
                    external_id="1", name="Balea Shampoo", price_cents=145,
                    regular_price_cents=295, brand="Balea", category_path=["Shampoo"],
                )
            ],
        ),
    )

    run_mod.run_scrapers(session, "10115")

    dm_store = session.scalar(select(Store).where(Store.chain == "dm"))
    assert dm_store is not None, "dm store must be created even with no coordinates"
    dm_offers = session.scalars(select(Offer).where(Offer.store_id == dm_store.id)).all()
    assert len(dm_offers) == 1
    assert dm_offers[0].source == "clearance"


# --- dm degrades the same way (2026-08-17) --------------------------------------------

def _failing_dm(monkeypatch):
    from app.scrapers.dm import DmScraper

    s = DmScraper()
    monkeypatch.setattr(s, "_fetch_live",
                        lambda plz: (_ for _ in ()).throw(RuntimeError("upstream down")))
    return s


def test_a_failed_dm_scrape_serves_nothing_by_default(monkeypatch):
    """dm's clearance feed is the ONLY source of a dm price, so an invented one has no real
    counterpart anywhere to correct it — the last place fabricated data should survive."""
    result = _failing_dm(monkeypatch).fetch("10713")
    assert result.offers == []
    assert "(sample)" not in result.store_name


def test_the_dev_flag_restores_dm_samples(monkeypatch):
    monkeypatch.setattr("app.scrapers.dm.settings.scrape_sample_fallback", True)
    result = _failing_dm(monkeypatch).fetch("10713")
    assert len(result.offers) > 0
    assert result.store_name.endswith("(sample)")
