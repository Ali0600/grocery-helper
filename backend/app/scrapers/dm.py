"""dm scraper — the **Ausverkauf** (clearance) feed, via dm's public product-search API.

dm is not, and cannot be, a flyer chain: its meinprospekt publisher (`DE-909`) exists and
even lists a brochure, but that brochure's `/pages` returns `{"contents": []}` — zero
offers, ever. Don't re-probe it.

What dm *does* have is an online catalog API. Most of that catalog is everyday pricing
with no discount and no validity window, which doesn't fit the deals model — but one
facet of it does: `isSellout=true`, the site's own "Ausverkauf" page. Measured 2026-07-30:

  * **every** item carries both a current and a struck-through previous price
    (0 inverted, median discount 48%) — better strike-price coverage than any chain we
    scrape, since REWE and ALDI mostly publish none;
  * 100% have an image, a category and a stable article number;
  * the whole feed fits in ONE request (`pageSize=1000` -> 251 products), so the
    aggressive, header-less rate limiting is nearly moot. `tracked_client` still paces
    and backs off, which is what handles the bursty 429s it does return.

Three traps this parser exists to avoid, all measured:

1. **`netPrice` is net-of-VAT** — every product carries `price` (7,95 €) *and* `netPrice`
   (6,68 €), the latter ex-VAT at a rate that varies by product class (19% cosmetics,
   7% food). Reading the wrong block under-reports every price by 7-16%.
2. **The Grundpreis' leading number is the PACK SIZE, not the unit price** —
   `"0,036 kg (81,94 € je 1 kg)"`. The parenthesised part is the per-unit price, and the
   `je 1 kg` shape matches none of `unit_price.py`'s existing patterns, so we emit the
   canonical `"1 kg = 81.94"` here (same idea as `bonial._kg_price`).
3. **"Nur Online" items aren't in a branch** — 37 of 251. The app is about deals you can
   walk in and buy, so they're skipped; the flag is per-product on `eyecatchers`.

Prices are **national**: verified identical with and without a `storeId`, so unlike the
flyer chains this needs no coordinates and no location cookie.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

import httpx

from .. import metrics
from ..core.config import settings
from ..http import tracked_client
from .base import ScrapedOffer, ScrapeResult

logger = logging.getLogger(__name__)

SEARCH_URL = "https://product-search.services.dmtech.com/de/search/crawl"
PRODUCT_BASE = "https://www.dm.de"
HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "de-DE",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}
#: The whole clearance feed in one request — measured 251 products, so this is headroom,
#: not a guess. If dm ever exceeds it, `count` vs len(products) makes the truncation loud.
PAGE_SIZE = 1000

#: `eyecatchers[].alt` marking an item as not stocked in a branch.
ONLINE_ONLY_MARKER = "Nur Online Grafik"

# German money: "1.234,56 €" / "7,95 €".
_MONEY_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+),(\d{2})")
# The per-unit price inside the Grundpreis: "0,036 kg (81,94 € je 1 kg)".
_BASE_PRICE_RE = re.compile(
    r"\(\s*(\d{1,3}(?:\.\d{3})*|\d+),(\d{2})\s*€\s*je\s+1\s+(\w+)\s*\)", re.IGNORECASE
)
#: Sub-units folded onto the kg/l axis so they sort against everything else.
#: Anything else (St, Wl, m) stays as-is: displayable, correctly unsortable.
_UNIT_SCALE = {"g": ("kg", 1000), "ml": ("l", 1000)}


def _money_cents(value: Optional[str]) -> Optional[int]:
    """"7,95 €" -> 795. None when the string carries no German money amount."""
    match = _MONEY_RE.search(value or "")
    if match is None:
        return None
    return int(match.group(1).replace(".", "")) * 100 + int(match.group(2))


def _price_block(tile: dict, key: str) -> dict:
    """`tileData.price.price` — the gross block. NEVER `netPrice` (trap 1)."""
    return ((tile.get(key) or {}).get("price") or {}) if isinstance(tile.get(key), dict) else {}


def _base_unit_price(tile: dict) -> Optional[str]:
    """dm's Grundpreis -> the canonical "1 kg = X" shape the app already parses.

    Reads the parenthesised per-unit price, not the leading pack size (trap 2), and folds
    g/ml onto the kg/l axis so they're comparable with every other chain.
    """
    infos = (tile.get("price") or {}).get("tileInfos") or []
    if not infos:
        return None
    match = _BASE_PRICE_RE.search(infos[0] or "")
    if match is None:
        return None
    cents = int(match.group(1).replace(".", "")) * 100 + int(match.group(2))
    unit = match.group(3)
    scaled = _UNIT_SCALE.get(unit.lower())
    if scaled is not None:
        unit, factor = scaled
        cents *= factor
    # Units we don't fold keep the source's own casing ("St", "Wl") so the card reads
    # "1,95 €/St" rather than "/st".
    return f"1 {unit} = {cents / 100:.2f}"


def _is_online_only(tile: dict) -> bool:
    return any(
        (e or {}).get("alt") == ONLINE_ONLY_MARKER for e in (tile.get("eyecatchers") or [])
    )


class DmScraper:
    chain = "dm"
    store_label = "dm"
    #: A third source beside "coupon"/"flyer". Neither of those would be true here, and
    #: `/api/offers`' `source` query pattern is built to accept this value.
    source = "clearance"

    def __init__(self, client: Optional[httpx.Client] = None) -> None:
        self._client = client

    def fetch(self, plz: str) -> ScrapeResult:
        """dm's clearance is national, so this takes no coordinates — unlike every flyer
        scraper, which needs the PLZ's lat/lng to pick a regional brochure."""
        try:
            offers = self._fetch_live()
            return ScrapeResult(
                chain=self.chain,
                store_name=f"{self.store_label} {plz}",
                plz=plz,
                offers=offers,
            )
        except Exception as exc:
            # Nothing beats serving nothing here: dm's sample prices are invented, and the
            # clearance feed is the only place a dm price comes from, so a fabricated one has
            # no real counterpart to be corrected by. See `scrape_sample_fallback`.
            degraded = self._sample() if settings.scrape_sample_fallback else []
            metrics.record_scrape_failure(self.chain, f"{type(exc).__name__}: {exc}")
            logger.warning(
                "dm live scrape failed for plz=%s; serving %s",
                plz, "sample data" if degraded else "no offers", exc_info=exc,
            )
            return ScrapeResult(
                chain=self.chain,
                store_name=f"{self.store_label} {plz}" + (" (sample)" if degraded else ""),
                plz=plz,
                offers=degraded,
            )

    # -- live -----------------------------------------------------------------

    def _fetch_live(self) -> List[ScrapedOffer]:
        own = self._client is None
        client = self._client or tracked_client(timeout=30, headers=HEADERS)
        try:
            resp = client.get(
                SEARCH_URL,
                params={"isSellout": "true", "pageSize": PAGE_SIZE, "currentPage": 0},
            )
            resp.raise_for_status()
            payload = resp.json()
            products = payload.get("products") or []
            count = payload.get("count")
            if isinstance(count, int) and count > len(products):
                # One page is meant to hold the whole feed; if it no longer does we are
                # silently serving a subset, which must be visible rather than inferred.
                logger.warning(
                    "dm: clearance feed has %s products but one page returned %s — "
                    "raise PAGE_SIZE or paginate",
                    count,
                    len(products),
                )
            offers = [o for o in (self._parse(p) for p in products) if o is not None]
            if not offers:
                raise RuntimeError("dm returned no parseable clearance offers")
            return offers
        finally:
            if own:
                client.close()

    def _parse(self, product: dict) -> Optional[ScrapedOffer]:
        if not isinstance(product, dict):
            return None
        tile = product.get("tileData")
        if not isinstance(tile, dict):
            return None
        if _is_online_only(tile):
            return None  # not stocked in a branch (trap 3)

        gross = _price_block(tile, "price")
        price_cents = _money_cents((gross.get("current") or {}).get("value"))
        if price_cents is None:
            return None
        regular_cents = _money_cents((gross.get("previous") or {}).get("value"))
        # A "previous" price that isn't above the sale price is not a discount; drop it
        # rather than store an inverted strike price.
        if regular_cents is not None and regular_cents <= price_cents:
            regular_cents = None

        dan = product.get("dan") or tile.get("dan")
        if dan is None:
            return None
        images = tile.get("images") or []
        image_url = (images[0] or {}).get("tileSrc") if images else None
        categories = ((tile.get("trackingData") or {}).get("categories") or [])

        return ScrapedOffer(
            external_id=str(dan),
            name=(product.get("title") or "").strip() or "dm Ausverkauf",
            price_cents=price_cents,
            regular_price_cents=regular_cents,
            brand=(product.get("brandName") or "").strip() or None,
            # No caption equivalent: dm states the pack size in the title. Passing the
            # Grundpreis' pack-size fragment here would feed junk to the classifier's
            # caption layer and render oddly on the card.
            unit=None,
            price_per_unit=_base_unit_price(tile),
            image_url=image_url,
            # dm publishes no start/end for a clearance item — it simply runs until sold
            # out. NULL dates pass every serve-time validity filter; the weekly reset is
            # what clears items that have gone.
            valid_from=None,
            valid_to=None,
            category_path=[c for c in categories if isinstance(c, str) and c.strip()],
            raw=product,
        )

    # -- fallback sample ------------------------------------------------------

    def _sample(self) -> List[ScrapedOffer]:
        def o(ext, name, price, regular, brand, path, ppu=None) -> ScrapedOffer:
            return ScrapedOffer(
                external_id=ext,
                name=name,
                price_cents=price,
                regular_price_cents=regular,
                brand=brand,
                price_per_unit=ppu,
                category_path=[path],
            )

        return [
            o("dm-001", "Shampoo Repair & Care, 300 ml", 145, 295, "Balea", "Shampoo",
              "1 l = 4.83"),
            o("dm-002", "Duschgel Sensitive, 250 ml", 95, 195, "Balea", "Duschgel"),
            o("dm-003", "Zahnpasta Complete, 75 ml", 99, 189, "Dontodent", "Zahnpasta"),
            o("dm-004", "Nagellack Bold Magnetic 04", 249, 499, "CATRICE", "Nagellack"),
            o("dm-005", "Handcreme Intensiv, 100 ml", 125, 249, "alverde", "Handcreme"),
            o("dm-006", "Colorwaschmittel Pulver, 20 WL", 275, 449, "Denkmit", "Waschmittel"),
        ]
