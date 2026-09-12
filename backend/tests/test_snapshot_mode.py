"""Snapshot mode — the contract of a deployment whose database ships inside the artifact.

Everything here guards a failure that is SILENT. A snapshot deployment that migrates, that can
write to the week it serves, or that serves an empty database because a URI flag was dropped,
all look exactly like a healthy one: 200s, no errors, plausible-looking JSON. So each guard
below has a matching sabotage recorded in the PR body, and two of these tests are the only
ones in the suite that run the app's `lifespan` — hence `with TestClient(app)`, deliberately
unlike the rest of the file's siblings (see test_api_offers.py's module docstring).
"""
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app import snapshot
from app.api import offers as offers_api
from app.core.config import settings
from app.db import get_session
from app.main import app
from app.models import Base, Offer, Store
from app.scripts.package_week import compact, export, journal_mode, read_only_url
from app.verticals import DRINK_CATEGORIES, VERTICALS

PLZ = "10115"


def _week_db(tmp_path, *, rows=True):
    """A real on-disk SQLite file shaped like a packaged week."""
    db = tmp_path / "week.db"
    engine = create_engine(f"sqlite:///{db}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    if rows:
        with Session(bind=engine) as session:
            lidl = Store(chain="lidl", name="Lidl", plz=PLZ)
            rewe = Store(chain="rewe", name="REWE", plz=PLZ)
            session.add_all([lidl, rewe])
            session.flush()
            drink = sorted(DRINK_CATEGORIES)[0]
            session.add_all(
                [
                    Offer(store_id=lidl.id, external_id="a", source="flyer",
                          name="Äpfel", category="fruits", price_cents=99,
                          price_per_unit="1 kg = 0.99", discount_pct=20.0),
                    Offer(store_id=rewe.id, external_id="b", source="flyer",
                          name="Gouda", category="cheese", price_cents=199),
                    Offer(store_id=lidl.id, external_id="c", source="flyer",
                          name="Cola", category=drink, price_cents=149),
                ]
            )
            session.commit()
    engine.dispose()
    return db


@pytest.fixture()
def snapshot_deployment(tmp_path, monkeypatch):
    """Settings as the deployed function has them: snapshot mode, read-only URL, real file."""
    db = _week_db(tmp_path)
    monkeypatch.setattr(settings, "snapshot_mode", True)
    monkeypatch.setattr(settings, "database_url", read_only_url(db))
    monkeypatch.setattr(settings, "snapshot_meta_path", str(tmp_path / "meta.json"))
    return db


def test_snapshot_mode_runs_no_migration_and_no_scrape_at_startup(
    snapshot_deployment, monkeypatch
):
    """The reason this mode exists.

    On the previous host an ephemeral disk left the offers table empty on every cold start, so
    the boot scrape's only condition was true every time and the API could not answer for
    30-60 seconds. Lambda caps the init phase at 10 seconds, so the same startup would not
    merely be slow — it would never become healthy at all.
    """
    called = []
    monkeypatch.setattr("app.main.run_migrations", lambda: called.append("migrate"))
    monkeypatch.setattr("app.main.run_scrapers", lambda s, p: called.append("scrape"))

    with TestClient(app):  # the `with` is what runs lifespan
        pass

    assert called == [], f"snapshot startup did work it must not do: {called}"


def test_snapshot_mode_refuses_a_writable_database_url(tmp_path, monkeypatch):
    """A writable URL in snapshot mode means the template is wrong, and the consequence is not
    visible from outside: the function would serve, and could modify, something other than the
    artifact the data gate approved. Failing startup keeps the previous version live."""
    db = _week_db(tmp_path)
    monkeypatch.setattr(settings, "snapshot_mode", True)
    # `uri=true` is deliberately PRESENT: a URL missing both flags is refused by the uri=true
    # check one line later, so this test would pass with the mode=ro check deleted and prove
    # nothing about it (the sabotage run caught exactly that).
    monkeypatch.setattr(settings, "database_url", f"sqlite:///file:{db}?uri=true")

    with pytest.raises(RuntimeError, match="mode=ro"):
        with TestClient(app):
            pass


def test_snapshot_mode_refuses_a_uri_without_the_uri_flag(tmp_path, monkeypatch):
    """`uri=true` is the flag whose absence fails OPEN, which is why it is asserted separately.

    Without it SQLAlchemy hands the whole string to sqlite3 as a *filename*, so sqlite3
    creates a file literally called `file:...?mode=ro` and serves an empty database. Every
    endpoint answers 200 with `[]`, the app shows "no deals", and nothing reports an error.
    """
    db = _week_db(tmp_path)
    monkeypatch.setattr(settings, "snapshot_mode", True)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///file:{db}?mode=ro")

    with pytest.raises(RuntimeError, match="uri=true"):
        with TestClient(app):
            pass


def test_snapshot_mode_refuses_a_missing_database(tmp_path, monkeypatch):
    """The package was built without its data — serving an empty API is the wrong answer."""
    monkeypatch.setattr(settings, "snapshot_mode", True)
    monkeypatch.setattr(
        settings, "database_url", f"sqlite:///file:{tmp_path / 'absent.db'}?mode=ro&uri=true"
    )

    with pytest.raises(RuntimeError, match="no database"):
        with TestClient(app):
            pass


@pytest.mark.parametrize("endpoint", ["/api/scrape", "/api/reset", "/api/recategorize"])
def test_write_endpoints_are_405_in_snapshot_mode(endpoint, tmp_path, monkeypatch):
    """405, and refused BEFORE anything runs.

    The scraper and the recategorizer are replaced with landmines: if the guard sits anywhere
    after them, the test reports a 500 from the landmine instead of a 405, which is the whole
    point — a guard that refuses only after attempting the write would leave the honest answer
    depending on SQLite's file permissions rather than on this deployment's contract.
    """
    db = _week_db(tmp_path)
    engine = create_engine(
        read_only_url(db), connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(bind=engine)

    def _session():
        with TestingSession() as session:
            yield session

    def _landmine(*a, **kw):
        raise AssertionError("a write path ran on a read-only snapshot deployment")

    monkeypatch.setattr(settings, "snapshot_mode", True)
    monkeypatch.setattr("app.scrapers.run.run_scrapers", _landmine)
    monkeypatch.setattr("app.scripts.recategorize.recategorize", _landmine)
    offers_api._last_scrape_at.clear()
    app.dependency_overrides[get_session] = _session
    try:
        client = TestClient(app)
        res = client.post(endpoint)
        assert res.status_code == 405, res.text
        assert "Sunday pipeline" in res.json()["detail"]
        # The outcome, not the status code: the three offers are still there.
        assert len(client.get("/api/offers", params={"plz": PLZ}).json()) >= 1
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_the_write_guard_is_inert_off_snapshot_mode():
    """Local dev, CI and the Docker path must be untouched by any of this."""
    offers_api._require_writable(None)  # no exception


def test_a_lambda_counts_as_a_deployed_host(monkeypatch):
    """The fail-closed admin guard keys on "am I deployed?", derived from the platform's own
    injected marker so there is no third value to set and forget. A new host with a new marker
    silently turns that guard back into fail-open."""
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "grocery-helper-api")
    monkeypatch.setattr(settings, "admin_token", "")

    with pytest.raises(HTTPException) as exc:
        offers_api._require_admin(None, None, None)
    assert exc.value.status_code == 403


def test_read_only_sqlite_uri_serves_reads_and_rejects_writes(tmp_path):
    """The URI form is the whole mechanism, so it is verified against real SQLite rather than
    assumed from the docs — reads work, writes are refused by the driver."""
    db = _week_db(tmp_path)
    engine = create_engine(read_only_url(db), connect_args={"check_same_thread": False})
    with Session(bind=engine) as session:
        assert session.scalars(select(Offer)).all(), "a read-only DB must still read"
        session.add(Offer(store_id=1, external_id="x", source="flyer", name="No",
                          category="other", price_cents=1))
        with pytest.raises(OperationalError, match="readonly"):
            session.commit()
    engine.dispose()


def test_the_exported_week_is_exactly_what_the_api_serves(tmp_path, monkeypatch):
    """The data gate judges the exported files, so they have to BE the served set.

    Exporting through the real route rather than re-querying is what makes that true: the
    route's vertical scoping, validity filter, dedup and sort are not reimplemented here, so
    the gate cannot approve a file the function would serve differently.
    """
    db = _week_db(tmp_path)
    out = tmp_path / "build"
    meta = export(db, out, PLZ, "cafe123")

    engine = create_engine(read_only_url(db), connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    app.dependency_overrides[get_session] = lambda: TestingSession()
    try:
        client = TestClient(app)
        for vertical in VERTICALS:
            exported = json.loads((out / f"served_{vertical}.json").read_text())
            live = client.get(
                "/api/offers", params={"plz": PLZ, "vertical": vertical, "limit": 2000}
            ).json()
            assert [o["id"] for o in exported] == [o["id"] for o in live], vertical
            assert meta["offers"][vertical] == len(live)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    # The drink carve-out is the case a single-vertical export would quietly get wrong.
    assert meta["offers"]["drinks"] == 1
    assert meta["offers"]["grocery"] == 2
    assert meta["commit"] == "cafe123"
    assert (out / "week.db").is_file()
    assert json.loads((out / "meta.json").read_text())["built_at"] == meta["built_at"]


def _set_wal(db) -> None:
    engine = create_engine(f"sqlite:///{db}")
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    engine.dispose()


def test_compacting_leaves_a_week_a_read_only_filesystem_can_open(tmp_path):
    """A WAL database needs to write its sidecars, so on the function's read-only filesystem
    it cannot be opened at all — not slowly, not degraded: every request fails."""
    db = _week_db(tmp_path)
    _set_wal(db)
    compact(db)
    out = tmp_path / "build"
    export(db, out, PLZ, "")

    assert journal_mode(out / "week.db") == "delete"
    for suffix in ("-journal", "-wal", "-shm"):
        assert not (out / f"week.db{suffix}").exists(), suffix


def test_packaging_refuses_a_week_that_was_never_compacted(tmp_path):
    """The reachable half of that hazard, and the one with no symptom until deployment.

    `export` without `compact` is a one-line mistake — the first draft of the test above made
    it — and everything downstream still succeeds: the package builds, the gate passes on the
    exported JSON, the deploy reports green, and then every request on the function fails.
    So the packaging step refuses rather than trusting its caller's ordering.
    """
    db = _week_db(tmp_path)
    _set_wal(db)
    with pytest.raises(RuntimeError, match="journal mode"):
        export(db, tmp_path / "build", PLZ, "")


def test_meta_is_absent_not_fatal_when_nothing_was_packaged(tmp_path, monkeypatch):
    """Local dev and CI serve a live database with no artifact behind them; provenance must
    never be the reason a healthy deployment fails its health check."""
    monkeypatch.setattr(settings, "snapshot_meta_path", str(tmp_path / "nope.json"))
    assert snapshot.read_meta() == {}

    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    monkeypatch.setattr(settings, "snapshot_meta_path", str(bad))
    assert snapshot.read_meta() == {}
