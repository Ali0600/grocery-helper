from __future__ import annotations

import json
import logging
import secrets
import time
from collections import Counter
from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from sqlalchemy import delete, false, select
from sqlalchemy.orm import selectinload

from .. import categories
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
from ..throttle import RateLimiter
from ..validity import berlin_today
from ..verticals import VERTICALS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["offers"])

# Scope a listing to one section of the app (grocery / drinks / drugstore). Built from
# VERTICALS so a new section needs no edit here, and matched as a pattern — like `source`
# above — so an unknown value is a 422 rather than silently returning EVERY chain (a typo
# that quietly widens a filter is the "gate evaluating less than it claims" trap). That
# 422 is also why a new section ships backend-first: an app asking for one this deploy
# doesn't know gets an error, not a fallback.
#
# **Omitting it now means GROCERY, not "every chain."** It used to mean no filter, which
# was fine at 1913/2000 but stopped being so when dm landed: measured 2026-07-30, all
# chains together is 2127, so an unfiltered read would silently truncate — the "gate looks
# green while evaluating less than it claims" trap, in data form. Since 2026-08-18 grocery
# also *excludes* the drink categories, so an old client sees no drinks; that is the same
# bargain as above — it has no UI for the section either way, and grocery alone had reached
# 1926 of the 2000 cap before the carve-out.
#
# Grocery is the right default rather than a raised cap because the ONLY clients that omit
# the param are app builds older than the vertical release. Those predate Drugstore
# entirely: they have no home screen, no drugstore chips and no way to reach that section,
# yet they were being served Rossmann (and would now be served dm) mixed into a grocery
# list. Defaulting to grocery gives them exactly what they were built for and permanently
# removes the cap pressure. Post-vertical clients always send the param explicitly.
_VERTICAL_PATTERN = "^(" + "|".join(VERTICALS) + ")$"
DEFAULT_VERTICAL = "grocery"


def _scoped(stmt, vertical: Optional[str]):
    """Narrow *stmt* to one section of the app, applying the default when omitted.

    Every vertical-aware endpoint goes through this one function on purpose: the bulk
    payload/trace endpoints promise to mirror `/offers`, and `/categories` renders the
    chips that filter it. If they defaulted differently the chips would advertise a
    vertical the list doesn't serve — so there is exactly one place the default lives.

    Two filters, because a vertical is a chain set, a category carve-out, or a chain set
    minus one (see `verticals.py`). `Offer.category` is NOT NULL, so `notin_` can't be
    tripped by SQL's three-valued logic — a nullable column would need an explicit
    `IS NULL` arm here, and would silently drop rows without one.
    """
    spec = VERTICALS.get(vertical or DEFAULT_VERTICAL)
    if spec is None:  # unreachable via the API (the Query pattern 422s first)
        return stmt.where(false())
    stmt = stmt.where(Store.chain.in_(spec.chains))
    if spec.categories is not None:
        stmt = stmt.where(Offer.category.in_(sorted(spec.categories)))
    if spec.excluded_categories:
        stmt = stmt.where(Offer.category.notin_(sorted(spec.excluded_categories)))
    return stmt


def _require_admin(
    x_admin_token: Optional[str], token: Optional[str], request: Optional[Request]
) -> None:
    """Guard a destructive endpoint with ADMIN_TOKEN — enforced only when that env is
    set (local dev / tests stay open). Prefers the `X-Admin-Token` header; the `token`
    query param is a deprecated fallback for pre-header app builds (query strings land
    in access logs — the header doesn't). Timing-safe compare; failures are logged so
    probing is visible. Non-str values are normalized (direct function calls in tests
    pass the FastAPI `Header(None)` default marker)."""
    if not settings.admin_token:
        return
    provided = next((v for v in (x_admin_token, token) if isinstance(v, str)), "")
    if not secrets.compare_digest(provided, settings.admin_token):
        client = request.client.host if request is not None and request.client else "unknown"
        logger.warning("admin auth failed for %s from %s", request.url.path if request else "?", client)
        raise HTTPException(status_code=403, detail="invalid or missing admin token")


