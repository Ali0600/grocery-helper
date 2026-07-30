"""HTTP-level tests for the offers API (filters/sort/limit, payload, admin guards,
scrape throttle) via TestClient with an in-memory DB. The TestClient is used WITHOUT a
`with` block on purpose: lifespan (migrations + boot scrape) must not run in tests."""
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import categories
from app.api import offers as offers_api
from app.core.config import settings
from app.db import get_session
from app.main import app
from app.models import Base, Offer, Store
from app.throttle import RateLimiter
from app.validity import berlin_today

TODAY = berlin_today()


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    _seed(session)

    app.dependency_overrides[get_session] = lambda: session
    # Isolate the scrape throttle's module state per test.
    offers_api._last_scrape_at.clear()
    offers_api._last_any_scrape = None
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()


def _seed(session: Session) -> None:
    lidl = Store(chain="lidl", name="Lidl 10115", plz="10115")
    edeka = Store(chain="edeka", name="Edeka 10115", plz="10115")
    far = Store(chain="rewe", name="REWE 99999", plz="99999")
    # A drugstore-vertical store in the same PLZ, so the `vertical` filter has something to
    # separate. Kept out of every other test's expectations: it's `household`, `flyer`, and
    # carries no discount, so the category/source/min_discount assertions above are unmoved.
    rossmann = Store(chain="rossmann", name="Rossmann 10115", plz="10115")
    session.add_all([lidl, edeka, far, rossmann])
    session.flush()

    def o(store, ext, name, price, **kw):
        kw.setdefault("category", "fruits")
        kw.setdefault("source", "flyer")
        kw.setdefault("valid_to", TODAY + timedelta(days=3))
        return Offer(store_id=store.id, external_id=ext, name=name, price_cents=price, **kw)

    session.add_all(
        [
            o(lidl, "a", "Avocado", 149, discount_pct=40.0,
              raw_payload=json.dumps({"id": "a", "brand": {"name": "Bio"}})),
            o(lidl, "b", "Banane", 99, discount_pct=10.0),
            o(lidl, "c", "Coupon Kaffee", 499, source="coupon", category="coffee"),
            o(edeka, "d", "Dorade", 799, category="fish"),
            o(edeka, "e", "Expired Erdbeeren", 199, valid_to=TODAY - timedelta(days=1)),
            o(edeka, "f", "Forever Feta", 189, valid_to=None, category="cheese"),
            o(far, "g", "Gouda (andere PLZ)", 299, category="cheese"),
            o(rossmann, "h", "Schauma Shampoo", 159, category="household"),
        ]
    )
    session.commit()


# --------------------------------------------------------------------------- #
# GET /api/offers — filters, sort, limit, validity
# --------------------------------------------------------------------------- #
def test_filters_by_plz_chain_category_source(client):
    names = lambda r: [o["name"] for o in r.json()]  # noqa: E731

    all_10115 = client.get("/api/offers?plz=10115&limit=100")
    assert "Gouda (andere PLZ)" not in names(all_10115)

    only_lidl = client.get("/api/offers?chain=lidl&limit=100")
    assert set(o["chain"] for o in only_lidl.json()) == {"lidl"}

    fish = client.get("/api/offers?category=fish&limit=100")
    assert names(fish) == ["Dorade"]

    coupons = client.get("/api/offers?source=coupon&limit=100")
    assert names(coupons) == ["Coupon Kaffee"]

    discounted = client.get("/api/offers?min_discount=20&limit=100")
    assert names(discounted) == ["Avocado"]


def test_validity_filter_drops_expired_keeps_null(client):
    names = [o["name"] for o in client.get("/api/offers?limit=100").json()]
    assert "Expired Erdbeeren" not in names
    assert "Forever Feta" in names  # null valid_to = no window -> kept


def test_sort_orders(client):
    by_discount = [o["name"] for o in client.get("/api/offers?sort=discount&limit=100").json()]
    assert by_discount.index("Avocado") < by_discount.index("Banane")  # 40% before 10%

    prices = [o["price_cents"] for o in client.get("/api/offers?sort=price&limit=100").json()]
    assert prices == sorted(prices)


