"""Lidl scraper — live, via the public Lidl Plus store/offers endpoints.

These are the same endpoints the Lidl Plus Android app uses; the store and
offers routes currently need no login. Flow:

  1. resolve the nearest store for a postal code   (stores.lidlplus.com)
  2. fetch that store's current offers              (offers.lidlplus.com)

Prices come as floats in euros with a separate struck-through "old" price, so we
get exact % discounts. If anything fails (endpoint change, offline, blocked),
`fetch()` falls back to sample data so the rest of the app keeps working.

Endpoints reverse-engineered from github.com/EvickaStudio/lidl-discounts.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

import httpx

from ..http import tracked_client
from .base import ScrapedOffer, ScrapeResult

logger = logging.getLogger(__name__)

STORES_URL = "https://stores.lidlplus.com/api"
OFFERS_URL = "https://offers.lidlplus.com/app/api"
APP_VERSION = "17.0.5"
HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "de-DE",
    "User-Agent": f"LidlPlus/{APP_VERSION} Android okhttp/4.12.0",
    "X-Client-Version": APP_VERSION,
    "X-Client-Platform": "android",
}
# Berlin center; only used to rank store-autocomplete results by distance.
BERLIN_LAT, BERLIN_LNG = 52.52, 13.405


class LidlScraper:
    chain = "lidl"
    country = "DE"
    source = "coupon"  # Lidl Plus app coupons

    def __init__(self, client: Optional[httpx.Client] = None) -> None:
        self._client = client

    def fetch(self, plz: str) -> ScrapeResult:
        try:
            store, offers = self._fetch_live(plz)
            loc = store.get("location") or {}
            return ScrapeResult(
                chain=self.chain,
                store_name=store.get("name") or f"Lidl {plz}",
                plz=plz,
                market_code=store.get("storeKey"),
                lat=loc.get("latitude"),
                lng=loc.get("longitude"),
                offers=offers,
            )
        except Exception:
            # Any live-scrape failure falls back to sample data so the system
            # stays up; log it so the degradation is visible (not silent).
            logger.warning(
                "Lidl live scrape failed for plz=%s; serving sample data", plz, exc_info=True
            )
            return ScrapeResult(
                chain=self.chain,
                store_name=f"Lidl {plz} (sample)",
                plz=plz,
                offers=self._sample(),
            )

    # -- live -----------------------------------------------------------------

    def _fetch_live(self, plz: str) -> Tuple[dict, List[ScrapedOffer]]:
        own = self._client is None
        client = self._client or tracked_client(timeout=25, headers=HEADERS)
        try:
            store = self._nearest_store(client, plz)
            store_key = store.get("storeKey")
            if not store_key:
                raise RuntimeError(f"No Lidl store with a storeKey for PLZ {plz}")
            resp = client.get(f"{OFFERS_URL}/v4/{self.country}/{store_key}/offers")
            resp.raise_for_status()
            parsed = [self._parse(o) for o in resp.json().get("offers", [])]
            offers = [o for o in parsed if o is not None]
            if not offers:
                raise RuntimeError("Lidl returned no parseable offers")
            return store, offers
        finally:
            if own:
                client.close()

    def _nearest_store(self, client: httpx.Client, plz: str) -> dict:
        resp = client.get(
            f"{STORES_URL}/v1/autocomplete/{self.country}",
            params={
                "input": plz,
                "language": "de",
                "latitude": BERLIN_LAT,
                "longitude": BERLIN_LNG,
            },
        )
        resp.raise_for_status()
        candidates = [s for s in resp.json() if s.get("storeKey")]
        if not candidates:
            raise RuntimeError(f"No Lidl stores found for PLZ {plz}")
        candidates.sort(
            key=lambda s: s["distance"] if s.get("distance") is not None else float("inf")
        )
        return candidates[0]

    def _parse(self, o: dict) -> Optional[ScrapedOffer]:
        pb = o.get("priceBox") or {}
        price = pb.get("largePartNumeric")
        if price is None:
            return None  # coupon / non-priced promo — skip
        regular = pb.get("smallPartNumeric")
        return ScrapedOffer(
            external_id=str(o.get("id") or o.get("title") or price),
            name=(o.get("title") or "").strip() or "Lidl Angebot",
            price_cents=round(float(price) * 100),
            regular_price_cents=round(float(regular) * 100) if regular is not None else None,
            brand=o.get("brand") or None,
            unit=self._unit(o),
            # The sale per-unit price (e.g. "1 kg = 1.93"); separate from `unit`,
            # which still falls back to this string only when packaging is absent.
            price_per_unit=(o.get("pricePerUnit") or "").strip() or None,
            image_url=o.get("imageUrl"),
            valid_from=self._parse_date(o.get("startValidityDate")),
            valid_to=self._parse_date(o.get("endValidityDate")),
        )

    @staticmethod
    def _unit(o: dict) -> Optional[str]:
        pack = o.get("packaging")
        if pack:
            first = pack.splitlines()[0].strip()
            if first:
                return first
        ppu = o.get("pricePerUnit")
        return ppu.strip() if ppu else None

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    # -- fallback sample ------------------------------------------------------

    def _sample(self) -> List[ScrapedOffer]:
        today = date.today()
        end = today + timedelta(days=6)

        def o(ext, name, price, regular, unit, brand=None) -> ScrapedOffer:
            return ScrapedOffer(
                external_id=ext,
                name=name,
                price_cents=price,
                regular_price_cents=regular,
                unit=unit,
                brand=brand,
                valid_from=today,
                valid_to=end,
            )

        return [
            o("ld-001", "Frisches Rinderhackfleisch", 249, 349, "500 g"),
            o("ld-002", "Hähnchenschnitzel", 399, 549, "400 g", "Metzgerfrisch"),
            o("ld-003", "Deutsche Markenbutter", 139, 239, "250 g", "Milbona"),
            o("ld-004", "Erdbeeren", 199, 299, "500 g"),
            o("ld-005", "Bananen", 129, 169, "1 kg"),
            o("ld-006", "Kartoffeln festkochend", 199, 299, "2 kg"),
            o("ld-007", "Gouda jung am Stück", 179, 259, "400 g", "Milbona"),
            o("ld-008", "Tiefkühl Pizza Salami", 199, 299, "320 g", "Trattoria Alfredo"),
            o("ld-009", "Frische Vollmilch 3,5%", 109, 135, "1 l", "Milbona"),
            o("ld-010", "Cola Mix", 449, 599, "6x1,5 l", "Freeway"),
            o("ld-011", "Lachsfilet", 399, 549, "240 g"),
            o("ld-012", "Tomaten Rispe", 149, 199, "500 g"),
        ]
