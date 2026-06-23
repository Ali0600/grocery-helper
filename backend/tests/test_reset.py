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
