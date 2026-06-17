from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class ScrapedOffer:
    """A single offer as pulled from a store, before normalization."""

    external_id: str
    name: str
    price_cents: int
    regular_price_cents: Optional[int] = None
    brand: Optional[str] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    # Source taxonomy nodes (Bonial categoryPaths), used as a categorization
    # signal; empty for sources that don't provide one (e.g. Lidl Plus coupons).
    category_path: List[str] = field(default_factory=list)


@dataclass
class ScrapeResult:
    """The output of one scraper run for one store."""

    chain: str
    store_name: str
    plz: str
    market_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    offers: List[ScrapedOffer] = field(default_factory=list)
