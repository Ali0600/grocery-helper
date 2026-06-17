"""Scrape -> normalize -> persist orchestration.

Two sources feed the same Lidl store, tagged by ``Offer.source``:
  - "coupon": Lidl Plus app coupons (clean, exact discounts; smaller set)
  - "flyer":  the weekly Aktionsprospekt via Bonial/meinprospekt (full breadth)

The Lidl Plus lookup also resolves the store's coordinates, which the flyer
scraper needs (its offers are location-gated).
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import categories
from ..models import Offer, Store
from .base import ScrapedOffer, ScrapeResult
from .bonial import BonialScraper
from .lidl import LidlScraper


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
    two feeds can't collide on the (store, external_id) unique key."""
    count = 0
    for raw in offers:
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
        offer.category = categories.classify(raw.name, raw.brand)
        offer.price_cents = raw.price_cents
        offer.regular_price_cents = raw.regular_price_cents
        offer.discount_pct = _discount_pct(raw.price_cents, raw.regular_price_cents)
        offer.unit = raw.unit
        offer.image_url = raw.image_url
        offer.valid_from = raw.valid_from
        offer.valid_to = raw.valid_to
        if is_new:
            session.add(offer)
        count += 1
    return count


def run_scrapers(session: Session, plz: str) -> int:
    """Scrape both sources for a postal code, upserting offers. Returns rows touched."""
    total = 0

    # 1. Lidl Plus coupons (also resolves the store + its coordinates).
    lidl = LidlScraper()
    result = lidl.fetch(plz)
    store = _get_or_create_store(session, result)
    total += _upsert(session, store, result.offers, source=lidl.source)

    # 2. Weekly Aktionsprospekt via Bonial, using the resolved coordinates.
    if store.lat is not None and store.lng is not None:
        flyer = BonialScraper().fetch(plz, store.lat, store.lng)
        total += _upsert(session, store, flyer.offers, source="flyer")

    session.commit()
    return total
