from __future__ import annotations

from .categories import label
from .models import Offer
from .schemas import OfferOut


def offer_to_out(offer: Offer) -> OfferOut:
    """Build the API representation of an Offer (pulls chain/name from its store)."""
    return OfferOut(
        id=offer.id,
        store_id=offer.store_id,
        chain=offer.store.chain,
        store_name=offer.store.name,
        name=offer.name,
        brand=offer.brand,
        category=offer.category,
        category_label=label(offer.category),
        price_cents=offer.price_cents,
        regular_price_cents=offer.regular_price_cents,
        discount_pct=offer.discount_pct,
        unit=offer.unit,
        image_url=offer.image_url,
        valid_from=offer.valid_from,
        valid_to=offer.valid_to,
    )
