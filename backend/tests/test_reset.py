"""Tests for POST /api/reset (wipe + re-scrape). The route function is called
directly against an in-memory SQLite session with the scraper monkeypatched, so the
test stays pure (no network), matching the rest of the suite."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.offers import trigger_reset
from app.core.config import settings
from app.db import Base
from app.models import Offer, Store


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(bind=engine)


def _seed(session: Session) -> Store:
    store = Store(chain="lidl", name="Test Lidl", plz="10115")
    session.add(store)
    session.flush()
    session.add_all(
        [
            Offer(store_id=store.id, external_id="a", source="flyer",
                  name="Apple", category="fruits", price_cents=99),
            Offer(store_id=store.id, external_id="b", source="flyer",
                  name="Milk", category="dairy", price_cents=89),
        ]
    )
    session.commit()
    return store


def test_reset_wipes_then_rescrapes(monkeypatch):
    session = _session()
    store = _seed(session)

    def fake_run(sess, plz):
        # the re-scrape re-populates the table after the wipe
        sess.add(Offer(store_id=store.id, external_id="fresh", source="flyer",
                       name="Banana", category="fruits", price_cents=59))
        sess.commit()
        return 1

    monkeypatch.setattr("app.scrapers.run.run_scrapers", fake_run)
    monkeypatch.setattr(settings, "admin_token", "")  # open by default

    result = trigger_reset(session, plz="10115", token=None)

    assert result["deleted"] == 2
    assert result["scraped"] == 1
    # the two seeded offers are gone, only the freshly-scraped one remains
    assert [o.name for o in session.scalars(select(Offer)).all()] == ["Banana"]


def test_reset_requires_token_when_configured(monkeypatch):
    session = _session()
    _seed(session)
    monkeypatch.setattr(settings, "admin_token", "secret")
    monkeypatch.setattr("app.scrapers.run.run_scrapers", lambda s, p: 0)

    # wrong/missing token -> 403, and nothing is deleted (guard runs before the wipe)
    with pytest.raises(HTTPException) as exc:
        trigger_reset(session, plz="10115", token=None)
    assert exc.value.status_code == 403
    assert len(session.scalars(select(Offer)).all()) == 2

    # correct token proceeds with the wipe
    result = trigger_reset(session, plz="10115", token="secret")
    assert result["deleted"] == 2


def test_a_deployed_instance_refuses_the_wipe_when_no_token_is_configured(monkeypatch):
    """The guard used to return early whenever ADMIN_TOKEN was empty — which is the state the
    deployed instance was actually in (`config.py` called the Render dashboard value "still
    outstanding"). So the one endpoint that DELETEs every offer was unauthenticated on a public
    URL, and the code read as if it were protected.

    "Off unless configured" is fail-OPEN, and the thing it leaves open is destructive. Absent
    configuration must deny where it counts and stay permissive only in local dev, so a
    forgotten dashboard value can never be the difference between guarded and wide open.
    """
    session = _session()
    _seed(session)
    monkeypatch.setattr(settings, "admin_token", "")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "deadbeef")  # what Render injects at runtime
    monkeypatch.setattr("app.scrapers.run.run_scrapers", lambda s, p: 0)

    with pytest.raises(HTTPException) as exc:
        trigger_reset(session, plz="10115", token=None)
    assert exc.value.status_code == 403
    # The outcome, not the status code: the table must still be there.
    assert len(session.scalars(select(Offer)).all()) == 2


def test_local_dev_without_a_token_is_still_open(monkeypatch):
    """The deny above is scoped to a DEPLOYED instance on purpose. Requiring a token locally
    would mean every contributor has to invent one before they can reset their own SQLite file,
    and the fix for that friction is people switching the guard off again."""
    session = _session()
    store = _seed(session)
    monkeypatch.setattr(settings, "admin_token", "")
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setattr(
        "app.scrapers.run.run_scrapers",
        lambda sess, plz: (
            sess.add(Offer(store_id=store.id, external_id="fresh", source="flyer",
                           name="Banana", category="fruits", price_cents=59)),
            sess.commit(),
            1,
        )[-1],
    )

    result = trigger_reset(session, plz="10115", token=None)
    assert result["deleted"] == 2
