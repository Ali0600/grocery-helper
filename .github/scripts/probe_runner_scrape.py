"""Scrape once on this host and report COUNTS ONLY — the Step 0 probe for the Lambda move.

Answers one question: does a GitHub runner's IP get served the same flyer data a Berlin laptop
gets? See .github/workflows/probe-runner-scrape.yml for why that is not obvious.

Prints nothing that could identify the postal code: every count is keyed on `chain`, never on
`store_name` (bonial.py builds those as f"{store_label} {plz}"). The PLZ arrives in $PLZ, is
passed to the scrapers, and is never written to stdout.

Run from `backend/` with DATABASE_URL pointing at a throwaway SQLite file and the schema
already created:

    cd backend && DATABASE_URL=sqlite:///./probe.db alembic upgrade head
    cd backend && PLZ=10115 python ../.github/scripts/probe_runner_scrape.py

Exits 1 when the result needs a human look, so the verdict is mechanical rather than eyeballed.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sqlite3
import sys
import time

# `python path/to/script.py` puts the SCRIPT's directory on sys.path, not the working
# directory, so importing `app` needs backend/ added explicitly — resolved from this file
# rather than from the cwd. The first run of this probe died right here instead of reporting a
# verdict, which is the right way round: a harness fault must never read as an answer.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))

from app import metrics  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import FlyerPage, Offer, Store  # noqa: E402
from app.scrapers.run import run_scrapers  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

# All eight chains the scrape covers: six grocery (lidl, rewe, edeka, edeka_center, penny,
# aldi) plus the two drugstore ones (rossmann via the flyer, dm via its clearance API).
EXPECTED_CHAINS = 8


def _per_chain(column) -> dict[str, int]:
    """Row counts grouped by chain — the only identifier safe to print."""
    with SessionLocal() as session:
        return dict(
            session.execute(
                select(Store.chain, func.count(column.id))
                .join(column, column.store_id == Store.id)
                .group_by(Store.chain)
            ).all()
        )


def _chain_floor() -> int:
    """The per-chain floor from the data gate itself, so this probe cannot drift from it.

    `.github/scripts/` is neither linted nor collected by the backend's tooling (ruff runs with
    working-directory backend, pytest has testpaths = tests), which is why verify_deals.py is
    loaded by path in its own test too.
    """
    path = pathlib.Path(__file__).resolve().parent / "verify_deals.py"
    spec = importlib.util.spec_from_file_location("verify_deals", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PROFILES["grocery"]["min_chain_offers"]


def main() -> int:
    plz = os.environ["PLZ"]  # read, never printed

    started = time.monotonic()
    with SessionLocal() as session:
        total = run_scrapers(session, plz)
    elapsed = time.monotonic() - started

    offers = _per_chain(Offer)
    pages = _per_chain(FlyerPage)
    floor = _chain_floor()

    print(f"\nscraped {total} offers in {elapsed:.0f}s\n")
    print(f"{'chain':<16}{'offers':>8}{'pages':>8}   floor {floor}")
    thin = []
    for chain in sorted(offers):
        n = offers[chain]
        if n < floor:
            thin.append(chain)
        print(f"{chain:<16}{n:>8}{pages.get(chain, 0):>8}   {'ok' if n >= floor else 'THIN'}")

    snap = metrics.snapshot()
    print(f"\noutbound calls: {snap['total_calls']} {snap['by_source']}")
    print(f"throttled:      {snap['throttled_total']} {snap['throttles']}")
    print(f"degraded:       {snap['scrape_failures_total']} {snap['scrape_failures']}")

    # The weekly pipeline ships this file inside the Lambda package, so its vacuumed size is
    # the number that has to clear the 250 MB unzipped / 50 MB zipped limits. VACUUM cannot run
    # inside a transaction, hence raw sqlite3 rather than a SQLAlchemy session.
    db = pathlib.Path("probe.db")
    before = db.stat().st_size
    with sqlite3.connect(db) as conn:
        conn.execute("VACUUM")
    print(f"\nprobe.db: {before / 1e6:.1f} MB -> {db.stat().st_size / 1e6:.1f} MB vacuumed")

    problems = []
    if snap["throttled_total"]:
        problems.append(f"throttled by {sorted(snap['throttles'])}")
    if snap["scrape_failures"]:
        problems.append(f"degraded chains {sorted(snap['scrape_failures'])}")
    if len(offers) < EXPECTED_CHAINS:
        problems.append(f"{EXPECTED_CHAINS - len(offers)} chain(s) served nothing at all")
    if thin:
        problems.append(f"under the floor: {thin}")

    print()
    if problems:
        print("VERDICT  needs a look: " + "; ".join(problems))
        print(
            "One degraded 'aldi' with everything else healthy is the known Overpass division "
            "flake (2026-08-17, 08-25, 09-11), not an IP block — a failed division is never "
            "cached, so the next run retries it."
        )
        return 1
    print(f"VERDICT  clean: {len(offers)} chains, every one at or above {floor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
