"""Nearby-store locator via OpenStreetMap Overpass.

Finds the nearest store of each known German grocery chain around a coordinate,
with its address, so the app can show a "Stores" directory. Lidl/REWE are
"active" (we scrape their deals); the rest are address-only placeholders the user
can add to a "My stores" list ("deals coming soon").

OSM data is free, key-less, and deterministic. Public Overpass instances are
flaky, so we try several mirrors in order and cache results per area (store
locations are static); on total failure we return [] and the caller shows a
friendly message — same fall-back-don't-crash spirit as the deal scrapers.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx

from ..http import tracked_client

# canonical slug -> (display label, OSM brand/name prefixes that map to it).
# Prefixes are matched against the lowercased `brand` (then `name`) tag, so
# "Aldi Nord"/"Aldi Süd" -> aldi and "Netto Marken-Discount" -> netto.
CHAINS: Dict[str, Tuple[str, List[str]]] = {
    "lidl": ("Lidl", ["lidl"]),
    "rewe": ("REWE", ["rewe"]),
    "edeka": ("Edeka", ["edeka"]),
    "aldi": ("Aldi", ["aldi"]),
    "netto": ("Netto", ["netto"]),
    "penny": ("Penny", ["penny"]),
    "kaufland": ("Kaufland", ["kaufland"]),
}
# Chains we actually scrape deals for; everything else is a placeholder.
ACTIVE_CHAINS = {"lidl", "rewe"}

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
HEADERS = {"User-Agent": "grocery-helper/1.0 (personal project; Berlin grocery deals)"}

_CACHE: Dict[Tuple[float, float, int], Tuple[float, List["NearbyStore"]]] = {}
_CACHE_TTL = 24 * 3600  # store locations are static; cache aggressively


@dataclass
class NearbyStore:
    chain: str
    label: str
    name: str
    address: Optional[str]
    lat: float
    lng: float
    distance_m: int
    active: bool


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _chain_for(brand: Optional[str], name: Optional[str]) -> Optional[str]:
    """Map an OSM brand/name to a canonical chain slug, or None if not in scope."""
    for text in (brand, name):  # brand is the more reliable signal; try it first
        if not text:
            continue
        t = text.strip().lower()
        for slug, (_, prefixes) in CHAINS.items():
            if any(t.startswith(p) for p in prefixes):
                return slug
    return None


def _assemble_address(tags: dict) -> Optional[str]:
    line1 = " ".join(x for x in [tags.get("addr:street"), tags.get("addr:housenumber")] if x)
    line2 = " ".join(x for x in [tags.get("addr:postcode"), tags.get("addr:city")] if x)
    return ", ".join(x for x in [line1, line2] if x) or None


def _select_nearest(elements: List[dict], lat: float, lng: float) -> List[NearbyStore]:
    """Pure: pick the nearest in-scope store per chain from raw Overpass elements.

    Unit-tested against a saved fixture so we never hit the live API in tests.
    """
    best: Dict[str, NearbyStore] = {}
    for el in elements:
        tags = el.get("tags") or {}
        slug = _chain_for(tags.get("brand"), tags.get("name"))
        if not slug:
            continue  # not a chain we list (bio/organic/local markets excluded)
        elat = el.get("lat") or (el.get("center") or {}).get("lat")  # node vs way
        elng = el.get("lon") or (el.get("center") or {}).get("lon")
        if elat is None or elng is None:
            continue
        dist = int(round(_haversine(lat, lng, elat, elng)))
        cur = best.get(slug)
        if cur is None or dist < cur.distance_m:  # strictly nearest of this chain
            best[slug] = NearbyStore(
                chain=slug,
                label=CHAINS[slug][0],
                name=tags.get("name") or CHAINS[slug][0],
                address=_assemble_address(tags),
                lat=float(elat),
                lng=float(elng),
                distance_m=dist,
                active=slug in ACTIVE_CHAINS,
            )
    return sorted(best.values(), key=lambda s: s.distance_m)


def _overpass_query(lat: float, lng: float, radius_m: int) -> str:
    return (
        "[out:json][timeout:25];"
        f'(node["shop"="supermarket"](around:{radius_m},{lat},{lng});'
        f'way["shop"="supermarket"](around:{radius_m},{lat},{lng}););'
        "out center tags;"
    )


def _fetch_overpass(query: str, client: httpx.Client) -> Optional[List[dict]]:
    """Try each mirror in order; first 200 wins. None if all fail."""
    for url in OVERPASS_MIRRORS:
        try:
            resp = client.post(url, data={"data": query})
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except Exception:
            continue
    return None


def nearby_stores(
    lat: float, lng: float, radius_m: int = 2500, client: Optional[httpx.Client] = None
) -> List[NearbyStore]:
    """Nearest store of each known chain around (lat, lng). [] if all mirrors fail."""
    key = (round(lat, 3), round(lng, 3), radius_m)
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    own = client is None
    client = client or tracked_client(timeout=30, headers=HEADERS)
    try:
        elements = _fetch_overpass(_overpass_query(lat, lng, radius_m), client)
    finally:
        if own:
            client.close()
    if elements is None:
        return []  # all mirrors failed; don't cache, let the caller retry later

    result = _select_nearest(elements, lat, lng)
    _CACHE[key] = (time.time(), result)
    return result
