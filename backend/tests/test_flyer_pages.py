"""Capturing the brochure page scans, and persisting them for the app's flyer viewer.

The pages ride along on `/pages` responses the scrape already makes, so nothing here
should ever add an outbound request — see `MeinprospektScraper._fetch_live`.
"""
import json
import os
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import FlyerPage, Store
from app.scrapers import run as run_mod
from app.scrapers.base import ScrapedOffer, ScrapedPage, ScrapeResult
from app.scrapers.bonial import RossmannScraper, _page_image_url

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "rossmann_pages.json")
VALID_FROM, VALID_TO = date(2026, 8, 24), date(2026, 8, 29)


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(bind=engine)


def _store(session: Session, chain: str = "rossmann") -> Store:
    store = Store(chain=chain, name=f"{chain} 10115", plz="10115")
    session.add(store)
    session.flush()
    return store


def _page(url: str, brochure: str = "A", number: int = 0) -> ScrapedPage:
    return ScrapedPage(brochure_id=brochure, page_number=number, image_url=url,
                       valid_from=VALID_FROM, valid_to=VALID_TO)


# --- parsing ---------------------------------------------------------------------------
def test_pages_from_the_real_rossmann_brochure():
    """The one saved fixture that still carries `images` (the other three were trimmed)."""
    with open(FIXTURE, encoding="utf-8") as f:
        payload = json.load(f)

    pages = RossmannScraper._pages_from_pages(payload, "2501199999", VALID_FROM, VALID_TO)

    assert len(pages) == 1
    # Derive the expectation from the fixture rather than pasting a URL: a hardcoded one
    # would still "pass" if the picker silently started returning a different rung.
    want = next(i["url"] for i in payload["contents"][0]["images"] if i["size"] == "1600x1600")
    assert pages[0].image_url == want
    assert pages[0].brochure_id == "2501199999"
    assert (pages[0].valid_from, pages[0].valid_to) == (VALID_FROM, VALID_TO)


def test_page_number_is_the_contents_index_not_the_source_number():
    """Measured across publishers, the source's own `number` is 0-based on one, 1-based on
    another and absent on a third, while the array order always matches the image URL's
    `_page_N` suffix. So the index is the page number, and this is what pins that."""
    payload = {"contents": [
        {"number": 7, "images": [{"size": "1600x1600", "url": "first.jpg"}]},
        {"number": 9, "images": [{"size": "1600x1600", "url": "second.jpg"}]},
        {"images": [{"size": "1600x1600", "url": "third.jpg"}]},  # no `number` at all
    ]}

    pages = RossmannScraper._pages_from_pages(payload, "A", VALID_FROM, VALID_TO)

    assert [p.page_number for p in pages] == [0, 1, 2]
    assert [p.image_url for p in pages] == ["first.jpg", "second.jpg", "third.jpg"]


def test_picks_the_1600_rung_and_falls_back_to_the_largest():
    ladder = [{"size": "75x96", "url": "tiny"}, {"size": "768x1024", "url": "medium"},
              {"size": "1600x1600", "url": "chosen"}, {"size": "2800x2800", "url": "huge"}]
    assert _page_image_url(ladder) == "chosen"
    # An unfamiliar ladder must still yield a readable page, not nothing.
    assert _page_image_url([i for i in ladder if i["size"] != "1600x1600"]) == "huge"
    assert _page_image_url([{"size": "wat", "url": "only"}]) == "only"


@pytest.mark.parametrize("payload", [
    {}, {"contents": None}, {"contents": ["nope", 7]},
    {"contents": [{"images": "not-a-list"}]},
    {"contents": [{"images": [{"size": "1600x1600"}]}]},          # no url
    {"contents": [{"images": [{"size": "1600x1600", "url": ""}]}]},  # empty url
])
def test_junk_pages_are_skipped_never_raised_on(payload):
    """Junk-total, like `_parse_offer`: one bad page must not fail the chain to no offers."""
    assert RossmannScraper._pages_from_pages(payload, "A", VALID_FROM, VALID_TO) == []


def test_pages_do_not_dedupe_the_way_offers_do():
    """Two brochures carrying the SAME products still have their own scans. The offers
    collapse by external_id; the pages must not, or a supplement loses its booklet."""
    page = {"images": [{"size": "1600x1600", "url": "same.jpg"}],
            "offers": [{"content": {"id": "x", "products": [{"name": "Shampoo"}],
                                    "deals": [{"type": "SALES_PRICE", "max": 1.99}]}}]}
    payload = {"contents": [page]}

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return payload

    class _Client:
        def get(self, url, params=None, headers=None): return _Resp()

    scraper = RossmannScraper(client=_Client())
    scraper._current_brochures = lambda client, cookie="": [  # type: ignore[method-assign]
        {"id": "A", "valid_from": VALID_FROM, "valid_to": VALID_TO},
        {"id": "B", "valid_from": VALID_FROM, "valid_to": VALID_TO},
    ]

    offers, pages = scraper._fetch_live(52.5, 13.4, "10115")

    assert len(offers) == 1                                   # deduped across brochures
    assert [p.brochure_id for p in pages] == ["A", "B"]        # ... pages are not


# --- the fetch contract ------------------------------------------------------------------
def test_fetch_returns_pages_alongside_offers(monkeypatch):
    scraper = RossmannScraper()
    monkeypatch.setattr(
        RossmannScraper, "_fetch_live",
        lambda self, lat, lng, plz=None: (
            [ScrapedOffer(external_id="x", name="Shampoo", price_cents=199)],
            [_page("page0.jpg")],
        ),
    )

    result = scraper.fetch("10115", 52.5, 13.4)

    assert [p.image_url for p in result.pages] == ["page0.jpg"]


