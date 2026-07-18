"""Tests for the recipe-candidate dump (`app.scripts.recipe_seed`).

This script has no runtime consumer — its output is read by the offline authoring step, whose
brief (`scripts/recipe-prompt.md`) describes the shape field by field. That makes the shape an
invisible contract: change it here and nothing fails until a weekly `claude -p` regen quietly
authors from a JSON it can't read. So the shape is pinned, not just the grouping.
"""
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import Offer, Store
from app.scripts import recipe_seed


@pytest.fixture()
def seeded(monkeypatch):
    """An in-memory DB with two chains in one PLZ, plus a third store in another PLZ."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = Session(bind=engine)

    lidl = Store(chain="lidl", name="Lidl", plz="10115")
    rewe = Store(chain="rewe", name="REWE", plz="10115")
    other = Store(chain="edeka", name="EDEKA", plz="99999")
    session.add_all([lidl, rewe, other])
    session.flush()
    session.add_all(
        [
            Offer(store_id=lidl.id, external_id="l1", source="flyer", name="Lidl Möhren",
                  category="vegetables", price_cents=99, price_per_unit="1 kg = 0.99",
                  discount_pct=20),
            Offer(store_id=lidl.id, external_id="l2", source="flyer", name="Lidl Hähnchen",
                  category="poultry", price_cents=499),
            Offer(store_id=rewe.id, external_id="r1", source="flyer", name="REWE Tomaten",
                  category="vegetables", price_cents=149),
            # not cookable — must never appear
            Offer(store_id=lidl.id, external_id="l3", source="flyer", name="Spülmittel",
                  category="household", price_cents=199),
            # different PLZ — must be filtered out by --plz
            Offer(store_id=other.id, external_id="e1", source="flyer", name="EDEKA Gurke",
                  category="vegetables", price_cents=79),
        ]
    )
    session.commit()

    # main() opens its own session; hand it this engine's.
    monkeypatch.setattr(recipe_seed, "SessionLocal", sessionmaker(bind=engine, class_=Session))
    return session


def _run(capsys, *argv: str) -> dict:
    monkeyargs = ["recipe_seed", *argv]
    import sys

    old, sys.argv = sys.argv, monkeyargs
    try:
        recipe_seed.main()
    finally:
        sys.argv = old
    return json.loads(capsys.readouterr().out)


def test_groups_candidates_by_chain(seeded, capsys):
    out = _run(capsys, "--plz", "10115")

    assert set(out) == {"plz", "by_chain"}
    assert out["plz"] == "10115"
    assert set(out["by_chain"]) == {"lidl", "rewe"}  # the 99999 store is filtered out

    lidl, rewe = out["by_chain"]["lidl"], out["by_chain"]["rewe"]
    # A chain's list holds ONLY its own products. This is the whole point of the dump: authoring
    # from a mixed list is what produced recipes needing four shops.
    assert [o["name"] for o in lidl["vegetables"]] == ["Lidl Möhren"]
    assert [o["name"] for o in rewe["vegetables"]] == ["REWE Tomaten"]
    assert [o["name"] for o in lidl["poultry"]] == ["Lidl Hähnchen"]
    assert rewe["poultry"] == []


def test_every_cookable_category_is_present_even_when_empty(seeded, capsys):
    out = _run(capsys, "--plz", "10115")
    for chain in out["by_chain"].values():
        assert list(chain) == recipe_seed.COOK_CATEGORIES
    # "this chain has no beef this week" must be visible, not inferred from a missing key
    assert out["by_chain"]["rewe"]["beef"] == []


def test_entry_carries_the_fields_the_authoring_brief_documents(seeded, capsys):
    out = _run(capsys, "--plz", "10115")
    entry = out["by_chain"]["lidl"]["vegetables"][0]
    assert set(entry) == {"name", "chain", "price_cents", "price_per_unit", "discount_pct"}
    assert entry["chain"] == "lidl"
    assert entry["price_per_unit"] == "1 kg = 0.99"


def test_non_cookable_categories_are_dropped(seeded, capsys):
    out = _run(capsys, "--plz", "10115")
    names = [o["name"] for cats in out["by_chain"].values() for lst in cats.values() for o in lst]
    assert "Spülmittel" not in names


def test_per_caps_each_chain_category_and_keeps_the_cheapest(seeded, capsys):
    session = seeded
    store = session.query(Store).filter_by(chain="lidl").one()
    session.add_all(
        [
            Offer(store_id=store.id, external_id=f"x{i}", source="flyer", name=f"Kohl {i}",
                  category="vegetables", price_cents=1000 + i)
            for i in range(5)
        ]
    )
    session.commit()

    out = _run(capsys, "--plz", "10115", "--per", "2")
    veg = out["by_chain"]["lidl"]["vegetables"]
    assert len(veg) == 2
    assert [o["price_cents"] for o in veg] == [99, 1000]  # cheapest first, capped
