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
  - EDEKA (publisher ``DE-220164``) -> :class:`EdekaScraper`

Flow:
  1. discover the publisher's currently-valid weekly brochure(s) from its
     meinprospekt page (the page embeds them in a Next.js ``__NEXT_DATA__`` blob)
  2. fetch each brochure's pages -> structured offers
  3. map to ScrapedOffer; the discount comes from SALES_PRICE vs REGULAR_PRICE,
     falling back to RECOMMENDED_RETAIL_PRICE (branded/non-food items print the
     struck-through price as a UVP deal — ~21% of offers carry ONLY this), then to
     the offer's discountLabel. (REWE's "Dein Markt" flyer carries neither on most
     items, so most REWE offers still list a price without a % discount.)

Offers are location-gated, so a store lat/lng is required (we reuse the one the
Lidl Plus store lookup already resolves for the postal code). Bonial soft-
throttles bursts, so this is meant to run weekly with caching; on any failure we
fall back to sample data so the rest of the app keeps working.
"""
from __future__ import annotations

import json
import logging
import math
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from ..core.config import settings
from ..http import tracked_client
from .base import ScrapedOffer, ScrapeResult

logger = logging.getLogger(__name__)

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
# Between flyer weeks (e.g. Sunday) last week's brochure has ended and next week's
# hasn't started, but meinprospekt already publishes next week's with a `validFrom` a
# day or two out. Look this far ahead for it before falling back to sample data.
UPCOMING_LOOKAHEAD_DAYS = 8
# Validity timestamps are Berlin-midnight boundaries expressed in UTC; convert with the
# real tz (handles CET/CEST) so day-limited windows land on the right calendar days
# regardless of where the scraper runs.
_BERLIN = ZoneInfo("Europe/Berlin")
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
        # Two attempts, but ONLY for an "empty answer" (our own RuntimeError: no brochure in the
        # list, or a brochure that parsed to zero offers). Those come back as HTTP 200, so the
        # transport-level retry in `tracked_client` never sees them — the aggregator soft-throttles
        # a burst by serving less content rather than an error. Proven on 2026-07-19: three chains
        # degraded to samples on one attempt and the identical request returned the full list ten
        # minutes later. An HTTP error is NOT retried here: 5xx/429 are already handled upstream,
        # and a 403 is a hard block that retrying only worsens.
        for attempt in (1, 2):
            try:
                offers = self._fetch_live(lat, lng, plz)
                if not offers:
                    raise RuntimeError(f"{self.chain}: meinprospekt returned no flyer offers")
                return ScrapeResult(
                    chain=self.chain, store_name=store_name, plz=plz,
                    lat=lat, lng=lng, offers=offers,
                )
            except RuntimeError as exc:
                if attempt == 1:
                    logger.warning(
                        "%s flyer scrape came back empty (%s); retrying once in %.0fs",
                        self.chain, exc, settings.scrape_thin_retry_s,
                    )
                    time.sleep(settings.scrape_thin_retry_s)
                    continue
                break
            except Exception:
                break
        logger.warning(
            "%s flyer scrape failed for plz=%s; serving sample data",
            self.chain, plz, exc_info=True,
        )
        return ScrapeResult(
            chain=self.chain, store_name=store_name, plz=plz,
            lat=lat, lng=lng, offers=self._sample(),
        )

    # -- live -----------------------------------------------------------------

    def _fetch_live(self, lat: float, lng: float, plz: Optional[str] = None) -> List[ScrapedOffer]:
        own = self._client is None
        client = self._client or tracked_client(timeout=30, headers=HEADERS)
        # Pin discovery to the *target* location (not the scraping host's IP) so the same
        # PLZ yields the same regional brochures from any machine — see `_location_cookie`.
        cookie = _location_cookie(lat, lng, plz)
        try:
            offers: dict = {}
            for b in self._current_brochures(client, cookie):
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

    def _current_brochures(self, client: httpx.Client, cookie: str = "") -> List[dict]:
        headers = {"Accept": "text/html"}
        if cookie:
            headers["Cookie"] = cookie
        resp = client.get(self.publisher_page, headers=headers)
        resp.raise_for_status()
        m = _NEXT_DATA_RE.search(resp.text)
        if not m:
            raise RuntimeError("publisher page missing __NEXT_DATA__")
        found: dict = {}
        self._collect_brochures(json.loads(m.group(1)), found)
        return _select_brochures(found, datetime.now(timezone.utc), self.chain)

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
        for page in _dicts(pages_json.get("contents")):
            for wrapper in _dicts(page.get("offers")):
                content = wrapper.get("content")
                if not isinstance(content, dict):
                    continue
                offer = cls._parse_offer(content, valid_from, valid_to)
                if offer:
                    out.append(offer)
        return out

    @staticmethod
    def _parse_offer(c: dict, valid_from, valid_to) -> Optional[ScrapedOffer]:
        """Junk-total: any malformed content dict parses to an offer or None, never an
        exception — `_offers_from_pages` has no per-offer try, so a single raising offer
        would fail the whole `_fetch_live` and silently degrade the chain to sample data
        for the week. Property-tested against arbitrary JSON-shaped junk."""
        sales = _deal(c, "SALES_PRICE")
        if sales is None or sales <= 0:
            return None  # not a (sanely) priced offer
        products = _dicts(c.get("products"))
        product = products[0] if products else {}
        brand = product.get("brandName")
        if not isinstance(brand, str) or not brand.strip():
            brand = None
        pname = product.get("name")
        name_parts = [x for x in (brand, pname) if isinstance(x, str) and x]
        name = " ".join(name_parts) or "Angebot"
        descs = _dicts(product.get("description"))
        unit = descs[0].get("paragraph") if descs else None
        if not isinstance(unit, str):
            unit = None
        regular = _deal(c, "REGULAR_PRICE")
        if regular is None:
            # Branded/non-food items carry the struck-through price as an RRP/UVP deal
            # instead (McCain 2.99 statt UVP 4.89) — ~21% of offers had ONLY this. Guard
            # rrp > sales so an inverted strike price is never stored (fail closed).
            rrp = _deal(c, "RECOMMENDED_RETAIL_PRICE")
            if rrp is not None and rrp > sales:
                regular = rrp
        if regular is None:
            label = c.get("discountLabel")
            regular = _regular_from_label(sales, label if isinstance(label, dict) else None)
        category_path = [
            cp["name"]
            for cp in _dicts(product.get("categoryPaths"))
            if isinstance(cp.get("name"), str) and cp["name"]
        ]
        # Prefer the offer's own on-sale window (day-limited specials) over the brochure's.
        own = _offer_validity(c, valid_from, valid_to)
        vf, vt = own if own else (valid_from, valid_to)
        image = c.get("image")
        return ScrapedOffer(
            external_id=str(c.get("id")),
            name=name,
            price_cents=round(sales * 100),
            regular_price_cents=round(regular * 100) if regular else None,
            brand=brand,
            unit=unit,
            price_per_unit=_base_unit(c) or _kg_price(c, sales),
            loyalty_note=_loyalty_note(c),
            app_price_cents=_app_price(c),
            image_url=image if isinstance(image, str) else None,
            valid_from=vf,
            valid_to=vt,
            category_path=category_path,
            raw=c,
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


class EdekaScraper(MeinprospektScraper):
    """EDEKA's weekly Prospekt (national publisher ``DE-220164``).

    EDEKA is a regional co-op; ``DE-220164`` is the national publisher and the
    brochure pages are location-gated (lat/lng), so a Berlin PLZ gets Berlin-ish
    offers. Like REWE's "Dein Markt", the flyer usually carries no struck-through
    regular price, so most offers list a price without a discount %.
    """

    publisher_id = "DE-220164"  # EDEKA
    publisher_page = "https://www.meinprospekt.de/edeka"
    chain = "edeka"
    store_label = "Edeka"

    def _sample(self) -> List[ScrapedOffer]:
        today = date.today()
        end = today + timedelta(days=6)

        def o(ext, name, price, regular, unit, brand=None):
            return ScrapedOffer(external_id=ext, name=name, price_cents=price,
                                regular_price_cents=regular, unit=unit, brand=brand,
                                valid_from=today, valid_to=end)

        # EDEKA flyer prices have no "old" price, so these mirror reality: no regular.
        return [
            o("ed-001", "Gut&Günstig Weizenmehl Type 405", 49, None, "1 kg", "Gut&Günstig"),
            o("ed-002", "EDEKA Bio Freilandeier", 299, None, "10 Stück", "EDEKA Bio"),
            o("ed-003", "Wiesenhof Hähnchenbrustfilet", 599, None, "400 g", "Wiesenhof"),
            o("ed-004", "Gut&Günstig Sonnenblumenöl", 199, None, "1 l", "Gut&Günstig"),
            o("ed-005", "Bauern Gut Schweinenackensteaks", 399, None, "1 kg", "Bauern Gut"),
        ]


class EdekaCenterScraper(MeinprospektScraper):
    """E center (EDEKA's hypermarket format) — its own meinprospekt publisher
    ``DE-3443181`` at ``/edekacenter-de``, separate from the regular EDEKA publisher.
    Same location-gated pipeline; kept a distinct chain/store so its (usually larger)
    weekly Prospekt can be compared against the standard EDEKA flyer. Like EDEKA/REWE,
    the flyer carries no struck-through regular price (so mostly no discount %)."""

    publisher_id = "DE-3443181"  # E center (EDEKA Center)
    publisher_page = "https://www.meinprospekt.de/edekacenter-de"
    chain = "edeka_center"
    store_label = "E center"

    def _sample(self) -> List[ScrapedOffer]:
        today = date.today()
        end = today + timedelta(days=6)

        def o(ext, name, price, regular, unit, brand=None):
            return ScrapedOffer(external_id=ext, name=name, price_cents=price,
                                regular_price_cents=regular, unit=unit, brand=brand,
                                valid_from=today, valid_to=end)

        return [
            o("ec-001", "Gut&Günstig Weizenmehl Type 405", 45, None, "1 kg", "Gut&Günstig"),
            o("ec-002", "Coca-Cola", 999, None, "12x1 l", "Coca-Cola"),
            o("ec-003", "Wiesenhof Hähnchenschenkel", 299, None, "1 kg", "Wiesenhof"),
            o("ec-004", "Barilla Spaghetti No.5", 99, None, "500 g", "Barilla"),
            o("ec-005", "EDEKA Bio Vollmilch", 119, None, "1 l", "EDEKA Bio"),
        ]


class _AldiScraper(MeinprospektScraper):
    """ALDI's weekly Prospekt. ALDI is **two independent companies** with disjoint
    territories, each with its own publisher — and unlike REWE/EDEKA, BOTH publisher pages
    are *national*: they ignore the `location` cookie and serve the identical brochure to
    Berlin and Munich (measured). So the source will not stop us from showing a Berlin user
    ALDI SÜD deals from ~300 km away — `run.py` must pick the division that actually operates
    at the postal code (`store_locator.aldi_division`).

    Both subclasses deliberately share ``chain = "aldi"``: the two never coexist in one
    place, so there is nothing to compare (unlike EDEKA vs E center) and the app shows a
    single "Aldi". The division stays visible in the store name ("ALDI Nord 10115").
    """

    chain = "aldi"

    def _sample(self) -> List[ScrapedOffer]:
        today = date.today()
        end = today + timedelta(days=6)

        def o(ext, name, price, regular, unit, brand=None):
            return ScrapedOffer(external_id=ext, name=name, price_cents=price,
                                regular_price_cents=regular, unit=unit, brand=brand,
                                valid_from=today, valid_to=end)

        # Most ALDI offers print no struck-through price (72% live), like REWE's flyer.
        return [
            o("al-001", "Rispentomaten", 149, None, "500 g"),
            o("al-002", "MILSANI Frische Vollmilch", 115, None, "1 l", "MILSANI"),
            o("al-003", "Gut Bio Eier", 249, 299, "10 Stück", "Gut Bio"),
            o("al-004", "Trader Joe's Walnusskerne", 199, None, "200 g", "Trader Joe's"),
        ]


class AldiNordScraper(_AldiScraper):
    """ALDI Nord (publisher ``DE-75``) — northern/eastern Germany, incl. Berlin."""

    publisher_id = "DE-75"
    publisher_page = "https://www.meinprospekt.de/aldinord-de"
    store_label = "ALDI Nord"


class AldiSuedScraper(_AldiScraper):
    """ALDI SÜD (publisher ``DE-77``) — southern/western Germany."""

    publisher_id = "DE-77"
    publisher_page = "https://www.meinprospekt.de/aldisued-de"
    store_label = "ALDI SÜD"


def _location_cookie(lat: float, lng: float, plz: Optional[str] = None) -> str:
    """Build the meinprospekt `location` cookie for the target coordinates.

    The publisher page picks which *regional* brochures to show from this cookie
    (which the site otherwise seeds from the request's IP geolocation). Pinning it to
    the scraped PLZ's coords makes discovery both correct (Berlin gets Berlin flyers,
    not the datacenter's region) and deterministic across machines — without it, a
    Frankfurt-hosted server and a Berlin laptop scrape different brochures for the
    same PLZ. The amount of detail mirrors the cookie the site sets itself."""
    payload = {"lat": lat, "lng": lng, "countryCode": "DE"}
    if plz:
        payload["zip"] = plz
    return "location=" + quote(json.dumps(payload, separators=(",", ":")))


def _dicts(value) -> List[dict]:
    """Only the dict elements of a maybe-list. The feed's list-of-objects fields have
    drifted before; a stray scalar where an object belongs must be skipped, not raised —
    one raising element fails the whole chain to sample data."""
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, dict)]


def _deal(content: dict, deal_type: str) -> Optional[float]:
    for d in _dicts(content.get("deals")):
        if d.get("type") == deal_type and d.get("max") is not None:
            try:
                value = float(d["max"])
            except (TypeError, ValueError):
                continue
            # A JSON-adjacent "NaN"/"Infinity" string parses as a float but blows up
            # round() downstream — treat it as no price, like any other junk.
            if math.isfinite(value):
                return value
    return None


def _base_unit(content: dict) -> Optional[str]:
    """The sale per-unit price string ("1 kg = 13.33") off the SALES_PRICE deal,
    when the flyer provides one (it's empty for ~25% of offers)."""
    for d in _dicts(content.get("deals")):
        if d.get("type") == "SALES_PRICE":
            raw = d.get("priceByBaseUnit")
            value = raw.strip() if isinstance(raw, str) else ""
            if value:
                return value
    return None


def _kg_price(content: dict, sales: float) -> Optional[str]:
    """By-weight items (loose melon/meat) flag the SALES_PRICE with a `kg-Preis`
    condition — the advertised price IS the per-kg price (Honigmelone 1,19 €/kg) while
    `priceByBaseUnit` is empty. Emit the Lidl-coupon Grundpreis shape ("1 kg = 1.19")
    that unit_price_cents + the app's fmtPricePerUnit already parse. The condition must
    normalize to exactly "kg-preis": a REWE travel offer carries "Festpreis" inside a
    long condition string and must NOT match."""
    for d in _dicts(content.get("deals")):
        if d.get("type") != "SALES_PRICE":
            continue
        for cond in _dicts(d.get("conditions")):
            other = cond.get("other")
            if isinstance(other, str) and other.strip().rstrip("*").lower() == "kg-preis":
                return f"1 kg = {sales:.2f}"
    return None


_BONUS_RE = re.compile(r"\d+[.,]\d{2}\s*€\s*Bonus", re.IGNORECASE)


def _loyalty_note(content: dict) -> Optional[str]:
    """A REWE bonus ("1,00 € Bonus") on an OTHER deal — collected with the loyalty
    card/app. The amount sits in the deal description or a condition's free-text
    `other` field, often amid noise, so pull just the canonical "X,XX € Bonus"."""
    for d in _dicts(content.get("deals")):
        if d.get("type") != "OTHER":
            continue
        desc = d.get("description")
        candidates = list(desc.splitlines()) if isinstance(desc, str) else []
        for cond in _dicts(d.get("conditions")):
            if isinstance(cond.get("other"), str):
                candidates.append(cond["other"])
        for text in candidates:
            m = _BONUS_RE.search(text)
            if m:
                return m.group(0).strip()
    return None


def _app_price(content: dict) -> Optional[int]:
    """The app-coupon price (cents) from a `SPECIAL_PRICE` deal whose condition marks
    it as app-gated ("APP-PREIS", "Nur mit App", "Exklusiv mit der App", …) — the
    lower price you pay with the chain's app. None otherwise: Payback, "6 für"
    multibuy, "ab 2 Kisten" bulk and day-only specials are excluded on purpose (they
    aren't a simple per-item price)."""
    for d in _dicts(content.get("deals")):
        if d.get("type") != "SPECIAL_PRICE" or d.get("max") is None:
            continue
        for cond in _dicts(d.get("conditions")):
            other = cond.get("other")
            if isinstance(other, str) and "app" in other.lower():
                try:
                    return round(float(d["max"]) * 100)
                except (TypeError, ValueError):
                    return None
    return None


def _regular_from_label(sales: float, label: Optional[dict]) -> Optional[float]:
    """Recover a regular price from the offer's discount badge when REGULAR_PRICE
    is absent: a "-0.50 €" amount or a "-20 %" percentage both imply it.

    Guards (property-tested): the value must be a finite positive number — a zero or
    negative amount would store an inverted strike price (the RRP path already holds this
    line with ``rrp > sales``), and a NaN would blow up ``round()`` in ``_parse_offer``,
    failing the whole chain to sample data over one bad badge."""
    if not label:
        return None
    try:
        value = float(label.get("value"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    kind = label.get("type")
    regular = None
    if kind == "DISCOUNT_AMOUNT":
        regular = round(sales + value, 2)
    elif kind == "DISCOUNT_PERCENTAGE" and value < 100:
        regular = round(sales / (1 - value / 100), 2)
    # Strictly above the sales price, AFTER rounding — a 0.5% badge on a 0,50 € item
    # rounds back to the sales price itself, and an equal strike-through is meaningless.
    return regular if regular is not None and regular > sales else None


def _offer_validity(
    content: dict, brochure_from: date, brochure_to: date
) -> Optional[Tuple[date, date]]:
    """The offer's own on-sale window from ``publicationProfiles[].validity``, as Berlin
    calendar dates clamped to the brochure window — this is how day-limited specials (a
    Lidl Thu–Sat "Wochenend-Kracher", a Friday-only deal) are expressed; without it every
    offer reads as valid the whole brochure week.

    Returns the **union** of profile windows that overlap the brochure (so a full-week
    offer that also appears in a weekend sub-publication isn't wrongly restricted), or None
    when there's no usable profile (caller keeps the brochure dates). ``endDate`` is an
    *exclusive* next-midnight boundary, so the last valid day is ``end - 1s``.
    """
    starts: List[date] = []
    ends: List[date] = []
    for pp in _dicts(content.get("publicationProfiles")):
        validity = pp.get("validity")
        if not isinstance(validity, dict):
            continue
        sd, ed = _parse_dt(validity.get("startDate")), _parse_dt(validity.get("endDate"))
        if not (sd and ed):
            continue
        d0 = sd.astimezone(_BERLIN).date()
        d1 = (ed.astimezone(_BERLIN) - timedelta(seconds=1)).date()
        if d1 < d0 or d1 < brochure_from or d0 > brochure_to:
            continue  # malformed, or doesn't overlap this brochure
        starts.append(max(d0, brochure_from))
        ends.append(min(d1, brochure_to))
    if not starts:
        return None
    return min(starts), max(ends)


def _select_brochures(found: dict, now: datetime, chain: str) -> List[dict]:
    """Pick which weekly brochure(s) to scrape from all the publisher lists.

    Normally that's the currently-valid weekly brochure(s) (``validFrom <= now <=
    validUntil``). Between flyer weeks — e.g. Sunday, when last week's brochure has
    ended and next week's hasn't started — meinprospekt already lists next week's
    brochure with a ``validFrom`` a day or two out; serve the soonest of those rather
    than falling back to sample data. Long-running (non-weekly) brochures are ignored
    via ``MAX_FLYER_DAYS``.
    """
    active: List[Tuple[datetime, dict]] = []
    upcoming: List[Tuple[datetime, dict]] = []
    for bid, b in found.items():
        vf, vu = _parse_dt(b.get("validFrom")), _parse_dt(b.get("validUntil"))
        if not (vf and vu) or (vu - vf).days > MAX_FLYER_DAYS:
            continue  # undated, or a long-running (non-weekly) brochure
        entry = {"id": bid, "valid_from": vf.date(), "valid_to": vu.date()}
        if vf <= now <= vu:
            active.append((vf, entry))
        elif now < vf <= now + timedelta(days=UPCOMING_LOOKAHEAD_DAYS):
            upcoming.append((vf, entry))
    if active:
        return [e for _, e in active]
    if upcoming:
        # Serve only the nearest upcoming week, not the one after it.
        earliest = min(vf for vf, _ in upcoming)
        return [e for vf, e in upcoming if (vf - earliest).days <= 1]
    raise RuntimeError(f"no active weekly brochure for {chain}")


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(value))  # +0000 -> +00:00
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
