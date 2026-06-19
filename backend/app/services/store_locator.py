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
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "grocery-helper/1.0 (personal project; Berlin grocery deals)"}

_CACHE: Dict[Tuple[float, float, int], Tuple[float, List["NearbyStore"]]] = {}
# All in-scope branches per area (for the "Change branch" picker), same TTL.
_BRANCH_CACHE: Dict[Tuple[float, float, int], Tuple[float, List["NearbyStore"]]] = {}
_PLZ_CACHE: Dict[str, Tuple[float, float]] = {}  # postal code -> centroid lat/lng
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


def _all_branches(elements: List[dict], lat: float, lng: float) -> List[NearbyStore]:
    """Pure: every in-scope store (not just the nearest per chain), sorted by
    distance and de-duplicated. One physical store can appear in OSM as both a node
    and a building way, so collapse by (chain, address) — or by coarse coordinates
    (~11 m) when an address is missing — keeping the nearest copy. Backs the picker.
    """
    out: List[NearbyStore] = []
    for el in elements:
        tags = el.get("tags") or {}
        slug = _chain_for(tags.get("brand"), tags.get("name"))
        if not slug:
            continue
        elat = el.get("lat") or (el.get("center") or {}).get("lat")  # node vs way
        elng = el.get("lon") or (el.get("center") or {}).get("lon")
        if elat is None or elng is None:
            continue
        out.append(
            NearbyStore(
                chain=slug,
                label=CHAINS[slug][0],
                name=tags.get("name") or CHAINS[slug][0],
                address=_assemble_address(tags),
                lat=float(elat),
                lng=float(elng),
                distance_m=int(round(_haversine(lat, lng, elat, elng))),
                active=slug in ACTIVE_CHAINS,
            )
        )
    out.sort(key=lambda s: s.distance_m)
    seen = set()
    deduped: List[NearbyStore] = []
    for s in out:
        key = (s.chain, s.address) if s.address else (s.chain, round(s.lat, 4), round(s.lng, 4))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    return deduped


def chain_branches(
    chain: str,
    lat: float,
    lng: float,
    radius_m: int = 6000,
    limit: int = 12,
    client: Optional[httpx.Client] = None,
) -> List[NearbyStore]:
    """Branches of one chain around (lat, lng), nearest first. [] if all mirrors fail
    or the chain isn't one we list. Wider radius than the nearest-scan so a branch a
    few km out (the one actually near the user) is included."""
    if chain not in CHAINS:
        return []
    key = (round(lat, 3), round(lng, 3), radius_m)
    cached = _BRANCH_CACHE.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        branches = cached[1]
    else:
        own = client is None
        client = client or tracked_client(timeout=30, headers=HEADERS)
        try:
            elements = _fetch_overpass(_overpass_query(lat, lng, radius_m), client)
        finally:
            if own:
                client.close()
        if elements is None:
            return []  # all mirrors failed; don't cache, let the caller retry
        branches = _all_branches(elements, lat, lng)
        _BRANCH_CACHE[key] = (time.time(), branches)
    return [s for s in branches if s.chain == chain][:limit]


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


def plz_centroid(plz: str, client: Optional[httpx.Client] = None) -> Optional[Tuple[float, float]]:
    """Geocode a German postal code to its centroid via OSM Nominatim (cached).

    The scraped Store coords point at the nearest *Lidl*, which can sit in the next
    district (e.g. a 10115/Wilmersdorf PLZ resolves to a Schöneberg Lidl ~3 km away).
    For the "Change branch" picker we want the user's actual neighbourhood, so we
    centre on the PLZ itself. None on any failure → caller falls back to the store
    coords. One request per PLZ per process (Nominatim asks for light, UA'd use)."""
    if plz in _PLZ_CACHE:
        return _PLZ_CACHE[plz]
    own = client is None
    client = client or tracked_client(timeout=20, headers=HEADERS)
    try:
        resp = client.get(
            NOMINATIM_URL,
            params={"postalcode": plz, "country": "Germany", "format": "json", "limit": 1},
        )
        resp.raise_for_status()
        data = resp.json()
        coord = (float(data[0]["lat"]), float(data[0]["lon"]))
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
        return None
    finally:
        if own:
            client.close()
    _PLZ_CACHE[plz] = coord
    return coord


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
