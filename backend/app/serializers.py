from __future__ import annotations

from .categories import label
from .models import Offer
from .product_group import product_group
from .schemas import OfferOut
from .unit_price import derive_price_per_unit, unit_price_cents
from .validity import is_day_limited, valid_days_label


def offer_to_out(offer: Offer) -> OfferOut:
    """Build the API representation of an Offer (pulls chain/name from its store)."""
    group, group_label = product_group(offer.name, offer.brand, offer.category)
    # Fall back to a per-unit price derived from the quantity when the source omitted
    # the Grundpreis (e.g. produce sold per "1 kg") so the card + €/kg sort still work.
    price_per_unit = offer.price_per_unit or derive_price_per_unit(
        offer.unit, offer.price_cents
    )
    return OfferOut(
        id=offer.id,
        store_id=offer.store_id,
        chain=offer.store.chain,
        store_name=offer.store.name,
        source=offer.source,
        name=offer.name,
        brand=offer.brand,
        category=offer.category,
        category_label=label(offer.category),
        group=group,
        group_label=group_label,
        price_cents=offer.price_cents,
        regular_price_cents=offer.regular_price_cents,
        discount_pct=offer.discount_pct,
        unit=offer.unit,
        price_per_unit=price_per_unit,
        unit_price_cents=unit_price_cents(price_per_unit),
        loyalty_note=offer.loyalty_note,
        app_price_cents=offer.app_price_cents,
        image_url=offer.image_url,
        valid_from=offer.valid_from,
        valid_to=offer.valid_to,
        valid_days=valid_days_label(offer.valid_from, offer.valid_to),
        day_limited=is_day_limited(offer.valid_from, offer.valid_to),
    )
