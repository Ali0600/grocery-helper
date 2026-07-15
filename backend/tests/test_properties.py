"""Property-based tests (Hypothesis) for the parsers that eat external junk.

These modules take strings and dicts straight from third-party feeds whose shapes have
drifted repeatedly (the Grundpreis family alone: parenthesised values, colon decimals,
missing leading amounts, labels-instead-of-values). Example tests cover the shapes we've
met; properties cover the ones we haven't. CI runs derandomized (tests/conftest.py), and
every counterexample a hunt finds is pinned as a plain example test beside the property.

The overarching invariant: **no junk input may raise.** A single malformed offer bubbling
an exception out of `_parse_offer` sends the whole chain to sample data for the week.
"""
import math
from datetime import date, datetime, timezone

from hypothesis import example, given
from hypothesis import strategies as st

from app.dedup import _norm_name
from app.scrapers.bonial import (
    MeinprospektScraper,
    _deal,
    _offer_validity,
    _parse_dt,
    _regular_from_label,
)
from app.unit_price import derive_price_per_unit, normalize_price_per_unit, unit_price_cents

# --- shared strategies -------------------------------------------------------------------

# Any JSON-ish scalar the feed could put where we expect something else.
junk_scalar = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(),  # includes NaN/inf — JSON-adjacent APIs do emit "NaN" strings
    st.text(max_size=40),
)

# Arbitrary nested JSON-ish structure (what a drifted feed field really is).
junk_json = st.recursive(
    junk_scalar,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(max_size=12), children, max_size=4),
    ),
    max_leaves=12,
)


# --- unit_price: the Grundpreis pipeline -------------------------------------------------


@given(ppu=st.text(max_size=60), price=st.one_of(st.none(), st.integers(-1000, 10_000_000)))
def test_normalize_never_raises_and_composes_with_the_sort(ppu, price):
    out = normalize_price_per_unit(ppu, price)
    assert out is None or isinstance(out, str)
    cents = unit_price_cents(out)
    assert cents is None or cents > 0


@given(ppu=st.text(max_size=60), price=st.integers(1, 1_000_000))
@example(ppu="((1 kg = 5.00))", price=399)  # nested parens: unwrap must reach a fixpoint
def test_normalize_is_idempotent(ppu, price):
    """Normalizing an already-normalized string must change nothing — otherwise the
    serializer's output depends on how many times a value passed through the pipeline."""
    once = normalize_price_per_unit(ppu, price)
    if once is not None:
        assert normalize_price_per_unit(once, price) == once


@given(
    value=st.floats(min_value=0.01, max_value=999, allow_nan=False),
    spacing=st.sampled_from(["100 g = {}", "100g = {}", "100 g={}", "100g={}"]),
)
def test_per_100g_is_never_read_as_per_kg(value, spacing):
    """The optional leading "1" must stay a literal 1: a per-100g Grundpreis read on the
    kg axis would understate the price 10x."""
    ppu = spacing.format(f"{value:.2f}")
    cents = unit_price_cents(normalize_price_per_unit(ppu, 500) or "")
    assert cents != round(value * 100) or cents is None


@given(unit=st.text(max_size=60), price=st.integers(-100, 10_000_000))
def test_derive_never_raises(unit, price):
    out = derive_price_per_unit(unit, price)
    assert out is None or isinstance(out, str)


@given(
    a=st.integers(1, 99),
    b=st.integers(1, 9999),
    template=st.sampled_from(
        ["{a}x {b} g", "{a} x {b} ml", "ca. {b} g", "Ca. {b},5 kg", "{a}-{b} g", "{b} g {a} Stück"]
    ),
)
def test_derive_refuses_multipacks_approximates_and_ranges(a, b, template):
    """Dividing a price by a multipack/approximate/range weight fabricates a €/kg — a
    wrong number is worse than none, so every trap shape must yield None."""
    assert derive_price_per_unit(template.format(a=a, b=b), 499) is None


@given(grams=st.integers(1, 5000), price=st.integers(1, 500_000))
@example(grams=2001, price=1)  # hypothesis-found: formatted as "1 kg = 0.00" — a zero
def test_derive_yields_a_sortable_value_or_nothing(grams, price):
    """Whatever derive emits must be usable by BOTH consumers (card + sort): a value that
    formats to "0.00" would display a zero Grundpreis while staying unsortable, so
    sub-half-cent results must be None rather than a lying string."""
    out = derive_price_per_unit(f"{grams}-g-Packung", price)
    if out is not None:
        assert out.startswith("1 kg = ")
        cents = unit_price_cents(out)
        assert cents is not None and cents > 0


@given(grams=st.integers(50, 5000), price=st.integers(50, 500_000))
def test_derive_divides_any_realistic_single_weight(grams, price):
    """For realistic inputs (≥50 g, ≥0.50 €) the division must always produce a value —
    the None branch above is strictly for corrupt sub-cent results."""
    out = derive_price_per_unit(f"{grams}-g-Packung", price)
    assert out is not None and unit_price_cents(out) > 0