# On-demand scrape throttle: a PLZ that already has offers is re-scraped at most once
# per cooldown, and scrape kickoffs are globally rate-limited — so a stranger hitting
# the public URL can't hammer the flyer sites from this server. An EMPTY PLZ always
# scrapes (the app's cold-start on-demand path and post-wipe rescrape must never block).
# `None` sentinels (not 0.0): time.monotonic() is small right after boot, and a 0-default
# would read as "just scraped" and wrongly throttle the first minutes after a cold start.
_SCRAPE_COOLDOWN_S = 600.0
_SCRAPE_MIN_GAP_S = 15.0
_last_scrape_at: dict = {}  # plz -> time.monotonic() of its last accepted scrape
_last_any_scrape: Optional[float] = None

# Public store-lookup rate limit: /api/nearby-stores fans out to Overpass/Nominatim on a
# cache miss, so a stranger iterating coordinates (the cache keys on ~110 m) could make THIS
# server hammer Overpass and get our IP rate-limited. Bound it to ~30/min (burst 30) — a
# single real user makes ~1 call (opening Stores / tapping Change), so this is invisible to
# them but a hard ceiling for an abuser. Over budget → return [] (the same graceful contract
# the endpoint already returns when the mirrors are unreachable). Global, not per-IP (simpler,
# and the goal is protecting our own outbound reputation); per-IP is a future refinement.
_NEARBY_LIMITER = RateLimiter(capacity=30, refill_per_s=0.5)


@router.get("/offers", response_model=List[OfferOut])
def list_offers(
    session: SessionDep,
    category: Optional[str] = None,
    chain: Optional[str] = None,
    plz: Optional[str] = None,
    source: Optional[str] = Query(None, pattern="^(coupon|flyer|clearance)$"),
    min_discount: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query("discount", pattern="^(discount|price)$"),
    limit: int = Query(200, ge=1, le=2000),
    vertical: Optional[str] = Query(None, pattern=_VERTICAL_PATTERN),
):
    """List offers, filterable by vertical/category/chain/plz/min-discount.

    Default sort is by % discount descending — the headline feature.
    """
    stmt = select(Offer).options(selectinload(Offer.store)).join(Store)
    if category:
        stmt = stmt.where(Offer.category == category)
    stmt = _scoped(stmt, vertical)
    if chain:
        stmt = stmt.where(Store.chain == chain)
    if plz:
        stmt = stmt.where(Store.plz == plz)
    if source:
        stmt = stmt.where(Offer.source == source)
    if min_discount is not None:
        stmt = stmt.where(Offer.discount_pct >= min_discount)
    # Drop offers whose validity window has passed (Berlin's "today", not the server's).
    stmt = stmt.where((Offer.valid_to.is_(None)) | (Offer.valid_to >= berlin_today()))
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


@router.get("/offers/payloads")
def offer_payloads(
    session: SessionDep,
    plz: Optional[str] = None,
    vertical: Optional[str] = Query(None, pattern=_VERTICAL_PATTERN),
):
    """All raw payloads for a PLZ's (deduped) offers, keyed by offer id — lets the app
    prefetch + cache them so the deal detail's "View payload" is instant + offline instead
    of a per-offer round-trip (which, on the sleepy free tier, means a cold start). Mirrors
    /api/offers' dedup + validity filter so the ids line up with the list; a value is null
    where the payload wasn't captured (pre-capture / sample fallback). Not in OfferOut (too
    big for the list) — this is fetched once, in the background.

    It takes `vertical` for the same reason: the app caches payloads per vertical, so
    without it a drugstore session would download every grocery payload too (~2 MB for a
    283-offer list) and the "ids line up with the list" contract would quietly be false."""
    stmt = select(Offer).options(selectinload(Offer.store)).join(Store)
    if plz:
        stmt = stmt.where(Store.plz == plz)
    stmt = _scoped(stmt, vertical)
    stmt = stmt.where((Offer.valid_to.is_(None)) | (Offer.valid_to >= berlin_today()))
    rows = dedup_offers(session.scalars(stmt).all())
    return {str(o.id): (json.loads(o.raw_payload) if o.raw_payload else None) for o in rows}


