"""Basket optimizer: given the categories you want and how many stores you're
willing to visit, pick the cheapest combination.

- store_count == 1: the single store that covers the most wanted categories,
  tie-broken by lowest total. (One trip, simplest.)
- store_count >= 2: cherry-pick the cheapest item per category across all
  available stores, then report how much that saves vs. the best single store.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Offer, Store
from ..schemas import OptimizeRequest, OptimizeResponse, StoreBasket
from ..serializers import offer_to_out


def optimize_basket(session: Session, req: OptimizeRequest) -> OptimizeResponse:
    wanted = req.categories
    stmt = select(Offer).join(Store)
    if req.plz:
        stmt = stmt.where(Store.plz == req.plz)
    if wanted:
        stmt = stmt.where(Offer.category.in_(wanted))
    stmt = stmt.where((Offer.valid_to.is_(None)) | (Offer.valid_to >= date.today()))
    offers = session.scalars(stmt).all()

    # cheapest offer per (store_id, category)
    best: Dict[int, Dict[str, Offer]] = {}
    stores: Dict[int, Store] = {}
    for off in offers:
        stores[off.store_id] = off.store
        per = best.setdefault(off.store_id, {})
        if off.category not in per or off.price_cents < per[off.category].price_cents:
            per[off.category] = off

    if not stores:
        return OptimizeResponse(
            store_count=req.store_count,
            baskets=[],
            total_cents=0,
            missing_categories=list(wanted),
        )

    def store_total(sid: int) -> int:
        return sum(o.price_cents for o in best[sid].values())

    # best single store: most categories covered, then cheapest
    best_single = max(stores, key=lambda sid: (len(best[sid]), -store_total(sid)))
    single_total = store_total(best_single)

    if req.store_count <= 1:
        chosen = best[best_single]
        s = stores[best_single]
        basket = StoreBasket(
            store_id=s.id,
            chain=s.chain,
            name=s.name,
            items=[offer_to_out(o) for o in chosen.values()],
            subtotal_cents=single_total,
        )
        return OptimizeResponse(
            store_count=1,
            baskets=[basket],
            total_cents=single_total,
            missing_categories=[c for c in wanted if c not in chosen],
            single_store_total_cents=single_total,
            savings_cents=0,
        )

    # multi-store: cheapest per category across all stores
    cats = wanted or sorted({c for per in best.values() for c in per})
    picks: Dict[int, List[Offer]] = {}
    covered = set()
    for cat in cats:
        candidates = [per[cat] for per in best.values() if cat in per]
        if not candidates:
            continue
        winner = min(candidates, key=lambda o: o.price_cents)
        picks.setdefault(winner.store_id, []).append(winner)
        covered.add(cat)

    baskets: List[StoreBasket] = []
    total = 0
    for sid, offs in picks.items():
        sub = sum(o.price_cents for o in offs)
        total += sub
        s = stores[sid]
        baskets.append(
            StoreBasket(
                store_id=s.id,
                chain=s.chain,
                name=s.name,
                items=[offer_to_out(o) for o in offs],
                subtotal_cents=sub,
            )
        )

    return OptimizeResponse(
        store_count=len(baskets),
        baskets=baskets,
        total_cents=total,
        missing_categories=[c for c in wanted if c not in covered],
        single_store_total_cents=single_total,
        savings_cents=max(single_total - total, 0),
    )
