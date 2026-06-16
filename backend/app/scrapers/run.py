"""Scrape -> normalize -> persist orchestration.

Adding a new chain = add its scraper to SCRAPERS; everything downstream
(categorization, discount %, storage, API) is store-agnostic.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import categories
from ..models import Offer, Store
from .base import ScrapeResult
from .lidl import LidlScraper

SCRAPERS = [LidlScraper()]


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
        )
        session.add(store)
        session.flush()  # assign store.id
    return store


def run_scrapers(session: Session, plz: str) -> int:
    """Run all scrapers for a postal code, upserting offers. Returns rows touched."""
    total = 0
    for scraper in SCRAPERS:
        result = scraper.fetch(plz)
        store = _get_or_create_store(session, result)
        for raw in result.offers:
            offer = session.scalar(
                select(Offer).where(
                    Offer.store_id == store.id,
                    Offer.external_id == raw.external_id,
                )
            )
            is_new = offer is None
            if is_new:
                offer = Offer(store_id=store.id, external_id=raw.external_id)
            offer.name = raw.name
            offer.brand = raw.brand
            offer.category = categories.classify(raw.name)
            offer.price_cents = raw.price_cents
            offer.regular_price_cents = raw.regular_price_cents
            offer.discount_pct = _discount_pct(raw.price_cents, raw.regular_price_cents)
            offer.unit = raw.unit
            offer.image_url = raw.image_url
            offer.valid_from = raw.valid_from
            offer.valid_to = raw.valid_to
            if is_new:
                session.add(offer)
            total += 1
    session.commit()
    return total