def _stored_path(offer: Offer) -> Optional[List[str]]:
    """The offer's source taxonomy path, decoded the same way `recategorize` does.

    Defensive about the element type on purpose: `explain` evaluates layers that `classify`
    short-circuits past, so it reaches `_path_node_hit` on rows the classifier never walked
    — and a non-string node there would raise inside `.strip()`. Scraped rows are clean, but
    this decodes a Text column, so it's validated here at the boundary rather than by
    loosening `_path_node_hit` (whose behaviour must stay byte-identical).
    """
    if not offer.category_path:
        return None
    try:
        raw = json.loads(offer.category_path)
    except ValueError:
        return None
    return [n for n in raw if isinstance(n, str)] if isinstance(raw, list) else None


def _trace_for(offer: Offer) -> dict:
    """Recompute the classification and report it alongside the STORED one.

    Categories are persisted at scrape time, so a row can predate a classifier change: the
    app would then be showing `stored_category` while the rules now say something else.
    `stale` names that explicitly — without it the trace would confidently explain a
    category the offer isn't actually in, which is the failure this feature exists to catch.
    """
    trace = categories.explain(offer.name, offer.brand, _stored_path(offer), offer.unit)
    return {
        "id": offer.id,
        "stored_category": offer.category,
        "stored_label": categories.label(offer.category),
        "computed_category": trace.category,
        "computed_label": categories.label(trace.category),
        "stale": trace.category != offer.category,
        "trace": trace,
    }


def _compact(trace: categories.ClassifyTrace) -> dict:
    """The trace stripped to what the app can't already derive — for the BULK response only.

    This one is prefetched for every offer, so its size is a storage budget, not a detail:
    measured over a real PLZ (1635 offers) the naive form is 2.30 MB, on top of the ~2.6 MB
    payload cache. Three lossless-for-the-UI cuts take it to 1.30 MB:
      * null fields dropped (most layers are a bare "no_match");
      * `name` dropped — it's a fixed function of `layer`, and the app renders its own
        human labels anyway;
      * `where` dropped on layers that didn't decide (it only means anything for a match);
      * of `inputs`, only `category_path` kept — the app already holds name/brand/unit on
        the Offer, and the padded haystacks are a deep-dive detail.
    The per-offer endpoint keeps the full shape, so nothing is permanently lost.
    """
    layers = []
    for step in trace.layers:
        entry = {k: v for k, v in asdict(step).items() if v is not None and k != "name"}
        if step.status != "decided":
            entry.pop("where", None)
        layers.append(entry)
    path = trace.inputs.category_path
    out = {
        "category": trace.category,
        "inputs": {"category_path": path} if path else {},
        "layers": layers,
    }
    # Without this a redirected offer renders as "pantry" above a layer list whose only
    # decided entry says "vegetables" — the trace contradicting its own answer, which is the
    # one thing a debugging surface must never do. Costs ~nothing: a handful of rows per PLZ.
    if trace.redirect is not None:
        out["redirect"] = {k: v for k, v in asdict(trace.redirect).items()
                           if v is not None and k != "name"}
    return out


@router.get("/offers/{offer_id}/category-trace")
def offer_category_trace(session: SessionDep, offer_id: int):
    """Why this offer is in its category: which rule decided, which layers were skipped and
    why, and what the losing layers WOULD have said (the counterfactual is what tells you
    where a fix belongs). Powers the app's "Why this category?" view.

    Read-only and un-guarded like /payload — the rule tables are in a public repo. Also
    exposes `category_path`, which is stored but deliberately absent from OfferOut, so the
    most common cause of a mis-file is no longer invisible from the API."""
    offer = session.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")
    return _trace_for(offer)


@router.get("/offers/category-traces")
def offer_category_traces(
    session: SessionDep,
    plz: Optional[str] = None,
    vertical: Optional[str] = Query(None, pattern=_VERTICAL_PATTERN),
):
    """Every (deduped) offer's classification trace for a PLZ, keyed by offer id — the app
    prefetches this so "Why this category?" is instant + offline. Mirrors /api/offers' dedup
    + validity filter (and its `vertical` scope) so the ids line up with the list, exactly
    like /offers/payloads."""
    stmt = select(Offer).options(selectinload(Offer.store)).join(Store)
    if plz:
        stmt = stmt.where(Store.plz == plz)
    stmt = _scoped(stmt, vertical)
    stmt = stmt.where((Offer.valid_to.is_(None)) | (Offer.valid_to >= berlin_today()))
    rows = dedup_offers(session.scalars(stmt).all())
    out = {}
    for offer in rows:
        entry = _trace_for(offer)
        entry["trace"] = _compact(entry["trace"])
        out[str(offer.id)] = entry
    return out