# --- bonial: the flyer payload parsers ---------------------------------------------------


@given(value=junk_scalar)
def test_parse_dt_never_raises(value):
    out = _parse_dt(value)
    assert out is None or isinstance(out, datetime)


@given(
    sales=st.floats(min_value=0.01, max_value=10_000, allow_nan=False),
    label=st.one_of(
        junk_scalar,
        st.fixed_dictionaries(
            {"type": junk_scalar, "value": junk_scalar},
        ),
        st.fixed_dictionaries(
            {
                "type": st.sampled_from(["DISCOUNT_AMOUNT", "DISCOUNT_PERCENTAGE"]),
                "value": st.one_of(st.floats(), st.integers(-100, 200), st.text(max_size=8)),
            }
        ),
    ),
)
@example(sales=2.99, label={"type": "DISCOUNT_AMOUNT", "value": -0.5})  # inverted strike
@example(sales=2.99, label={"type": "DISCOUNT_AMOUNT", "value": float("nan")})
def test_regular_from_label_never_inverts_the_strike_price(sales, label):
    """A recovered regular price below (or equal to) the sales price is an inverted
    strike-through — the RRP path already guards this (rrp > sales); the label path must
    hold the same line, and junk must yield None, never an exception."""
    out = _regular_from_label(sales, label if isinstance(label, dict) else None)
    assert out is None or (math.isfinite(out) and out > sales)


_ISO = st.datetimes(
    min_value=datetime(2024, 1, 1),
    max_value=datetime(2030, 1, 1),
).map(lambda d: d.replace(tzinfo=timezone.utc).isoformat())

_BROCHURE_FROM = date(2026, 7, 13)
_BROCHURE_TO = date(2026, 7, 18)


@given(
    profiles=st.lists(
        st.one_of(
            junk_scalar,
            st.fixed_dictionaries(
                {
                    "validity": st.one_of(
                        junk_scalar,
                        st.fixed_dictionaries(
                            {
                                "startDate": st.one_of(junk_scalar, _ISO),
                                "endDate": st.one_of(junk_scalar, _ISO),
                            }
                        ),
                    )
                }
            ),
        ),
        max_size=5,
    )
)
def test_offer_validity_is_always_clamped_to_the_brochure(profiles):
    out = _offer_validity({"publicationProfiles": profiles}, _BROCHURE_FROM, _BROCHURE_TO)
    if out is not None:
        vf, vt = out
        assert _BROCHURE_FROM <= vf <= vt <= _BROCHURE_TO


@given(content=junk_json)
def test_deal_helpers_never_raise_on_junk(content):
    """Every per-deal helper walks `content["deals"]` — a feed that puts a string where a
    deal dict belongs must not be able to raise."""
    if not isinstance(content, dict):
        content = {"deals": content}
    assert _deal(content, "SALES_PRICE") is None or True  # value unconstrained; no raise


@given(
    content=st.fixed_dictionaries(
        {
            "id": junk_scalar,
            "deals": junk_json,
            "products": junk_json,
            "publicationProfiles": junk_json,
            "discountLabel": junk_json,
            "image": junk_scalar,
        }
    )
)
@example(
    content={  # one NaN "max" must not nuke the whole chain to sample data
        "id": 1,
        "deals": [{"type": "SALES_PRICE", "max": float("nan")}],
        "products": [],
        "publicationProfiles": [],
        "discountLabel": None,
        "image": None,
    }
)
@example(
    content={  # a string where the product dict belongs
        "id": 1,
        "deals": [{"type": "SALES_PRICE", "max": 1.99}],
        "products": ["not-a-dict"],
        "publicationProfiles": [],
        "discountLabel": None,
        "image": None,
    }
)
def test_parse_offer_never_raises_on_junk_content(content):
    """THE load-bearing property: `_offers_from_pages` has no per-offer try, so a single
    malformed offer raising inside `_parse_offer` fails the whole `_fetch_live` — and the
    chain silently serves sample data for the week. Junk must parse to an offer or None."""
    out = MeinprospektScraper._parse_offer(content, _BROCHURE_FROM, _BROCHURE_TO)
    if out is not None:
        assert out.price_cents > 0
        assert out.regular_price_cents is None or out.regular_price_cents > out.price_cents


# --- dedup: the name normalizer ----------------------------------------------------------


@given(name=st.one_of(st.none(), st.text(max_size=80)))
def test_norm_name_never_raises_is_idempotent_and_tidy(name):
    out = _norm_name(name)
    assert _norm_name(out) == out  # idempotent
    assert out == out.strip() and "  " not in out  # collapsed whitespace


@given(pages_json=junk_json)
def test_offers_from_pages_never_raises_on_junk(pages_json):
    """The walk ABOVE _parse_offer must be junk-total too — same blast radius."""
    if not isinstance(pages_json, dict):
        pages_json = {"contents": pages_json}
    out = MeinprospektScraper._offers_from_pages(pages_json, _BROCHURE_FROM, _BROCHURE_TO)
    assert isinstance(out, list)
