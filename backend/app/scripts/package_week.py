"""Turn a freshly scraped database into the week that ships inside the deployment artifact.

Run by the weekly pipeline between the scrape and the data gate:

    python -m app.scripts.package_week --db week.db --out ../infra/build --plz "$PLZ" \
        --commit "$GITHUB_SHA"

It does three things, in this order:

1. **Compacts** the SQLite file and leaves it in the shape a read-only filesystem can open —
   rollback journal, no `-wal`/`-shm` sidecars. A WAL database cannot be opened at all when
   the directory is not writable, which on Lambda means every request fails.

2. **Exports what the API will actually serve**, per vertical, by calling `/api/offers`
   through the real app against this very file, opened read-only exactly as the function will
   open it. The data gate then judges those files. That indirection is the point: the gate is
   reading the app's own output rather than a second implementation of the route's filtering,
   dedup and sort, so it cannot pass a file the function would serve differently. It also
   proves the read-only URI works here, in CI, rather than discovering it on the function.

3. **Stamps `meta.json`** — when this week was built, from which commit, and how many offers
   per vertical. `/health` serves `built_at`, which is how the pipeline knows the week it just
   packaged is the week now being served; "the deploy succeeded" says nothing about that.

Prints counts only. The postal code is an input, never output: store names embed it.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..db import get_session
from ..main import app
from ..verticals import VERTICALS

# What the app asks for, so the exported file is the same set the app loads.
SERVE_LIMIT = 2000


def read_only_url(db: pathlib.Path) -> str:
    """The URL the deployed function uses, built for a local file.

    Both query flags are load-bearing; see app/snapshot.py for what each one prevents.
    """
    return f"sqlite:///file:{db.resolve()}?mode=ro&uri=true"


def journal_mode(db: pathlib.Path) -> str:
    """The file's current journal mode, read without changing anything."""
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        return conn.execute("PRAGMA journal_mode").fetchone()[0].lower()


def compact(db: pathlib.Path) -> None:
    """Shrink the file and put it in a shape a read-only filesystem can open.

    Leaving WAL is the part that matters: a WAL database needs to write its sidecars, so on
    the function's read-only filesystem it cannot be opened at all. Measured rather than
    assumed (2026-09-12): an idle second connection does NOT block the switch, and one holding
    a transaction makes SQLite raise `database is locked` — loudly. So this needs no read-back
    check of its own; the failure it could have hidden does not exist. What can still go wrong
    is skipping this step entirely, which `export` refuses.
    """
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("VACUUM")
    # SQLite removes its own sidecars on leaving WAL; belt-and-braces for a crashed run.
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = db.with_name(db.name + suffix)
        if sidecar.exists():
            sidecar.unlink()


def export(db: pathlib.Path, out: pathlib.Path, plz: str, commit: str) -> dict:
    """Write `served_<vertical>.json`, `week.db` and `meta.json` into `out`; return the meta."""
    out.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        read_only_url(db), connect_args={"check_same_thread": False}, pool_pre_ping=True
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _session() -> Session:
        with TestingSession() as session:
            yield session

    # No `with TestClient(app)`: that would run the app's lifespan, and this process is not a
    # deployment — there is nothing to verify and nothing to migrate.
    app.dependency_overrides[get_session] = _session
    try:
        client = TestClient(app)
        offers: dict[str, int] = {}
        chains: dict[str, list[str]] = {}
        for vertical in VERTICALS:
            res = client.get(
                "/api/offers",
                params={"plz": plz, "vertical": vertical, "limit": SERVE_LIMIT},
            )
            res.raise_for_status()
            served = res.json()
            (out / f"served_{vertical}.json").write_text(
                json.dumps(served), encoding="utf-8"
            )
            offers[vertical] = len(served)
            chains[vertical] = sorted({o["chain"] for o in served})
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()

    # Refuse to package a database the function could not open. This is the reachable
    # version of the WAL hazard — not a PRAGMA that silently fails, but an `export` reached
    # without `compact`, which is a one-line mistake with a completely silent consequence:
    # the package builds, deploys, and then every request fails on a read-only filesystem.
    # (The first draft of this script's own test made exactly that mistake.)
    mode = journal_mode(db)
    if mode != "delete":
        raise RuntimeError(
            f"{db} is in {mode} journal mode — a WAL database cannot be opened on the "
            "function's read-only filesystem. Call compact() before export()."
        )
    shutil.copy2(db, out / "week.db")
    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "offers": offers,
        "chains": chains,
        "week_db_bytes": db.stat().st_size,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="the scraped SQLite file to package")
    ap.add_argument("--out", required=True, help="directory the Lambda package is built from")
    ap.add_argument("--plz", required=True, help="postal code to export (never printed)")
    ap.add_argument("--commit", default="", help="git SHA to stamp into meta.json")
    args = ap.parse_args()

    db = pathlib.Path(args.db)
    before = db.stat().st_size
    compact(db)
    print(f"week.db: {before / 1e6:.1f} MB -> {db.stat().st_size / 1e6:.1f} MB compacted")

    meta = export(db, pathlib.Path(args.out), args.plz, args.commit)
    print(f"built_at {meta['built_at']}  commit {(meta['commit'] or 'none')[:12]}")
    for vertical, n in meta["offers"].items():
        print(f"  {vertical:<10}{n:>6} offers  {len(meta['chains'][vertical])} chains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