@router.get("/categories", response_model=List[CategoryCount])
def list_categories(
    session: SessionDep,
    plz: Optional[str] = None,
    vertical: Optional[str] = Query(None, pattern=_VERTICAL_PATTERN),
):
    """Categories that currently have offers, with counts (for filter chips).

    Counts distinct products (deduped) so the chip number matches the deduped list, and
    takes the same `vertical` scope as `/offers` so the chips match the list they filter.
    Categories with no offers are omitted, so a vertical simply never sees the other's
    chips — no per-vertical category list is needed. That holds for a category-scoped
    vertical too, and for the same reason: `_scoped` filters the rows the counts are
    built from, so Drinks' chips can only be drink slugs and Grocery's can never include
    one. The chips are derived from the same query as the list, never from a second list
    of "which categories belong here" that could drift from it.
    """
    stmt = select(Offer).options(selectinload(Offer.store)).join(Store).where(
        (Offer.valid_to.is_(None)) | (Offer.valid_to >= berlin_today())
    )
    if plz:
        stmt = stmt.where(Store.plz == plz)
    stmt = _scoped(stmt, vertical)
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

    Rate-limited so a third party can't drive this endpoint's outbound Overpass/Nominatim
    fan-out unbounded (which would burn our IP's reputation with the free OSM services).
    """
    if not _NEARBY_LIMITER.allow():
        logger.warning("nearby-stores rate limit reached; returning [] to protect the OSM fan-out budget")
        return []
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
    `market_code` means no real store resolved (sample-data fallback). Throttled:
    a PLZ that already has offers is re-scraped at most once per cooldown (and
    kickoffs are globally rate-limited) — the skip returns `scraped=0, skipped=True`.
    An empty PLZ always scrapes, so the app's cold-start path never blocks.
    """
    global _last_any_scrape
    from ..scrapers.run import run_scrapers

    target = plz or settings.default_plz
    now = time.monotonic()
    has_rows = (
        session.scalar(
            select(Offer.id).join(Store).where(Store.plz == target).limit(1)
        )
        is not None
    )
    last_plz = _last_scrape_at.get(target)
    on_cooldown = last_plz is not None and now - last_plz < _SCRAPE_COOLDOWN_S
    too_soon = _last_any_scrape is not None and now - _last_any_scrape < _SCRAPE_MIN_GAP_S
    if has_rows and (on_cooldown or too_soon):
        logger.info("scrape skipped (throttled) for plz=%s", target)
        stores = session.scalars(select(Store).where(Store.plz == target)).all()
        return {
            "plz": target,
            "scraped": 0,
            "skipped": True,
            "stores": [
                StoreOut(id=s.id, chain=s.chain, name=s.name, plz=s.plz, market_code=s.market_code)
                for s in stores
            ],
        }

    _last_scrape_at[target] = now
    _last_any_scrape = now
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
def trigger_recategorize(
    session: SessionDep,
    token: Optional[str] = None,
    x_admin_token: Optional[str] = Header(None),
    request: Request = None,
):
    """Re-apply the classifier to all stored offers (admin/maintenance).

    Guarded by ADMIN_TOKEN when that env is set (otherwise open, for local dev)."""
    _require_admin(x_admin_token, token, request)
    from ..scripts.recategorize import recategorize

    return {"recategorized": recategorize(session)}


@router.post("/reset")
def trigger_reset(
    session: SessionDep,
    plz: Optional[str] = None,
    token: Optional[str] = None,
    x_admin_token: Optional[str] = Header(None),
    request: Request = None,
):
    """Wipe every stored offer, then re-scrape `plz` from scratch (admin/maintenance).

    Unlike /api/scrape (which upserts in place), this first DELETEs all offers so stale
    rows the weekly scrape no longer touches are removed too, then re-scrapes. The
    immediate re-scrape re-populates the table, so the brief empty window self-heals; on a
    sample-data fallback the table comes back sparse (re-run when the source is reachable).
    Guarded by ADMIN_TOKEN when that env var is set (otherwise open, for local dev);
    send the token as an `X-Admin-Token` header (query `token` is a deprecated fallback).
    """
    _require_admin(x_admin_token, token, request)

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
