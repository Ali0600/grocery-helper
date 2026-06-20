from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class OfferOut(BaseModel):
    id: int
    store_id: int
    chain: str
    store_name: str
    source: str  # "coupon" (Lidl Plus) or "flyer" (Prospekt)
    name: str
    brand: Optional[str] = None
    category: str
    category_label: str
    # Product sub-group within the category (e.g. "avocado" inside fruits), so the
    # app can cluster competing offers under a header. None = doesn't group.
    group: Optional[str] = None
    group_label: Optional[str] = None
    price_cents: int
    regular_price_cents: Optional[int] = None
    discount_pct: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[str] = None  # "1 kg = 13.33", formatted client-side
    # Normalized cents per kg/litre for the "cheapest €/kg" sort; None if the
    # per-unit basis isn't comparable (per-piece, etc.).
    unit_price_cents: Optional[int] = None
    loyalty_note: Optional[str] = None  # REWE card bonus, e.g. "1,00 € Bonus"
    app_price_cents: Optional[int] = None  # EDEKA app-coupon price (below price_cents)
    image_url: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class CategoryCount(BaseModel):
    category: str
    label: str
    count: int


class StoreOut(BaseModel):
    id: int
    chain: str
    name: str
    plz: str
    market_code: Optional[str] = None


class NearbyStoreOut(BaseModel):
    chain: str
    label: str
    name: str
    address: Optional[str] = None
    lat: float
    lng: float
    distance_m: int
    active: bool  # True for chains we scrape deals for (lidl/rewe)


class OptimizeRequest(BaseModel):
    categories: List[str]
    store_count: int = 1  # 1 = single best store, 2+ = cherry-pick across stores
    plz: Optional[str] = None


class StoreBasket(BaseModel):
    store_id: int
    chain: str
    name: str
    items: List[OfferOut]
    subtotal_cents: int


class OptimizeResponse(BaseModel):
    store_count: int
    baskets: List[StoreBasket]
    total_cents: int
    missing_categories: List[str]
    single_store_total_cents: Optional[int] = None
    savings_cents: Optional[int] = None
