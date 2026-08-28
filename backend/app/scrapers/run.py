"""Scrape -> normalize -> persist orchestration.

Three sources, tagged by ``Offer.source``:
  - "coupon":    Lidl Plus app coupons (clean, exact discounts; smaller set)
  - "flyer":     the weekly Aktionsprospekt via Bonial/meinprospekt (full breadth)
  - "clearance": dm's Ausverkauf, from its product-search API (see ``dm.py``)

REWE, EDEKA, E center, ALDI and Rossmann are further chains (each its own store) from the
same meinprospekt "flyer" pipeline. The Lidl Plus lookup resolves the postal code's
coordinates, which every flyer scraper needs (their offers are location-gated); the others
reuse them, since a Berlin PLZ resolves to one brochure region.

**dm is the exception and runs before that guard**: its prices are national, so it needs
no coordinates, and gating it on the Lidl lookup would make a whole chain disappear
without error whenever Lidl degrades to samples.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import categories, metrics
from ..dedup import dedup_scraped
from ..models import FlyerPage, Offer, Store
from ..services.store_locator import aldi_division
from .base import ScrapedOffer, ScrapedPage, ScrapeResult
from .bonial import (
    AldiNordScraper,
    AldiSuedScraper,
    BonialScraper,
    EdekaCenterScraper,
    EdekaScraper,
    PennyScraper,
    ReweScraper,
    RossmannScraper,
)
from .dm import DmScraper
from .lidl import LidlScraper

logger = logging.getLogger(__name__)


def _discount_pct(price: int, regular: Optional[int]) -> Optional[float]:
    if not regular or regular <= 0 or price >= regular:
        return None
    return round((regular - price) / regular * 100, 1)


def _get_or_create_store(session: Session, result: ScrapeResult) -> Store:
    store = session.scalar(
        select(Store).where(Store.chain == result.chain, Store.plz == result.plz)
    )
    if store is None:
        store = Store(
            chain=result.chain,
            name=result.store_name,
            plz=result.plz,
            market_code=result.market_code,
            lat=result.lat,
            lng=result.lng,
        )
        session.add(store)
        session.flush()  # assign store.id
    else:
        if result.lat is not None:
            store.lat = result.lat
        if result.lng is not None:
            store.lng = result.lng
    return store


def _upsert(session: Session, store: Store, offers: List[ScrapedOffer], source: str) -> int:
    """Upsert offers for one source. external_id is namespaced by source so the
    two feeds can't collide on the (store, external_id) unique key.

    Offers are first collapsed by (normalized name, price) so the same product
    surfaced across a chain's overlapping brochures is stored once — making the row
    count deterministic regardless of how many duplicate brochures the publisher page
    served for the scraping host's IP (see `dedup_scraped`)."""
    count = 0
    for raw in dedup_scraped(offers):
        ext = f"{source}:{raw.external_id}"
        offer = session.scalar(
            select(Offer).where(Offer.store_id == store.id, Offer.external_id == ext)
        )
        is_new = offer is None
        if is_new:
            offer = Offer(store_id=store.id, external_id=ext)
        offer.source = source
        offer.name = raw.name
        offer.brand = raw.brand
        offer.category_path = json.dumps(raw.category_path) if raw.category_path else None
        # raw.unit is the flyer caption — it states what the product IS where the name lies.
        offer.category = categories.classify(raw.name, raw.brand, raw.category_path, raw.unit)
        offer.price_cents = raw.price_cents
        offer.regular_price_cents = raw.regular_price_cents
        offer.discount_pct = _discount_pct(raw.price_cents, raw.regular_price_cents)
        offer.unit = raw.unit
        offer.price_per_unit = raw.price_per_unit
        offer.loyalty_note = raw.loyalty_note
        offer.app_price_cents = raw.app_price_cents
        offer.image_url = raw.image_url
        offer.valid_from = raw.valid_from
        offer.valid_to = raw.valid_to
        offer.raw_payload = json.dumps(raw.raw, ensure_ascii=False) if raw.raw else None
        if is_new:
            session.add(offer)
        count += 1
    return count


def _upsert_pages(session: Session, store: Store, pages: List[ScrapedPage]) -> None:
    """Replace this store's flyer pages with the ones THIS scrape captured.

    Delete-then-insert, not an upsert, and that is the whole design. `/api/reset` deletes
    `Offer` rows but keeps `Store` rows, so a merging writer would leave last week's pages
    hanging off the store with nothing to retire them. Replacing also means a failed scrape
    (`pages == []`) clears them, which matches what we already decided about invented
    prices: showing nothing is honest, showing last week's flyer as this week's is not.

    Returns None deliberately — `run_scrapers`' running total is the OFFER count the API
    reports as "rows scraped", and folding pages into it would silently inflate it.
    """
    session.execute(delete(FlyerPage).where(FlyerPage.store_id == store.id))
    for page in pages:
        session.add(
            FlyerPage(
                store_id=store.id,
                brochure_id=page.brochure_id,
                page_number=page.page_number,
                image_url=page.image_url,
                valid_from=page.valid_from,
                valid_to=page.valid_to,
            )
        )


