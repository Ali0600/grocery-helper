"""Collapse duplicate offers to one per product.

A chain publishes several weekly brochures, so the flyer feed repeats the same
product across them (each with a distinct content id our `external_id` keys on),
and a product can also appear as both a coupon and a flyer offer. These share
store + name + price, so we keep a single representative — preferring a
discounted, flyer (richer: image / categoryPath / per-unit) row — and apply the
same collapse to the offer list and the category counts so they agree.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List

from .models import Offer


def _norm_name(name: str | None) -> str:
    # Different brochures spell the same product slightly differently — most often
    # a curly vs straight apostrophe ("Butcher's" / "Butcher’s"). Normalize unicode,
    # unify apostrophe variants, and collapse whitespace so they match.
    s = unicodedata.normalize("NFKC", name or "").lower()
    for ch in "’‘`´":
        s = s.replace(ch, "'")
    return re.sub(r"\s+", " ", s).strip()


def _key(o: Offer):
    return (o.store_id, _norm_name(o.name), o.price_cents)


def _rank(o: Offer):
    # Higher wins. Keep the richest copy: some brochure crops of the same product
    # omit the per-unit price, so prefer one that has it (else the €/kg sort loses
    # the item); then a discount, then flyer over coupon, then a stable id tiebreak.
    return (
        o.price_per_unit is not None,
        o.discount_pct if o.discount_pct is not None else -1.0,
        1 if o.source == "flyer" else 0,
        o.image_url is not None,
        -(o.id or 0),
    )


def dedup_offers(offers: Iterable[Offer]) -> List[Offer]:
    """One offer per (store, name, price); the best representative wins."""
    best: dict = {}
    for o in offers:
        k = _key(o)
        cur = best.get(k)
        if cur is None or _rank(o) > _rank(cur):
            best[k] = o
    return list(best.values())
