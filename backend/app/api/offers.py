from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, select

from ..categories import CATEGORIES
from ..core.config import settings
from ..db import SessionDep
from ..dedup import dedup_offers
from ..models import Offer, Store
from ..schemas import (
    CategoryCount,
    NearbyStoreOut,
    OfferOut,
    OptimizeRequest,
    OptimizeResponse,
    StoreOut,
)
from ..serializers import offer_to_out
from ..services.optimizer import optimize_basket

logger = logging.getLogger(__name__)

router = APIRouter(tags=["offers"])


@router.get("/offers", response_model=List[OfferOut])
def list_offers(
    session: SessionDep,
    category: Optional[str] = None,
    chain: Optional[str] = None,
    plz: Optional[str] = None,
    source: Optional[str] = Query(None, pattern="^(coupon|flyer)$"),
    min_discount: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query("discount", pattern="^(discount|price)$"),
    limit: int = Query(200, ge=1, le=2000),
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
    if source:
        stmt = stmt.where(Offer.source == source)
    if min_discount is not None:
        stmt = stmt.where(Offer.discount_pct >= min_discount)
    # Drop offers whose validity window has passed.
    stmt = stmt.where((Offer.valid_to.is_(None)) | (Offer.valid_to >= date.today()))
    # Collapse the same product repeated across brochures/sources, then sort +
    # limit in Python (dedup changes the count, so SQL LIMIT can't go first).
    rows = dedup_offers(session.scalars(stmt).all())
    if sort == "discount":
        rows.sort(key=lambda o: o.discount_pct if o.discount_pct is not None else -1.0, reverse=True)
    else:
        rows.sort(key=lambda o: o.price_cents)
    return [offer_to_out(o) for o in rows[:limit]]


@router.get("/offers/{offer_id}/payload")
def offer_payload(session: SessionDep, offer_id: int):
    """The full raw source payload an offer was scraped from (flyer `content` /
    Lidl coupon dict), for the app's "View payload" debug view. `payload` is null for
    offers scraped before the field existed or from sample-data fallback — re-scrape to
    capture it. Read-only; not part of OfferOut (too large for the list)."""
    offer = session.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")
    payload = json.loads(offer.raw_payload) if offer.raw_payload else None
    return {"id": offer.id, "source": offer.source, "payload": payload}


@router.get("/categories", response_model=List[CategoryCount])
def list_categories(session: SessionDep, plz: Optional[str] = None):
    """Categories that currently have offers, with counts (for filter chips).

    Counts distinct products (deduped) so the chip number matches the deduped list.
    """
    stmt = select(Offer).join(Store).where(
        (Offer.valid_to.is_(None)) | (Offer.valid_to >= date.today())
    )
    if plz:
        stmt = stmt.where(Store.plz == plz)
    counts = Counter(o.category for o in dedup_offers(session.scalars(stmt).all()))
    return [
        CategoryCount(category=slug, label=lbl, count=counts[slug])
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


@router.get("/scrape-stats")
def scrape_stats():
    """Count of outbound calls to the scraped sites (Lidl Plus / meinprospekt /
    Overpass), by source and host. Browsing the app makes **none** of these — they
    happen only when we scrape (cold start, set-PLZ) or resolve nearby stores.
    `recent` is the latest individual calls (newest first, with timestamps);
    counts reset on server restart.
    """
    from ..metrics import snapshot

    return snapshot()


@router.get("/nearby-stores", response_model=List[NearbyStoreOut])
def list_nearby_stores(
    session: SessionDep,
    plz: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    chain: Optional[str] = None,
):
    """Nearby stores around the PLZ (or explicit lat/lng), from OpenStreetMap.

    Without `chain`: the nearest store of each known chain (Lidl/REWE come back
    `active=True`; the rest are address-only placeholders the app can save). With
    `chain=<slug>`: every branch of that one chain near the PLZ, nearest first — the
    "Change branch" picker, so the user can pick the store actually near them rather
    than the one merely nearest the PLZ centroid. Empty list = mirrors unreachable.
    """
    from ..services.store_locator import CHAINS, chain_branches, nearby_stores, plz_centroid

    if lat is None or lng is None:
        target = plz or settings.default_plz
        # The "Change branch" picker centres on the PLZ's real centroid so it lists
        # the user's neighbourhood, not the scraped Lidl's (which can be a district
        # away). The general nearest-per-chain list keeps the scraped-store coords so
        # its Lidl/REWE stay consistent with the deals.
        if chain:
            centroid = plz_centroid(target)
            if centroid is not None:
                lat, lng = centroid
        if lat is None or lng is None:
            # A scraped store for this PLZ already has coordinates; reuse them.
            store = session.scalar(
                select(Store).where(Store.plz == target, Store.lat.is_not(None)).limit(1)
            )
            if store is not None:
                lat, lng = store.lat, store.lng
            else:
                lat, lng = _resolve_plz_coords(target)
    if lat is None or lng is None:
        return []  # couldn't locate the PLZ; app shows a "set your PLZ" message

    if chain:
        stores = chain_branches(chain, lat, lng) if chain in CHAINS else []
    else:
        stores = nearby_stores(lat, lng)
    return [NearbyStoreOut(**vars(s)) for s in stores]


def _resolve_plz_coords(plz: str) -> tuple[Optional[float], Optional[float]]:
    """Best-effort PLZ -> lat/lng via the Lidl Plus store autocomplete (the same
    lookup the scraper uses), for PLZs not yet scraped."""
    from ..http import tracked_client
    from ..scrapers.lidl import HEADERS as LIDL_HEADERS
    from ..scrapers.lidl import LidlScraper

    try:
        with tracked_client(timeout=20, headers=LIDL_HEADERS) as c:
            store = LidlScraper()._nearest_store(c, plz)
        loc = store.get("location") or {}
        return loc.get("latitude"), loc.get("longitude")
    except Exception:
        logger.warning("PLZ coord resolve failed for plz=%s", plz, exc_info=True)
        return None, None


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


@router.post("/reset")
def trigger_reset(session: SessionDep, plz: Optional[str] = None, token: Optional[str] = None):
    """Wipe every stored offer, then re-scrape `plz` from scratch (admin/maintenance).

    Unlike /api/scrape (which upserts in place), this first DELETEs all offers so stale
    rows the weekly scrape no longer touches are removed too, then re-scrapes. The
    immediate re-scrape re-populates the table, so the brief empty window self-heals; on a
    sample-data fallback the table comes back sparse (re-run when the source is reachable).
    Guarded by ADMIN_TOKEN only when that env var is set (otherwise open, like /api/scrape).
    """
    if settings.admin_token and token != settings.admin_token:
        raise HTTPException(status_code=403, detail="invalid or missing admin token")

    from ..scrapers.run import run_scrapers

    target = plz or settings.default_plz
    deleted = session.execute(delete(Offer)).rowcount
    session.commit()
    scraped = run_scrapers(session, target)
    stores = session.scalars(select(Store).where(Store.plz == target)).all()
    return {
        "plz": target,
        "deleted": deleted,
        "scraped": scraped,
        "stores": [
            StoreOut(id=s.id, chain=s.chain, name=s.name, plz=s.plz, market_code=s.market_code)
            for s in stores
        ],
    }