def test_limit_truncates(client):
    assert len(client.get("/api/offers?limit=2").json()) == 2


def test_serializer_carries_store_fields(client):
    offer = client.get("/api/offers?chain=lidl&limit=1").json()[0]
    assert offer["chain"] == "lidl" and offer["store_name"] == "Lidl 10115"


# --------------------------------------------------------------------------- #
# `vertical` — the grocery/drugstore split
# --------------------------------------------------------------------------- #
def test_vertical_scopes_offers_to_its_chains(client):
    chains = lambda r: {o["chain"] for o in r.json()}  # noqa: E731

    grocery = client.get("/api/offers?vertical=grocery&limit=100")
    assert "rossmann" not in chains(grocery)
    assert {"lidl", "edeka"} <= chains(grocery)

    drugstore = client.get("/api/offers?vertical=drugstore&limit=100")
    assert chains(drugstore) == {"rossmann"}
    assert [o["name"] for o in drugstore.json()] == ["Schauma Shampoo"]


def test_vertical_omitted_defaults_to_grocery(client):
    """Omitting the param means GROCERY, not "every chain".

    Only app builds older than the vertical release omit it, and they predate Drugstore
    entirely — no home screen, no drugstore chips, no way to reach that section. Serving
    them drugstore rows mixed into a grocery list was both wrong for them and, once dm
    landed (all chains = 2127), over the 2000 cap, which truncates silently.
    """
    chains = {o["chain"] for o in client.get("/api/offers?limit=2000").json()}
    assert {"lidl", "edeka", "rewe"} <= chains
    assert "rossmann" not in chains
    assert "dm" not in chains


def test_omitted_vertical_scopes_categories_the_same_way_as_offers(client):
    """The chips must not advertise a vertical the list won't serve. Both endpoints route
    through one `_vertical_chains`, so this pins that they can't drift apart."""
    listed = {o["category"] for o in client.get("/api/offers?limit=2000").json()}
    chips = {c["category"] for c in client.get("/api/categories").json()}
    assert chips <= listed


def test_unknown_vertical_is_rejected_not_ignored(client):
    """A typo must 422, never fall through to "no filter" — a bad value that silently widens
    the query is a filter that reports success while evaluating nothing."""
    assert client.get("/api/offers?vertical=grocerry&limit=100").status_code == 422
    assert client.get("/api/categories?vertical=pharmacy").status_code == 422


def test_categories_take_the_same_vertical_scope(client):
    """The chips must describe the list they filter, or they promise offers that aren't there."""
    grocery = {c["category"] for c in client.get("/api/categories?vertical=grocery").json()}
    assert "household" not in grocery  # the only household offer is Rossmann's
    assert {"fruits", "fish"} <= grocery

    drugstore = client.get("/api/categories?vertical=drugstore").json()
    assert [(c["category"], c["count"]) for c in drugstore] == [("household", 1)]


def test_bulk_prefetch_endpoints_honour_vertical(client):
    """Both promise to mirror /api/offers so their ids line up with the list; if they ignored
    `vertical` a drugstore session would also pull every grocery payload."""
    listed = {str(o["id"]) for o in client.get("/api/offers?vertical=drugstore&limit=100").json()}
    payloads = client.get("/api/offers/payloads?vertical=drugstore").json()
    traces = client.get("/api/offers/category-traces?vertical=drugstore").json()
    assert set(payloads) == listed
    assert set(traces) == listed


# --------------------------------------------------------------------------- #
# GET /api/offers/{id}/payload
# --------------------------------------------------------------------------- #
def test_payload_roundtrip_null_and_404(client):
    rows = client.get("/api/offers?limit=100").json()
    with_payload = next(o for o in rows if o["name"] == "Avocado")
    without = next(o for o in rows if o["name"] == "Banane")

    ok = client.get(f"/api/offers/{with_payload['id']}/payload").json()
    assert ok["payload"] == {"id": "a", "brand": {"name": "Bio"}}
    assert client.get(f"/api/offers/{without['id']}/payload").json()["payload"] is None
    assert client.get("/api/offers/999999/payload").status_code == 404


