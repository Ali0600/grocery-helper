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
    session.add_all([lidl, edeka, far])
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
            o(lidl, "c", "Coupon Kaffee", 499, source="coupon", category="soft_drinks"),
            o(edeka, "d", "Dorade", 799, category="fish"),
            o(edeka, "e", "Expired Erdbeeren", 199, valid_to=TODAY - timedelta(days=1)),
            o(edeka, "f", "Forever Feta", 189, valid_to=None, category="cheese"),
            o(far, "g", "Gouda (andere PLZ)", 299, category="cheese"),
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
