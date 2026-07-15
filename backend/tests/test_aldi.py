"""Tests for the ALDI flyer scrapers.

ALDI is two independent companies with disjoint territories, each with its own meinprospekt
publisher — and unlike REWE/EDEKA, BOTH publisher pages are *national*: a live probe found
they serve the identical brochure to Berlin and Munich, ignoring the `location` cookie. So
the source will not stop us handing a Berlin user ALDI SÜD deals from ~300 km away; the
division is chosen in `run.py` from `store_locator.aldi_division`. These tests pin the
publisher config and the shared-chain contract that design depends on.
"""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Offer, Store
from app.scrapers import run as run_mod
from app.scrapers.base import ScrapedOffer, ScrapeResult
from app.scrapers.bonial import AldiNordScraper, AldiSuedScraper


def test_aldi_nord_publisher_config():
    a = AldiNordScraper()
    assert a.publisher_id == "DE-75"
    assert a.store_label == "ALDI Nord"
    assert a.source == "flyer"
    assert a.publisher_page.endswith("/aldinord-de")


def test_aldi_sued_publisher_config():
    a = AldiSuedScraper()
    assert a.publisher_id == "DE-77"
    assert a.store_label == "ALDI SÜD"
    assert a.source == "flyer"
    assert a.publisher_page.endswith("/aldisued-de")


def test_both_divisions_share_one_chain_but_are_distinct_publishers():
    """The two never coexist in a place, so there is nothing to compare (unlike EDEKA vs
    E center) — the app shows a single "Aldi" and the store name carries the division.
    Sharing the chain is only safe because exactly one division is scraped per PLZ."""
    nord, sued = AldiNordScraper(), AldiSuedScraper()
    assert nord.chain == sued.chain == "aldi"
    assert nord.publisher_id != sued.publisher_id
    assert nord.publisher_page != sued.publisher_page


def test_collect_brochures_filters_to_the_right_division():
    """The publisher page embeds competitors' brochures — including the *other* ALDI's, so
    a leaky filter here is exactly the wrong-region bug this design exists to prevent."""
    blob = {
        "props": [
            {"id": 1, "pageCount": 20, "validUntil": "2026-07-18", "publisher": {"id": "DE-75"}},
            {"id": 2, "pageCount": 20, "validUntil": "2026-07-18", "publisher": {"id": "DE-77"}},
            {"id": 3, "pageCount": 20, "validUntil": "2026-07-18", "publisher": {"id": "DE-1013"}},
        ]
    }
    nord: dict = {}
    AldiNordScraper()._collect_brochures(blob, nord)
    assert sorted(nord) == ["1"]

    sued: dict = {}
    AldiSuedScraper()._collect_brochures(blob, sued)
    assert sorted(sued) == ["2"]


def test_sample_fallback_is_labelled_and_priced():
    offers = AldiNordScraper()._sample()
    assert offers and all(o.price_cents > 0 for o in offers)
    assert all(o.external_id.startswith("al-") for o in offers)


# --- run_scrapers routes to the division that actually operates at the PLZ -------------
def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(bind=engine)


def _stub_everything_but_aldi(monkeypatch):
    """Neutralize the other five scrapers so only the ALDI routing is under test. Lidl still
    resolves the coordinates every flyer chain reuses."""
    def lidl_result(self, plz):
        return ScrapeResult(chain="lidl", store_name=f"Lidl {plz}", plz=plz,
                            lat=52.5, lng=13.4, offers=[])
    monkeypatch.setattr(run_mod.LidlScraper, "fetch", lidl_result)
    for cls in (run_mod.BonialScraper, run_mod.ReweScraper,
                run_mod.EdekaScraper, run_mod.EdekaCenterScraper):
        monkeypatch.setattr(
            cls, "fetch",
            lambda self, plz, lat, lng: ScrapeResult(
                chain=self.chain, store_name=f"{self.store_label} {plz}", plz=plz,
                lat=lat, lng=lng, offers=[]),
        )


def _aldi_fetch(label):
    def fetch(self, plz, lat, lng):
        return ScrapeResult(
            chain=self.chain, store_name=f"{self.store_label} {plz}", plz=plz, lat=lat, lng=lng,
            offers=[ScrapedOffer(external_id="x1", name=f"{label} Rispentomaten",
                                 price_cents=149)],
        )
    return fetch


@pytest.mark.parametrize(
    "division, want_store, other_label",
    [("nord", "ALDI Nord 10115", "SUED"), ("sued", "ALDI SÜD 10115", "NORD")],
)
def test_run_scrapers_scrapes_only_the_local_division(
    monkeypatch, division, want_store, other_label
):
    """The publishers are national, so BOTH would happily answer — only the division OSM
    says operates here may be stored."""
    _stub_everything_but_aldi(monkeypatch)
    monkeypatch.setattr(run_mod, "aldi_division", lambda lat, lng: division)
    monkeypatch.setattr(run_mod.AldiNordScraper, "fetch", _aldi_fetch("NORD"))
    monkeypatch.setattr(run_mod.AldiSuedScraper, "fetch", _aldi_fetch("SUED"))

    session = _session()
    run_mod.run_scrapers(session, "10115")

    store = session.scalar(select(Store).where(Store.chain == "aldi"))
    assert store is not None and store.name == want_store
    names = [o.name for o in session.scalars(select(Offer).where(Offer.store_id == store.id))]
    assert len(names) == 1
    assert other_label not in names[0]  # the wrong region must never be stored


def test_run_scrapers_skips_aldi_when_the_division_is_undetermined(monkeypatch, caplog):
    """Fail closed: guessing a region would look exactly like real data, so no ALDI store
    is created at all — and the skip is logged, never silent."""
    _stub_everything_but_aldi(monkeypatch)
    monkeypatch.setattr(run_mod, "aldi_division", lambda lat, lng: None)
    monkeypatch.setattr(run_mod.AldiNordScraper, "fetch", _aldi_fetch("NORD"))
    monkeypatch.setattr(run_mod.AldiSuedScraper, "fetch", _aldi_fetch("SUED"))

    session = _session()
    with caplog.at_level("WARNING"):
        run_mod.run_scrapers(session, "10115")

    assert session.scalar(select(Store).where(Store.chain == "aldi")) is None
    assert session.scalar(select(Store).where(Store.chain == "lidl")) is not None  # others OK
    assert any("aldi" in r.message.lower() for r in caplog.records)