def test_bulk_payloads_keyed_by_id_scoped_to_plz(client):
    rows = client.get("/api/offers?plz=10115&limit=100").json()
    by_id = client.get("/api/offers/payloads?plz=10115").json()
    # One entry per served (deduped) offer, keyed by id — so the app can look up any
    # offer it's showing; the other-PLZ offer is excluded (same scoping as the list).
    assert set(by_id.keys()) == {str(o["id"]) for o in rows}
    avocado = next(o for o in rows if o["name"] == "Avocado")
    banane = next(o for o in rows if o["name"] == "Banane")
    assert by_id[str(avocado["id"])] == {"id": "a", "brand": {"name": "Bio"}}
    assert by_id[str(banane["id"])] is None  # present, but captured as null


# --------------------------------------------------------------------------- #
# GET /api/offers/{id}/category-trace  +  /api/offers/category-traces
# --------------------------------------------------------------------------- #
def test_category_trace_reports_the_deciding_rule_and_the_stored_category(client):
    rows = client.get("/api/offers?limit=100").json()
    avocado = next(o for o in rows if o["name"] == "Avocado")

    body = client.get(f"/api/offers/{avocado['id']}/category-trace").json()
    assert body["stored_category"] == avocado["category"]
    assert body["computed_category"] == body["trace"]["category"]
    # Every layer is reported, in order — the skipped ones are the point, not noise.
    assert [s["layer"] for s in body["trace"]["layers"]] == [
        "0", "1", "2", "2b", "3", "4", "5", "6", "7"
    ]
    winner = next(s for s in body["trace"]["layers"] if s["status"] == "decided")
    assert winner["slug"] == body["computed_category"]
    assert client.get("/api/offers/999999/category-trace").status_code == 404


def test_category_trace_flags_a_row_whose_stored_category_is_stale(client, monkeypatch):
    """A category is persisted at scrape time, so the rules can move underneath a row.
    `stale` has to say so — otherwise the trace explains a category the app isn't showing."""
    rows = client.get("/api/offers?limit=100").json()
    avocado = next(o for o in rows if o["name"] == "Avocado")
    assert client.get(f"/api/offers/{avocado['id']}/category-trace").json()["stale"] is False

    monkeypatch.setattr(categories, "_RULES", [("household", ["avocado"])])
    body = client.get(f"/api/offers/{avocado['id']}/category-trace").json()
    assert body["stored_category"] == "fruits" and body["computed_category"] == "household"
    assert body["stale"] is True


def test_category_trace_exposes_the_path_that_offerout_hides(client):
    """`category_path` drives layers 1 and 3 but isn't in OfferOut — the trace is the only
    way to see it, so "this offer has no path" stops being a guess."""
    rows = client.get("/api/offers?limit=100").json()
    avocado = next(o for o in rows if o["name"] == "Avocado")
    assert "category_path" not in avocado  # still absent from the list payload
    inputs = client.get(f"/api/offers/{avocado['id']}/category-trace").json()["trace"]["inputs"]
    assert inputs["text"] == " avocado  "  # the REAL padded haystack, space guards visible


def test_bulk_category_traces_keyed_by_id_scoped_to_plz_and_null_free(client):
    rows = client.get("/api/offers?plz=10115&limit=100").json()
    by_id = client.get("/api/offers/category-traces?plz=10115").json()
    # Same dedup + validity scoping as /api/offers, so the ids line up with the list.
    assert set(by_id.keys()) == {str(o["id"]) for o in rows}
    avocado = next(o for o in rows if o["name"] == "Avocado")
    entry = by_id[str(avocado["id"])]
    assert entry["computed_category"] == avocado["category"]
    assert [s["layer"] for s in entry["trace"]["layers"]] == [
        "0", "1", "2", "2b", "3", "4", "5", "6", "7"
    ]
    # Nulls are stripped in the bulk form — with them it is several MB over a real PLZ.
    assert all(v is not None for s in entry["trace"]["layers"] for v in s.values())


