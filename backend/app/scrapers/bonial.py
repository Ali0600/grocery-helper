"""Bonial / meinprospekt scraper — Lidl's weekly Aktionsprospekt (the real flyer).

The Lidl Plus scraper (`lidl.py`) returns app *coupons*; this returns the full
printed weekly leaflet, which meinprospekt (a Bonial property) exposes as
STRUCTURED offers — name, brand, sales + regular price, image, validity — so no
OCR is needed.

Flow:
  1. discover Lidl's currently-valid weekly brochure(s) from the publisher page
     (the page embeds them in a Next.js ``__NEXT_DATA__`` blob)
  2. fetch each brochure's pages -> structured offers
  3. map to ScrapedOffer; the discount comes from SALES_PRICE vs REGULAR_PRICE,
     falling back to the offer's discountLabel to recover more discounts

Offers are location-gated, so a store lat/lng is required (we reuse the one the
Lidl Plus store lookup already resolves). Bonial soft-throttles bursts, so this
is meant to run weekly with caching; on any failure we fall back to sample data
so the rest of the app keeps working.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import httpx

from .base import ScrapedOffer, ScrapeResult

PUBLISHER_ID = "DE-1013"  # Lidl (the page also embeds other retailers' brochures)
PUBLISHER_PAGE = "https://www.meinprospekt.de/lidl"
BE = "https://content-viewer-be.meinprospekt.de"
CONSUMER = "meinprospekt"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "de-DE,de;q=0.9",
    "Bonial-Api-Consumer": CONSUMER,
}
# A weekly flyer runs <= ~2 weeks; this excludes long-running "Preisführer" lists.
MAX_FLYER_DAYS = 14
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


class BonialScraper:
    chain = "lidl"
    source = "flyer"  # weekly Aktionsprospekt

    def __init__(self, client: Optional[httpx.Client] = None) -> None:
        self._client = client

    def fetch(self, plz: str, lat: float, lng: float) -> ScrapeResult:
        try:
            offers = self._fetch_live(lat, lng)
            if not offers:
                raise RuntimeError("Bonial returned no flyer offers")
            return ScrapeResult(
                chain=self.chain, store_name=f"Lidl {plz}", plz=plz,
                lat=lat, lng=lng, offers=offers,
            )
        except Exception:
            return ScrapeResult(
                chain=self.chain, store_name=f"Lidl {plz}", plz=plz,
                lat=lat, lng=lng, offers=self._sample(),
            )

    # -- live -----------------------------------------------------------------

    def _fetch_live(self, lat: float, lng: float) -> List[ScrapedOffer]:
        own = self._client is None
        client = self._client or httpx.Client(
            timeout=30, follow_redirects=True, headers=HEADERS
        )
        try:
            offers: dict = {}
            for b in self._current_brochures(client):
                resp = client.get(
                    f"{BE}/v1/brochures/{b['id']}/pages", params={"lat": lat, "lng": lng}
                )
                resp.raise_for_status()
                for off in self._offers_from_pages(resp.json(), b["valid_from"], b["valid_to"]):
                    offers[off.external_id] = off  # dedupe across brochures
            return list(offers.values())
        finally:
            if own:
                client.close()

    def _current_brochures(self, client: httpx.Client) -> List[dict]:
        resp = client.get(PUBLISHER_PAGE, headers={"Accept": "text/html"})
        resp.raise_for_status()
        m = _NEXT_DATA_RE.search(resp.text)
        if not m:
            raise RuntimeError("publisher page missing __NEXT_DATA__")
        found: dict = {}
        self._collect_brochures(json.loads(m.group(1)), found)
        now = datetime.now(timezone.utc)
        active = []
        for bid, b in found.items():
            vf, vu = _parse_dt(b.get("validFrom")), _parse_dt(b.get("validUntil"))
            if vf and vu and vf <= now <= vu and (vu - vf).days <= MAX_FLYER_DAYS:
                active.append({"id": bid, "valid_from": vf.date(), "valid_to": vu.date()})
        if not active:
            raise RuntimeError("no active weekly Lidl brochure found")
        return active

    @staticmethod
    def _collect_brochures(node, out: dict) -> None:
        if isinstance(node, dict):
            publisher = (node.get("publisher") or {}).get("id")
            if (
                node.get("pageCount")
                and node.get("validUntil")
                and node.get("id") is not None
                and publisher == PUBLISHER_ID  # Lidl only, not embedded competitors
            ):
                out.setdefault(str(node["id"]), node)
            for v in node.values():
                BonialScraper._collect_brochures(v, out)
        elif isinstance(node, list):
            for v in node:
                BonialScraper._collect_brochures(v, out)

    # -- parsing (pure; unit-tested against a saved fixture) ------------------

    @classmethod
    def _offers_from_pages(cls, pages_json: dict, valid_from, valid_to) -> List[ScrapedOffer]:
        out = []
        for page in pages_json.get("contents", []):
            for wrapper in page.get("offers") or []:
                content = wrapper.get("content")
                offer = cls._parse_offer(content, valid_from, valid_to) if content else None
                if offer:
                    out.append(offer)
        return out

    @staticmethod
    def _parse_offer(c: dict, valid_from, valid_to) -> Optional[ScrapedOffer]:
        sales = _deal(c, "SALES_PRICE")
        if sales is None:
            return None  # not a priced offer
        product = (c.get("products") or [{}])[0]
        brand = product.get("brandName") or None
        name = " ".join(x for x in [brand, product.get("name")] if x) or "Lidl Angebot"
        desc = product.get("description") or []
        unit = (desc[0] or {}).get("paragraph") if desc else None
        regular = _deal(c, "REGULAR_PRICE")
        if regular is None:
            regular = _regular_from_label(sales, c.get("discountLabel"))
        category_path = [
            cp["name"] for cp in (product.get("categoryPaths") or []) if cp.get("name")
        ]
        return ScrapedOffer(
            external_id=str(c.get("id")),
            name=name,
            price_cents=round(sales * 100),
            regular_price_cents=round(regular * 100) if regular else None,
            brand=brand,
            unit=unit,
            image_url=c.get("image"),
            valid_from=valid_from,
            valid_to=valid_to,
            category_path=category_path,
        )

    # -- fallback sample ------------------------------------------------------

    def _sample(self) -> List[ScrapedOffer]:
        today = date.today()
        end = today + timedelta(days=6)

        def o(ext, name, price, regular, unit, brand=None):
            return ScrapedOffer(external_id=ext, name=name, price_cents=price,
                                regular_price_cents=regular, unit=unit, brand=brand,
                                valid_from=today, valid_to=end)

        return [
            o("fl-001", "Eberswalder Rostbratwurst", 199, 249, "300 g", "Eberswalder"),
            o("fl-002", "Heinz Tomatenketchup", 179, 279, "800 ml", "Heinz"),
            o("fl-003", "Brunch Kräuter", 129, 189, "250 g", "Brunch"),
            o("fl-004", "Nautica Räucherlachs", 349, 429, "200 g", "Nautica"),
        ]


def _deal(content: dict, deal_type: str) -> Optional[float]:
    for d in content.get("deals") or []:
        if d.get("type") == deal_type and d.get("max") is not None:
            return float(d["max"])
    return None


def _regular_from_label(sales: float, label: Optional[dict]) -> Optional[float]:
    """Recover a regular price from the offer's discount badge when REGULAR_PRICE
    is absent: a "-0.50 €" amount or a "-20 %" percentage both imply it."""
    if not label:
        return None
    try:
        value = float(label.get("value"))
    except (TypeError, ValueError):
        return None
    kind = label.get("type")
    if kind == "DISCOUNT_AMOUNT":
        return round(sales + value, 2)
    if kind == "DISCOUNT_PERCENTAGE" and 0 < value < 100:
        return round(sales / (1 - value / 100), 2)
    return None


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(value))  # +0000 -> +00:00
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
