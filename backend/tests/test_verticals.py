"""The section registry — and the one invariant a category-scoped section rests on.

`verticals.py` used to be a plain chain→section map, where "a row belongs to exactly one
section" was true by construction. Drinks broke that: it borrows the grocery chains and
takes two categories with it, so the partition is now something two entries have to
*agree* about. These tests are that agreement, checked over the data rather than over the
two names that happen to exist today — a section added later inherits every check here
without anyone remembering to add a case.
"""
from __future__ import annotations

import pytest

from app.categories import CATEGORIES
from app.verticals import CHAIN_VERTICAL, DRINK_CATEGORIES, VERTICALS, chains_for

CARVED = {slug: s for slug, s in VERTICALS.items() if s.categories is not None}
HOMES = {slug: s for slug, s in VERTICALS.items() if s.is_home}


def test_every_carved_out_category_is_excluded_by_the_section_it_was_taken_from():
    """The partition, stated once and generically.

    If a home section keeps serving a category a sibling also claims, the offer shows up
    in BOTH — the deals list, the chips and the basket all double-count it. This is the
    check that makes `DRINK_CATEGORIES` being named twice safe.
    """
    assert CARVED, "no category-scoped section — this test would be vacuous"
    for slug, spec in CARVED.items():
        siblings = [
            (h_slug, home)
            for h_slug, home in HOMES.items()
            if set(home.chains) & set(spec.chains)
        ]
        assert siblings, f"{slug} borrows chains no home section owns"
        for h_slug, home in siblings:
            missing = spec.categories - home.excluded_categories
            assert not missing, (
                f"{h_slug} still serves {sorted(missing)}, which {slug} also claims — "
                "those offers would appear in both sections"
            )


def test_no_category_is_excluded_without_a_section_that_claims_it():
    """The mirror failure, and the quieter one: exclude a category from its home section
    and forget to carve it out anywhere, and those offers are served by NOTHING. Nothing
    errors; the products simply stop existing for every client."""
    claimed = set().union(*(s.categories for s in CARVED.values())) if CARVED else set()
    for slug, spec in VERTICALS.items():
        orphaned = spec.excluded_categories - claimed
        assert not orphaned, (
            f"{slug} excludes {sorted(orphaned)} and no section serves them — "
            "those offers would be unreachable"
        )


def test_carved_out_categories_are_real_category_slugs():
    """`verticals.py` can't import `categories.py` (it is a leaf module, imported by the
    scrapers and the locator), so a typo there would be a filter that silently matches
    nothing. This is the check that import cycle costs us."""
    for slug, spec in CARVED.items():
        unknown = spec.categories - set(CATEGORIES)
        assert not unknown, f"{slug} names categories that don't exist: {sorted(unknown)}"
    assert DRINK_CATEGORIES <= set(CATEGORIES)


def test_a_carved_out_section_borrows_its_chains_and_never_owns_them():
    """`CHAIN_VERTICAL` answers "which section does this chain belong to" for the
    scrapers and the tests that pin a new chain's home. Drinks borrowing the six
    supermarkets must not overwrite grocery's claim on them."""
    for chain in VERTICALS["grocery"].chains:
        assert CHAIN_VERTICAL[chain] == "grocery"
    assert "drinks" not in set(CHAIN_VERTICAL.values())
    # Home sections still partition the chains between themselves.
    seen = [c for s in HOMES.values() for c in s.chains]
    assert len(seen) == len(set(seen))


def test_drinks_is_the_grocery_chains_and_nothing_else():
    """Pinned as a fact, not derived: Drinks is a category carve-out, so the day it grows
    a chain of its own is the day the partition above stops describing it."""
    assert VERTICALS["drinks"].chains == VERTICALS["grocery"].chains
    assert VERTICALS["drinks"].categories == DRINK_CATEGORIES
    assert VERTICALS["grocery"].excluded_categories == DRINK_CATEGORIES
    # Coffee is the user's call and the easiest thing for a later edit to "tidy" in.
    assert "coffee" not in DRINK_CATEGORIES


@pytest.mark.parametrize("vertical", sorted(VERTICALS))
def test_chains_for_answers_every_registered_section(vertical):
    assert chains_for(vertical), f"{vertical} serves no chains"


def test_chains_for_fails_closed_on_an_unknown_section():
    assert chains_for("pharmacy") == ()
