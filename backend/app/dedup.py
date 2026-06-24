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
from typing import TYPE_CHECKING, Iterable, List

from .models import Offer

if TYPE_CHECKING:
    from .scrapers.base import ScrapedOffer


def _norm_name(name: str | None) -> str:
    # Different brochures spell the same product slightly differently — a curly vs
    # straight apostrophe ("Butcher's"/"Butcher’s"), decorative German quotes around a
    # word ("…Avocado »Hass«"), or an extra produce quality-grade ("…Hass, Kl. I" vs
    # "…Hass"). Normalize unicode, drop apostrophes, strip the grade token, turn any
    # remaining punctuation into spaces, and collapse whitespace so the variants match.
    s = unicodedata.normalize("NFKC", name or "").lower()
    for ch in "’‘`´'":
        s = s.replace(ch, "")  # contraction apostrophe -> nothing ("butcher's" -> butchers)
    s = re.sub(r"\bkl(?:asse)?\.?\s*(?:i{1,3}|[123])\b", " ", s)  # produce grade ("Kl. I")
    s = re.sub(r"[^\w ]+", " ", s)  # decorative quotes / commas / hyphens -> space
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


def _rank_scraped(o: "ScrapedOffer"):
    # Mirror _rank for a not-yet-persisted ScrapedOffer (no discount_pct/source yet):
    # prefer a per-unit price, then a struck regular price, then an image, then a
    # stable external_id tiebreak so the choice is deterministic across runs.
    return (
        o.price_per_unit is not None,
        o.regular_price_cents is not None and o.regular_price_cents > o.price_cents,
        o.image_url is not None,
        o.external_id or "",
    )


def dedup_scraped(offers: Iterable["ScrapedOffer"]) -> List["ScrapedOffer"]:
    """Collapse the same product scraped across one chain's overlapping brochures
    (same normalized name + price), keeping the richest copy — the scrape-time twin of
    `dedup_offers`. A publisher's meinprospekt page surfaces a set of "active" brochures
    that depends on the scraping host's IP/geolocation (a Frankfurt datacenter sees more,
    overlapping brochures than a Berlin home line), so the *raw* offer count is
    non-deterministic. Deduping here makes the stored set and the reported scrape count
    depend only on the distinct products, not on how many duplicate brochures were served.
    """
    best: dict = {}
    for o in offers:
        k = (_norm_name(o.name), o.price_cents)
        cur = best.get(k)
        if cur is None or _rank_scraped(o) > _rank_scraped(cur):
            best[k] = o
    return list(best.values())
