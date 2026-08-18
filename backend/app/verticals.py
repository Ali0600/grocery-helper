"""Which section of the app a deal belongs to — the home screen's three buttons.

The app opens on a home screen with three buttons — Grocery, Drinks and Drugstore — and
every deals surface below that is scoped to one of them. A section is a **fact about the
data**, not about a `Store` row, so this is a frozen constant rather than a DB column — no
migration, and it can't drift per-row. Same shape and spirit as
``store_locator.ACTIVE_CHAINS``.

This module deliberately imports nothing from the app: ``api/offers.py``,
``services/store_locator.py`` and ``scrapers/run.py`` all need it, and a leaf module
keeps that free of import cycles.

**Two shapes of vertical, and the difference matters.**

* Grocery and Drugstore are **chain sets** — a Rossmann in any PLZ is a drugstore, whatever
  it sells. Their chains are disjoint, so a row belongs to exactly one of them.
* Drinks (2026-08-18) is a **category set** carved out of the grocery chains: the same six
  supermarkets, restricted to ``soft_drinks`` and ``alcoholic``. Grocery names the *same*
  constant in ``excluded_categories``, so the two are one partition expressed once — a
  drink cannot go missing from both sections, or appear in both, without that single
  frozenset changing. ``tests/test_verticals.py`` pins exactly that.

**Why the split is load-bearing, not just navigation.** ``/api/offers`` caps at 2000 and
the app loads the whole set. Measured 2026-08-18 for one Berlin PLZ, deduped: all seven
grocery-and-drugstore chains as one query would be far past the cap, and **grocery alone
had reached 1926 of 2000** (lidl 434, aldi 379, penny 330, rewe 278, edeka_center 266,
edeka 239) — 96% of the ceiling, one good flyer week from silent truncation. Moving drinks
to their own section takes grocery to **1689** and gives Drinks **237**. Scoping each
section to its own query is the only reason all three fit.

Truncation is why the cap matters at all: ``/api/offers`` slices **after** a discount sort
with nulls last, so the dropped rows are disproportionately the chains that publish no
strike price. Penny joined grocery on 2026-08-11 (255 deduped) and was chosen over Netto
(461 raw) and Kaufland (723 raw) for exactly this reason; raising the cap is the
prerequisite for an eighth chain. See ``docs/DECISIONS.md``.

That is also why ``/api/offers`` defaults to **grocery** when no ``vertical`` is given,
instead of returning every chain (see ``api/offers.py``). Only app builds older than the
vertical release omit it, and those predate Drugstore entirely — they have no UI for it,
so serving them a truncated all-chains list was both over the cap and wrong.

**Adding a category-scoped vertical is a two-release sequence.** The ``vertical`` query
param is a ``Query(pattern=…)`` built from this dict, so an app asking for a section the
deployed backend doesn't know gets a **422**. Ship the backend first, confirm it serves,
then ship the app.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Tuple

#: The categories that make up the Drinks section. Named once and used **twice** below —
#: as Drinks' `categories` and as Grocery's `excluded_categories` — because those two are
#: the same statement seen from either side. A second literal here would be a partition
#: that can drift, and its failure mode is silent: a drink served in both sections, or in
#: neither. `tests/test_categories.py` pins that these are real category slugs (this
#: module cannot import `categories.py` without an import cycle).
DRINK_CATEGORIES: FrozenSet[str] = frozenset({"soft_drinks", "alcoholic"})


@dataclass(frozen=True)
class VerticalSpec:
    label: str
    chains: Tuple[str, ...]
    #: OpenStreetMap tags identifying this kind of shop, for the nearby-store locator.
    #: Supermarkets and drugstores are tagged differently (`shop=chemist` is a German
    #: Drogerie: dm/Rossmann), so a supermarket-only query cannot find them.
    osm_tags: Tuple[str, ...]
    #: Serve **only** these categories. ``None`` means "everything these chains sell" and
    #: is what makes a vertical a plain chain set. A vertical that sets this shares its
    #: chains with a home vertical, which must exclude the same categories.
    categories: Optional[FrozenSet[str]] = None
    #: Categories carved out of this vertical into a category-scoped sibling.
    excluded_categories: FrozenSet[str] = field(default_factory=frozenset)

    @property
    def is_home(self) -> bool:
        """True when this vertical owns its chains outright (a chain set, not a carve-out)."""
        return self.categories is None


VERTICALS: Dict[str, VerticalSpec] = {
    # Insertion order drives the home screen's card order and the data gate's profile order.
    "grocery": VerticalSpec(
        label="Grocery",
        chains=("lidl", "rewe", "edeka", "edeka_center", "aldi", "penny"),
        osm_tags=("shop=supermarket",),
        excluded_categories=DRINK_CATEGORIES,
    ),
    # The same six supermarkets, restricted to what you drink. Not a chain of its own: the
    # user asked for drinks out of the food list ("I'm just looking for food and it's
    # distracting"), and the cap arithmetic above made it the right answer anyway.
    # Coffee deliberately stays in Grocery (the user's call): a bag of beans is an aisle
    # you cook from, not a bottle you drink.
    "drinks": VerticalSpec(
        label="Drinks",
        chains=("lidl", "rewe", "edeka", "edeka_center", "aldi", "penny"),
        osm_tags=("shop=supermarket",),
        categories=DRINK_CATEGORIES,
    ),
    # dm is here via its **clearance** feed, not a flyer. Its meinprospekt brochure serves
    # `{"contents": []}` and always will (don't re-probe), and its 21k-product catalog is
    # everyday pricing with no discount or validity — still not a deals source. But the
    # catalog's `isSellout=true` facet is: 214 in-store items, every one with a struck
    # price. See `scrapers/dm.py`.
    "drugstore": VerticalSpec(
        label="Drugstore",
        chains=("rossmann", "dm"),
        osm_tags=("shop=chemist",),
    ),
}

#: chain slug -> the vertical that OWNS it. Built from the home verticals only, whose
#: chains are disjoint by construction; a category-scoped vertical borrows its chains and
#: so must not overwrite them here (that is what makes `CHAIN_VERTICAL["lidl"]` still
#: answer "grocery" now that Drinks exists).
CHAIN_VERTICAL: Dict[str, str] = {
    chain: vertical
    for vertical, spec in VERTICALS.items()
    if spec.is_home
    for chain in spec.chains
}


def chains_for(vertical: str) -> Tuple[str, ...]:
    """The chains in *vertical*, or () if it isn't one we know."""
    spec = VERTICALS.get(vertical)
    return spec.chains if spec else ()
