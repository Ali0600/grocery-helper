"""Tests for the basket optimizer — a live endpoint whose selection math (coverage
tiebreaks, cross-store cherry-picking, savings) had zero coverage until now.

Same in-memory-session pattern as test_reset.py: no network, schema via create_all.
"""
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Offer, Store
from app.schemas import OptimizeRequest
from app.services.optimizer import optimize_basket


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(bind=engine)


def _store(session: Session, chain: str, plz: str = "10115") -> Store:
    store = Store(chain=chain, name=f"{chain} {plz}", plz=plz)
    session.add(store)
    session.flush()
    return store


def _offer(session: Session, store: Store, category: str, price: int, **kw) -> Offer:
    o = Offer(
        store_id=store.id,
        external_id=f"{store.chain}:{category}:{price}",
        source="flyer",
        name=kw.pop("name", f"{category} @ {store.chain}"),
        category=category,
        price_cents=price,
        **kw,
    )
    session.add(o)
    session.flush()
    return o


def test_single_store_prefers_coverage_over_price():
    """A store covering BOTH wanted categories must beat a cheaper store covering one."""
    s = _session()
    lidl, rewe = _store(s, "lidl"), _store(s, "rewe")
    _offer(s, lidl, "dairy", 100)  # cheap, but lidl has no fruit
    _offer(s, rewe, "dairy", 200)
    _offer(s, rewe, "fruits", 300)

    res = optimize_basket(s, OptimizeRequest(categories=["dairy", "fruits"], store_count=1))
    assert len(res.baskets) == 1
    assert res.baskets[0].chain == "rewe"
    assert res.total_cents == 500
    assert res.missing_categories == []


def test_single_store_ties_on_coverage_break_by_lower_total():
    s = _session()
    lidl, rewe = _store(s, "lidl"), _store(s, "rewe")
    _offer(s, lidl, "dairy", 100)
    _offer(s, lidl, "fruits", 100)
    _offer(s, rewe, "dairy", 150)
    _offer(s, rewe, "fruits", 150)

    res = optimize_basket(s, OptimizeRequest(categories=["dairy", "fruits"], store_count=1))
    assert res.baskets[0].chain == "lidl"
    assert res.total_cents == 200


def test_single_store_uses_its_cheapest_offer_per_category():
    s = _session()
    lidl = _store(s, "lidl")
    _offer(s, lidl, "dairy", 300)
    _offer(s, lidl, "dairy", 120)  # the cheaper duplicate must win

    res = optimize_basket(s, OptimizeRequest(categories=["dairy"], store_count=1))
    assert res.total_cents == 120


def test_single_store_reports_missing_categories():
    s = _session()
    lidl = _store(s, "lidl")
    _offer(s, lidl, "dairy", 100)

    res = optimize_basket(s, OptimizeRequest(categories=["dairy", "fish"], store_count=1))
    assert res.missing_categories == ["fish"]
    assert res.total_cents == 100  # the covered part still priced


def test_multi_store_cherry_picks_cheapest_per_category():
    s = _session()
    lidl, rewe = _store(s, "lidl"), _store(s, "rewe")
    _offer(s, lidl, "dairy", 100)
    _offer(s, lidl, "fruits", 400)
    _offer(s, rewe, "dairy", 300)
    _offer(s, rewe, "fruits", 200)

    res = optimize_basket(s, OptimizeRequest(categories=["dairy", "fruits"], store_count=2))
    assert res.total_cents == 300  # 100 (lidl dairy) + 200 (rewe fruits)
    by_chain = {b.chain: b for b in res.baskets}
    assert by_chain["lidl"].items[0].category == "dairy"
    assert by_chain["rewe"].items[0].category == "fruits"
    # Savings vs the best single store (lidl covers both at 500): 500 - 300.
    assert res.single_store_total_cents == 500
    assert res.savings_cents == 200


def test_multi_store_savings_never_negative():
    """One store already optimal → cherry-picking equals it; the clamp keeps savings at 0."""
    s = _session()
    lidl, rewe = _store(s, "lidl"), _store(s, "rewe")
    _offer(s, lidl, "dairy", 100)
    _offer(s, lidl, "fruits", 100)
    _offer(s, rewe, "dairy", 500)

    res = optimize_basket(s, OptimizeRequest(categories=["dairy", "fruits"], store_count=2))
    assert res.savings_cents == 0
    assert res.total_cents == 200
    assert len(res.baskets) == 1  # everything cheapest at lidl → one basket


def test_multi_store_is_uncapped_by_design():
    """store_count >= 2 means "cherry-pick freely", not "at most N stores" — pinned so a
    future 'fix' doesn't silently change the product behavior."""
    s = _session()
    for i, chain in enumerate(["lidl", "rewe", "edeka"]):
        st = _store(s, chain)
        _offer(s, st, f"cat{i}", 100)

    res = optimize_basket(
        s, OptimizeRequest(categories=["cat0", "cat1", "cat2"], store_count=2)
    )
    assert len(res.baskets) == 3  # one per store, despite store_count=2
    assert res.store_count == 3  # the response reports what it actually used


def test_expired_offers_are_excluded():
    s = _session()
    lidl = _store(s, "lidl")
    _offer(s, lidl, "dairy", 100, valid_to=date.today() - timedelta(days=2))
    _offer(s, lidl, "dairy", 250, valid_to=date.today() + timedelta(days=2))

    res = optimize_basket(s, OptimizeRequest(categories=["dairy"], store_count=1))
    assert res.total_cents == 250  # the expired 100c offer must not win


def test_plz_filter_scopes_the_search():
    s = _session()
    here = _store(s, "lidl", plz="10115")
    there = _store(s, "lidl", plz="80331")
    _offer(s, here, "dairy", 300)
    _offer(s, there, "dairy", 100)  # cheaper, but in Munich

    res = optimize_basket(s, OptimizeRequest(categories=["dairy"], store_count=1, plz="10115"))
    assert res.baskets[0].store_id == here.id
    assert res.total_cents == 300


def test_empty_db_returns_all_categories_missing():
    s = _session()
    res = optimize_basket(s, OptimizeRequest(categories=["dairy", "fish"], store_count=1))
    assert res.baskets == []
    assert res.total_cents == 0
    assert res.missing_categories == ["dairy", "fish"]


def test_no_categories_means_everything_available():
    """An empty wish list optimizes over every category the stores carry."""
    s = _session()
    lidl = _store(s, "lidl")
    _offer(s, lidl, "dairy", 100)
    _offer(s, lidl, "fruits", 150)

    res = optimize_basket(s, OptimizeRequest(categories=[], store_count=2))
    assert res.total_cents == 250
    assert res.missing_categories == []