# --------------------------------------------------------------------------- #
# Admin guard on /api/reset + /api/recategorize
# --------------------------------------------------------------------------- #
def test_reset_open_when_no_token_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "")
    monkeypatch.setattr("app.scrapers.run.run_scrapers", lambda s, p: 0)
    assert client.post("/api/reset?plz=10115").status_code == 200


def test_reset_guarded_when_token_set(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "s3cret")
    monkeypatch.setattr("app.scrapers.run.run_scrapers", lambda s, p: 0)

    assert client.post("/api/reset?plz=10115").status_code == 403
    assert client.post("/api/reset?plz=10115", headers={"X-Admin-Token": "wrong"}).status_code == 403

    ok = client.post("/api/reset?plz=10115", headers={"X-Admin-Token": "s3cret"})
    assert ok.status_code == 200
    assert ok.json()["deleted"] > 0

    # Deprecated query-param fallback still accepted (pre-header app builds).
    assert client.post("/api/reset?plz=10115&token=s3cret").status_code == 200


def test_recategorize_guarded_when_token_set(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "s3cret")
    assert client.post("/api/recategorize").status_code == 403
    ok = client.post("/api/recategorize", headers={"X-Admin-Token": "s3cret"})
    assert ok.status_code == 200 and "recategorized" in ok.json()


# --------------------------------------------------------------------------- #
# Scrape throttle
# --------------------------------------------------------------------------- #
def test_scrape_throttled_only_when_plz_has_rows(client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.scrapers.run.run_scrapers", lambda s, p: calls.append(p) or 5)

    # 10115 already has offers: first scrape runs, immediate second is skipped.
    first = client.post("/api/scrape?plz=10115").json()
    assert first["scraped"] == 5 and calls == ["10115"]
    second = client.post("/api/scrape?plz=10115").json()
    assert second["skipped"] is True and second["scraped"] == 0 and calls == ["10115"]

    # An EMPTY PLZ scrapes even right after (cold-start path must never block).
    third = client.post("/api/scrape?plz=20095").json()
    assert "skipped" not in third and calls == ["10115", "20095"]


def test_nearby_stores_is_rate_limited(client, monkeypatch):
    """A stranger iterating coordinates can't drive unbounded Overpass fan-out: once the
    token bucket is empty the endpoint returns [] WITHOUT calling the locator (which is
    what protects our IP's standing with the free OSM mirrors)."""
    calls = {"n": 0}

    def fake_nearby(lat, lng, **kw):
        calls["n"] += 1
        return []

    monkeypatch.setattr("app.services.store_locator.nearby_stores", fake_nearby)
    # A tiny, frozen-clock limiter: 2 tokens, no refill.
    monkeypatch.setattr(offers_api, "_NEARBY_LIMITER", RateLimiter(2, 0, clock=lambda: 0.0))

    # Explicit lat/lng → no PLZ resolution; each allowed call fans out to the (faked) locator.
    urls = "/api/nearby-stores?lat=52.52&lng=13.4"
    r1, r2, r3 = client.get(urls), client.get(urls), client.get(urls)

    assert r1.status_code == r2.status_code == r3.status_code == 200
    assert r1.json() == r3.json() == []
    assert calls["n"] == 2  # the 3rd request was rate-limited → locator never invoked


def test_health_exposes_the_running_commit(monkeypatch):
    """The deploy job polls /health until `commit` equals the merged SHA — that's what
    makes "is my code live yet?" a queryable fact instead of an inference from data
    shapes. None when not on Render (local dev)."""
    from app.main import health

    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    assert health() == {"status": "ok", "commit": None}

    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    assert health() == {"status": "ok", "commit": "abc123"}
