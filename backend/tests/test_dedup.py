"""Tests for collapsing duplicate offers (same product across brochures/sources)."""
from app.dedup import dedup_offers
from app.models import Offer


def _o(id, name, price, source="flyer", disc=None, store=1, ppu=None):
    return Offer(
        id=id, store_id=store, name=name, price_cents=price,
        source=source, discount_pct=disc, price_per_unit=ppu, category="x",
    )


def test_collapses_same_product_across_brochures_and_sources():
    # The real shape: one coupon + two flyer rows for the same product/price.
    offers = [
        _o(1, "Sonnencrusti", 98, "coupon", None),
        _o(2, "Sonnencrusti", 98, "flyer", 33.3),
        _o(3, "Sonnencrusti", 98, "flyer", 33.3),
    ]
    out = dedup_offers(offers)
    assert len(out) == 1
    assert out[0].discount_pct == 33.3  # prefers a discounted, flyer row


def test_keeps_distinct_products():
    offers = [_o(1, "A", 100), _o(2, "B", 100), _o(3, "A", 200)]
    assert len(dedup_offers(offers)) == 3  # different name or price -> kept


def test_name_match_is_case_and_space_insensitive():
    assert len(dedup_offers([_o(1, " Beef ", 100), _o(2, "beef", 100)])) == 1


def test_curly_vs_straight_apostrophe_collapses():
    # Real case: two brochures spelled it with ' and ’.
    offers = [_o(1, "Butcher's Angus Patties", 1149), _o(2, "Butcher’s Angus Patties", 1149)]
    assert len(dedup_offers(offers)) == 1


def test_collapses_guillemets_and_quality_grade():
    # Real case: the same REWE avocado in two brochures — one wraps the variety in
    # German quotes and adds a produce grade ("»Hass«, Kl. I"), the other doesn't.
    offers = [
        _o(1, "REWE Feine Welt Essreife Avocado »Hass«, Kl. I", 179),
        _o(2, "REWE Feine Welt Essreife Avocado Hass", 179),
    ]
    assert len(dedup_offers(offers)) == 1


def test_grade_strip_does_not_overmerge_distinct_products():
    # Stripping the "Kl. I" grade must not collapse genuinely different products.
    offers = [_o(1, "Tafeläpfel Elstar", 199), _o(2, "Tafeläpfel Braeburn", 199)]
    assert len(dedup_offers(offers)) == 2


def test_same_product_at_different_stores_not_merged():
    assert len(dedup_offers([_o(1, "A", 100, store=1), _o(2, "A", 100, store=2)])) == 2


def test_prefers_flyer_over_coupon_on_a_tie():
    out = dedup_offers([_o(1, "X", 100, "coupon", 20.0), _o(2, "X", 100, "flyer", 20.0)])
    assert out[0].source == "flyer"  # richer row (image / categoryPath / per-unit)


def test_prefers_the_copy_that_has_the_per_unit_price():
    # Same flyer product across two brochures; only one crop carries the €/kg —
    # keep that one so the "Cheapest €/kg" sort doesn't lose the item.
    out = dedup_offers([
        _o(1, "Rumpsteak", 999, ppu=None),
        _o(2, "Rumpsteak", 999, ppu="1 kg = 39.96"),
    ])
    assert len(out) == 1 and out[0].price_per_unit == "1 kg = 39.96"
