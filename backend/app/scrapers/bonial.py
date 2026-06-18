"""Meinprospekt / Bonial scraper — the weekly Aktionsprospekt (the real flyer).

The Lidl Plus scraper (`lidl.py`) returns app *coupons*; this returns the full
printed weekly leaflet, which meinprospekt (a Bonial property) exposes as
STRUCTURED offers — name, brand, sales (+ sometimes regular) price, image,
validity — so no OCR is needed.

It started Lidl-only but the pipeline is publisher-agnostic, so it's now a
generic engine (`MeinprospektScraper`) parameterized by publisher; each chain is
a thin subclass:
  - Lidl (publisher ``DE-1013``) -> :class:`BonialScraper`
  - REWE (publisher ``DE-1062``) -> :class:`ReweScraper`

Flow:
  1. discover the publisher's currently-valid weekly brochure(s) from its
     meinprospekt page (the page embeds them in a Next.js ``__NEXT_DATA__`` blob)
  2. fetch each brochure's pages -> structured offers
  3. map to ScrapedOffer; the discount comes from SALES_PRICE vs REGULAR_PRICE,
     falling back to the offer's discountLabel to recover more discounts. (Lidl
     flyers carry regular prices; REWE's "Dein Markt" flyer usually does not, so
     most REWE offers list a price without a % discount.)

Offers are location-gated, so a store lat/lng is required (we reuse the one the
Lidl Plus store lookup already resolves for the postal code). Bonial soft-
throttles bursts, so this is meant to run weekly with caching; on any failure we
fall back to sample data so the rest of the app keeps working.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import httpx

from ..http import tracked_client
from .base import ScrapedOffer, ScrapeResult

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


class MeinprospektScraper:
    """Generic engine: discover one publisher's current weekly brochure(s) from
    its meinprospekt page, then pull each brochure's structured offers.

    Subclasses set the publisher config (``publisher_id``, ``publisher_page``,
    ``chain``, ``store_label``) and a ``_sample`` fallback.
    """

    source = "flyer"  # weekly Aktionsprospekt
    publisher_id: str = ""
    publisher_page: str = ""
    chain: str = ""
    store_label: str = ""

    def __init__(self, client: Optional[httpx.Client] = None) -> None:
        self._client = client

    def fetch(self, plz: str, lat: float, lng: float) -> ScrapeResult:
        store_name = f"{self.store_label} {plz}"
        try:
            offers = self._fetch_live(lat, lng)
            if not offers:
                raise RuntimeError(f"{self.chain}: meinprospekt returned no flyer offers")
            return ScrapeResult(
                chain=self.chain, store_name=store_name, plz=plz,
                lat=lat, lng=lng, offers=offers,
            )
        except Exception:
            return ScrapeResult(
                chain=self.chain, store_name=store_name, plz=plz,
                lat=lat, lng=lng, offers=self._sample(),
            )

    # -- live -----------------------------------------------------------------

    def _fetch_live(self, lat: float, lng: float) -> List[ScrapedOffer]:
        own = self._client is None
        client = self._client or tracked_client(timeout=30, headers=HEADERS)
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
        resp = client.get(self.publisher_page, headers={"Accept": "text/html"})
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
            raise RuntimeError(f"no active weekly brochure for {self.chain}")
        return active

    def _collect_brochures(self, node, out: dict) -> None:
        """Walk the page blob collecting brochures published by *this* chain
        (the page also embeds competitors' brochures)."""
        if isinstance(node, dict):
            pub = node.get("publisher")
            # `publisher` is usually a dict, but some nodes carry a list — guard it.
            pub_id = pub.get("id") if isinstance(pub, dict) else None
            if (
                node.get("pageCount")
                and node.get("validUntil")
                and node.get("id") is not None
                and pub_id == self.publisher_id
            ):
                out.setdefault(str(node["id"]), node)
            for v in node.values():
                self._collect_brochures(v, out)
        elif isinstance(node, list):
            for v in node:
                self._collect_brochures(v, out)

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
        name = " ".join(x for x in [brand, product.get("name")] if x) or "Angebot"
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
            price_per_unit=_base_unit(c),
            loyalty_note=_loyalty_note(c),
            image_url=c.get("image"),
            valid_from=valid_from,
            valid_to=valid_to,
            category_path=category_path,
        )

    # -- fallback sample (overridden per chain) -------------------------------

    def _sample(self) -> List[ScrapedOffer]:
        return []


class BonialScraper(MeinprospektScraper):
    """Lidl's weekly Aktionsprospekt (kept as the original class name)."""

    publisher_id = "DE-1013"  # Lidl
    publisher_page = "https://www.meinprospekt.de/lidl"
    chain = "lidl"
    store_label = "Lidl"

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


class ReweScraper(MeinprospektScraper):
    """REWE's weekly "Dein Markt" Prospekt (publisher ``DE-1062``).

    Same structured meinprospekt pipeline as Lidl, but REWE's flyer carries no
    struck-through regular price, so most offers list a price without a discount %.
    """

    publisher_id = "DE-1062"  # REWE
    publisher_page = "https://www.meinprospekt.de/rewe-de"
    chain = "rewe"
    store_label = "REWE"

    def _sample(self) -> List[ScrapedOffer]:
        today = date.today()
        end = today + timedelta(days=6)

        def o(ext, name, price, regular, unit, brand=None):
            return ScrapedOffer(external_id=ext, name=name, price_cents=price,
                                regular_price_cents=regular, unit=unit, brand=brand,
                                valid_from=today, valid_to=end)

        # REWE flyer prices have no "old" price, so these mirror reality: no regular.
        return [
            o("rw-001", "Rauch Happy Day Saft", 199, None, "1 l", "Rauch"),
            o("rw-002", "Radeberger Pilsner", 999, None, "20x0,5 l", "Radeberger"),
            o("rw-003", "Wagner Steinofen Pizza Salami", 199, None, "320 g", "Wagner"),
            o("rw-004", "Milram Gewürzquark", 99, None, "200 g", "Milram"),
            o("rw-005", "Rügenwalder Teewurst", 149, None, "125 g", "Rügenwalder"),
        ]


def _deal(content: dict, deal_type: str) -> Optional[float]:
    for d in content.get("deals") or []:
        if d.get("type") == deal_type and d.get("max") is not None:
            return float(d["max"])
    return None


def _base_unit(content: dict) -> Optional[str]:
    """The sale per-unit price string ("1 kg = 13.33") off the SALES_PRICE deal,
    when the flyer provides one (it's empty for ~25% of offers)."""
    for d in content.get("deals") or []:
        if d.get("type") == "SALES_PRICE":
            value = (d.get("priceByBaseUnit") or "").strip()
            if value:
                return value
    return None


_BONUS_RE = re.compile(r"\d+[.,]\d{2}\s*€\s*Bonus", re.IGNORECASE)


def _loyalty_note(content: dict) -> Optional[str]:
    """A REWE bonus ("1,00 € Bonus") on an OTHER deal — collected with the loyalty
    card/app. The amount sits in the deal description or a condition's free-text
    `other` field, often amid noise, so pull just the canonical "X,XX € Bonus"."""
    for d in content.get("deals") or []:
        if d.get("type") != "OTHER":
            continue
        candidates = list((d.get("description") or "").splitlines())
        for cond in d.get("conditions") or []:
            if isinstance(cond.get("other"), str):
                candidates.append(cond["other"])
        for text in candidates:
            m = _BONUS_RE.search(text)
            if m:
                return m.group(0).strip()
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