def test_a_failed_scrape_serves_no_pages(monkeypatch):
    """Same bargain as the invented prices: a chain that could not be scraped shows
    nothing. Last week's flyer presented as this week's is worse than an absent link."""
    monkeypatch.setattr(
        RossmannScraper, "_fetch_live",
        lambda self, lat, lng, plz=None: ([], [_page("stale.jpg")]),
    )

    result = RossmannScraper().fetch("10115", 52.5, 13.4)

    assert result.offers == [] or all(o.external_id.startswith("ro-") for o in result.offers)
    assert result.pages == []


# --- persistence -------------------------------------------------------------------------
def test_upsert_pages_replaces_rather_than_accumulating():
    """`/api/reset` deletes Offer rows and KEEPS Store rows, so a merging writer would pile
    week on week. Replacing is what retires last week's scans."""
    session = _session()
    store = _store(session)

    run_mod._upsert_pages(session, store, [_page("wk1-p0.jpg"), _page("wk1-p1.jpg", number=1)])
    run_mod._upsert_pages(session, store, [_page("wk2-p0.jpg")])

    rows = session.scalars(select(FlyerPage).where(FlyerPage.store_id == store.id)).all()
    assert [r.image_url for r in rows] == ["wk2-p0.jpg"]


def test_an_empty_scrape_clears_the_stored_pages():
    session = _session()
    store = _store(session)
    run_mod._upsert_pages(session, store, [_page("last-week.jpg")])

    run_mod._upsert_pages(session, store, [])

    assert session.scalars(select(FlyerPage)).all() == []


def test_pages_land_on_every_flyer_chain_and_on_no_other(monkeypatch):
    """Derive the expected chain set from `run.py` rather than listing it: a chain wired in
    later but missing an `_upsert_pages` call would otherwise go silently pageless.

    Sabotage: comment out any one of the seven call sites and this names the chain."""
    def flyer(self, plz, lat, lng):
        return ScrapeResult(
            chain=self.chain, store_name=f"{self.store_label} {plz}", plz=plz, lat=lat, lng=lng,
            offers=[ScrapedOffer(external_id="x", name="Butter", price_cents=199)],
            pages=[_page(f"{self.chain}-p0.jpg")],
        )

    monkeypatch.setattr(
        run_mod.LidlScraper, "fetch",
        lambda self, plz: ScrapeResult(chain="lidl", store_name=f"Lidl {plz}", plz=plz,
                                       lat=52.5, lng=13.4, offers=[]),
    )
    monkeypatch.setattr(
        run_mod.DmScraper, "fetch",
        lambda self, plz: ScrapeResult(chain="dm", store_name=f"dm {plz}", plz=plz,
                                       offers=[ScrapedOffer(external_id="d", name="Creme",
                                                            price_cents=99)]),
    )
    for cls in (run_mod.BonialScraper, run_mod.ReweScraper, run_mod.EdekaScraper,
                run_mod.EdekaCenterScraper, run_mod.PennyScraper, run_mod.RossmannScraper,
                run_mod.AldiNordScraper):
        monkeypatch.setattr(cls, "fetch", flyer)
    monkeypatch.setattr(run_mod, "aldi_division", lambda lat, lng: "nord")

    session = _session()
    run_mod.run_scrapers(session, "10115")

    stores = {s.id: s.chain for s in session.scalars(select(Store)).all()}
    with_pages = {stores[r.store_id] for r in session.scalars(select(FlyerPage)).all()}
    from app.verticals import CHAIN_VERTICAL
    expected = {c for c in CHAIN_VERTICAL if c != "dm"}
    assert with_pages == expected
    # dm has no brochure at all — its publisher serves an empty one, permanently.
    assert "dm" not in with_pages


def test_the_lidl_flyer_pages_land_on_the_same_store_row_as_its_coupons(monkeypatch):
    """Block 3 reuses the store object block 1 created, because a coupon Lidl and a flyer
    Lidl are one `(chain, plz)` row. If that ever split, the app would see two Lidls."""
    monkeypatch.setattr(
        run_mod.LidlScraper, "fetch",
        lambda self, plz: ScrapeResult(chain="lidl", store_name=f"Lidl {plz}", plz=plz,
                                       lat=52.5, lng=13.4,
                                       offers=[ScrapedOffer(external_id="c", name="Coupon",
                                                            price_cents=99)]),
    )
    monkeypatch.setattr(
        run_mod.DmScraper, "fetch",
        lambda self, plz: ScrapeResult(chain="dm", store_name="dm", plz=plz, offers=[]),
    )
    monkeypatch.setattr(
        run_mod.BonialScraper, "fetch",
        lambda self, plz, lat, lng: ScrapeResult(
            chain="lidl", store_name=f"Lidl {plz}", plz=plz, lat=lat, lng=lng,
            offers=[ScrapedOffer(external_id="f", name="Flyer", price_cents=149)],
            pages=[_page("lidl-p0.jpg")]),
    )
    for cls in (run_mod.ReweScraper, run_mod.EdekaScraper, run_mod.EdekaCenterScraper,
                run_mod.PennyScraper, run_mod.RossmannScraper):
        monkeypatch.setattr(
            cls, "fetch",
            lambda self, plz, lat, lng: ScrapeResult(
                chain=self.chain, store_name=f"{self.store_label} {plz}", plz=plz,
                lat=lat, lng=lng, offers=[]),
        )
    monkeypatch.setattr(run_mod, "aldi_division", lambda lat, lng: None)

    session = _session()
    run_mod.run_scrapers(session, "10115")

    lidl_stores = session.scalars(select(Store).where(Store.chain == "lidl")).all()
    assert len(lidl_stores) == 1
    pages = session.scalars(select(FlyerPage)).all()
    assert [p.store_id for p in pages] == [lidl_stores[0].id]