def run_scrapers(session: Session, plz: str) -> int:
    """Scrape both sources for a postal code, upserting offers. Returns rows touched."""
    total = 0

    # 1. Lidl Plus coupons (also resolves the store + its coordinates).
    lidl = LidlScraper()
    result = lidl.fetch(plz)
    store = _get_or_create_store(session, result)
    total += _upsert(session, store, result.offers, source=lidl.source)

    # 2. dm's Ausverkauf (clearance) — the DRUGSTORE vertical's catalog-sourced chain.
    #    Deliberately OUTSIDE the coordinate guard below: dm's prices are national, so it
    #    needs no lat/lng, and putting it inside would silently drop dm on any run where
    #    the Lidl Plus lookup fell back to samples (no coordinates) — a whole chain
    #    vanishing with no error, exactly the failure mode the ALDI skip had.
    dm_scraper = DmScraper()
    dm_result = dm_scraper.fetch(plz)
    dm_store = _get_or_create_store(session, dm_result)
    total += _upsert(session, dm_store, dm_result.offers, source=dm_scraper.source)

    # 3. Weekly Aktionsprospekt via meinprospekt, using the resolved coordinates.
    if store.lat is not None and store.lng is not None:
        flyer = BonialScraper().fetch(plz, store.lat, store.lng)
        total += _upsert(session, store, flyer.offers, source="flyer")
        # `store` here is the Lidl row from step 1 — same (chain, plz), so the coupon
        # store and the flyer store are one row. Steps 1 and 2 get no _upsert_pages call:
        # coupons and dm clearance have no brochure to scan.
        _upsert_pages(session, store, flyer.pages)

        # 4. REWE's weekly flyer (same pipeline, second chain + store).
        rewe_scraper = ReweScraper()
        rewe = rewe_scraper.fetch(plz, store.lat, store.lng)
        rewe_store = _get_or_create_store(session, rewe)
        total += _upsert(session, rewe_store, rewe.offers, source=rewe_scraper.source)
        _upsert_pages(session, rewe_store, rewe.pages)

        # 5. EDEKA's weekly flyer (same pipeline, third chain + store).
        edeka_scraper = EdekaScraper()
        edeka = edeka_scraper.fetch(plz, store.lat, store.lng)
        edeka_store = _get_or_create_store(session, edeka)
        total += _upsert(session, edeka_store, edeka.offers, source=edeka_scraper.source)
        _upsert_pages(session, edeka_store, edeka.pages)

        # 6. E center (EDEKA's hypermarket format) — a separate publisher, chain + store.
        ecenter_scraper = EdekaCenterScraper()
        ecenter = ecenter_scraper.fetch(plz, store.lat, store.lng)
        ecenter_store = _get_or_create_store(session, ecenter)
        total += _upsert(session, ecenter_store, ecenter.offers, source=ecenter_scraper.source)
        _upsert_pages(session, ecenter_store, ecenter.pages)

        # 7. Penny — the sixth grocery chain. Regional like REWE/EDEKA, so it reuses the same
        # Lidl-resolved coordinates and the `location` cookie does the rest; no division to
        # resolve as ALDI needs.
        penny_scraper = PennyScraper()
        penny = penny_scraper.fetch(plz, store.lat, store.lng)
        penny_store = _get_or_create_store(session, penny)
        total += _upsert(session, penny_store, penny.offers, source=penny_scraper.source)
        _upsert_pages(session, penny_store, penny.pages)

        # 8. ALDI — two independent companies with disjoint territories, and BOTH their
        #    publishers are national, so the feed can't tell us which one applies here.
        #    Ask OSM which division actually operates at these coordinates; if that can't
        #    be answered, skip ALDI rather than guess — a missing chain is visible, whereas
        #    wrong-region deals look exactly like real ones.
        division = aldi_division(store.lat, store.lng)
        if division is None:
            logger.warning(
                "aldi: could not determine Nord/SÜD for plz=%s; skipping ALDI this run", plz
            )
            # Count it, exactly like a scraper that raised. This skip is a DEGRADED RUN — the
            # chain serves nothing — but for a long time it was the one degradation that left
            # `/api/scrape-stats` reading clean, because the failure happens BEFORE any scraper
            # is constructed and so never reaches the recording in `bonial.py`. Observed twice:
            # a whole flyer week with 5 grocery chains and `scrape_failures: {}` beside it,
            # while three Overpass mirrors had been tried. The data gate caught it both times
            # (`chains >= 6`), so this does not change what is DETECTED — it changes whether the
            # dashboard can say why, which is the difference between a red gate and a diagnosis.
            metrics.record_scrape_failure("aldi", "aldi_division_unresolved")
        else:
            aldi_scraper = AldiNordScraper() if division == "nord" else AldiSuedScraper()
            aldi = aldi_scraper.fetch(plz, store.lat, store.lng)
            aldi_store = _get_or_create_store(session, aldi)
            total += _upsert(session, aldi_store, aldi.offers, source=aldi_scraper.source)
            _upsert_pages(session, aldi_store, aldi.pages)

        # 9. Rossmann — the DRUGSTORE vertical. Scraped in the same run as the grocery
        #    chains (one scrape fills both verticals); which vertical it lands in is decided
        #    at serve time by `app/verticals.py`, from its chain slug.
        rossmann_scraper = RossmannScraper()
        rossmann = rossmann_scraper.fetch(plz, store.lat, store.lng)
        rossmann_store = _get_or_create_store(session, rossmann)
        total += _upsert(session, rossmann_store, rossmann.offers, source=rossmann_scraper.source)
        _upsert_pages(session, rossmann_store, rossmann.pages)

    session.commit()
    return total
