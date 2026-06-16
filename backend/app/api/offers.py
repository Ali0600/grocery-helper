from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from ..categories import CATEGORIES, label
from ..core.config import settings
from ..db import SessionDep
from ..models import Offer, Store
from ..schemas import (
    CategoryCount,
    OfferOut,
    OptimizeRequest,
    OptimizeResponse,
    StoreOut,
)
from ..serializers import offer_to_out
from ..services.optimizer import optimize_basket

router = APIRouter(tags=["offers"])


@router.get("/offers", response_model=List[OfferOut])
def list_offers(
    session: SessionDep,
    category: Optional[str] = None,
    chain: Optional[str] = None,
    plz: Optional[str] = None,
    min_discount: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query("discount", pattern="^(discount|price)$"),
    limit: int = Query(100, ge=1, le=500),
):
    """List offers, filterable by category/chain/plz/min-discount.

    Default sort is by % discount descending — the headline feature.
    """
    stmt = select(Offer).join(Store)
    if category:
        stmt = stmt.where(Offer.category == category)
    if chain:
        stmt = stmt.where(Store.chain == chain)
    if plz:
        stmt = stmt.where(Store.plz == plz)
    if min_discount is not None:
        stmt = stmt.where(Offer.discount_pct >= min_discount)
    # Drop offers whose validity window has passed.
    stmt = stmt.where((Offer.valid_to.is_(None)) | (Offer.valid_to >= date.today()))
    # In SQLite/Postgres, DESC orders NULLs last, so null-discount items sink.
    stmt = stmt.order_by(
        Offer.discount_pct.desc() if sort == "discount" else Offer.price_cents.asc()
    ).limit(limit)
    return [offer_to_out(o) for o in session.scalars(stmt).all()]


@router.get("/categories", response_model=List[CategoryCount])
def list_categories(session: SessionDep, plz: Optional[str] = None):
    """Categories that currently have offers, with counts (for filter chips)."""
    stmt = select(Offer.category, func.count(Offer.id)).join(Store).group_by(
        Offer.category
    )
    if plz:
        stmt = stmt.where(Store.plz == plz)
    stmt = stmt.where((Offer.valid_to.is_(None)) | (Offer.valid_to >= date.today()))
    counts = {cat: cnt for cat, cnt in session.execute(stmt).all()}
    return [
        CategoryCount(category=slug, label=lbl, count=counts.get(slug, 0))
        for slug, lbl in CATEGORIES.items()
        if counts.get(slug, 0) > 0
    ]


@router.get("/stores", response_model=List[StoreOut])
def list_stores(session: SessionDep):
    stores = session.scalars(select(Store)).all()
    return [
        StoreOut(id=s.id, chain=s.chain, name=s.name, plz=s.plz, market_code=s.market_code)
        for s in stores
    ]


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, session: SessionDep):
    """Best basket across 1 or 2+ stores for the requested categories."""
    return optimize_basket(session, req)


@router.post("/scrape")
def trigger_scrape(session: SessionDep, plz: Optional[str] = None):
    """Scrape a postal code on demand and return the resolved store(s).

    Used by the app when the user sets/changes their PLZ. A store with a null
    `market_code` means no real store resolved (sample-data fallback).
    """
    from ..scrapers.run import run_scrapers

    target = plz or settings.default_plz
    scraped = run_scrapers(session, target)
    stores = session.scalars(select(Store).where(Store.plz == target)).all()
    return {
        "plz": target,
        "scraped": scraped,
        "stores": [
            StoreOut(id=s.id, chain=s.chain, name=s.name, plz=s.plz, market_code=s.market_code)
            for s in stores
        ],
    }


@router.post("/recategorize")
def trigger_recategorize(session: SessionDep):
    """Dev convenience: re-apply the classifier to all stored offers."""
    from ..scripts.recategorize import recategorize

    return {"recategorized": recategorize(session)}
