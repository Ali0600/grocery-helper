"""Guards on the audit's own instrument (`app/scripts/contact_sheets.py`).

The weekly photo audit is only as trustworthy as the sheets it reads, and both claims below
are invisible in the output: a duplicate photo just looks like another product, and an expired
one looks like this week's. Getting either wrong wastes a reviewer's whole pass.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, Offer, Store
from app.scripts.contact_sheets import _served
from app.validity import berlin_today

TODAY = berlin_today()


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    lidl = Store(chain="lidl", name="Lidl 10115", plz="10115")
    rewe = Store(chain="rewe", name="REWE 10115", plz="10115")
    s.add_all([lidl, rewe])
    s.flush()

    def o(store, ext, name, **kw):
        kw.setdefault("category", "fruits")
        kw.setdefault("source", "flyer")
        kw.setdefault("price_cents", 199)
        kw.setdefault("valid_to", TODAY + timedelta(days=3))
        kw.setdefault("image_url", f"https://cdn.example/{ext}.jpg")
        return Offer(store_id=store.id, external_id=ext, name=name, **kw)

    s.add_all([
        o(lidl, "a1", "Avocado"),
        o(rewe, "a2", "Avocado"),                      # same product, second chain
        o(lidl, "a3", "avocado"),                      # ...and a casing variant
        o(lidl, "b1", "Banane", category="fruits"),
        # `Apfelsaft` sorts FIRST by name but belongs to a LATE category, and `Zitrone` the
        # other way round. Without a crossing pair, name-order and category-order agree and
        # the grouping assertion below passes whichever key is used — proven: the first
        # version of this fixture was all-`fruits` and the sabotage sailed through it.
        o(lidl, "e1", "Apfelsaft", category="soft_drinks"),
        o(lidl, "f1", "Zitrone", category="fruits"),
        # A crossing PAIR is still not enough — sorted by name these three fruits happened to
        # stay contiguous anyway, and the sabotage passed twice. `Cola` sorts between Banane
        # and Zitrone, so a name-only sort genuinely INTERLEAVES the two chips.
        o(lidl, "g1", "Cola", category="soft_drinks"),
        o(lidl, "c1", "Altbrot", valid_to=TODAY - timedelta(days=1)),   # last week
        o(lidl, "d1", "Kein Bild", image_url=None),                     # nothing to show
    ])
    s.commit()
    yield s
    s.close()


def test_one_tile_per_product_not_per_offer(session):
    """A product repeats across brochures and chains. Showing the same photo five times
    spends a reviewer's attention on nothing and pads the sheet count with no new evidence."""
    names = [i.name.lower() for i in _served(session)]
    assert names.count("avocado") == 1, f"expected Avocado once, got {names}"


def test_only_this_weeks_offers_are_shown(session):
    """The offers table accretes flyer weeks — it holds ~19k rows against ~2k on sale. Sheets
    built from the whole table would have a reviewer adjudicating products that stopped being
    on sale weeks ago, and every fix they proposed would be unverifiable in the app."""
    assert "Altbrot" not in {i.name for i in _served(session)}


def test_products_with_no_photo_are_left_out(session):
    """A tile with no image carries no evidence — it is a text row wearing a picture's costume."""
    assert "Kein Bild" not in {i.name for i in _served(session)}


def test_items_are_grouped_by_category_so_a_sheet_asks_one_question(session):
    """Sheets are per-category so the reviewer reads 'does every one of these belong in X?'
    rather than classifying from scratch — which is the slower, less reliable question.

    Asserted as CONTIGUITY rather than sortedness: contiguity is the property the sheets
    actually need (one chip per sheet), and it stays meaningful even if the ordering within a
    category changes.
    """
    from itertools import groupby

    order = [i.category for i in _served(session)]
    assert len(order) > len(set(order)), "fixture must repeat a category, or this proves nothing"
    runs = [c for c, _ in groupby(order)]
    assert len(runs) == len(set(runs)), (
        f"each category must appear in ONE unbroken block, got {order}"
    )
