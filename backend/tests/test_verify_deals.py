"""Guards on the weekly data-quality gate (`.github/scripts/verify_deals.py`).

The gate is a production alarm that, until 2026-08-08, had no test, no fixture and no lint —
it lives under `.github/`, which ruff (working-directory `backend`) and pytest (`testpaths =
tests`) both walk straight past. So nothing had ever proven it fires.

Loaded by path rather than imported: `.github` is not a valid package name.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "verify_deals.py"


@pytest.fixture(scope="module")
def gate():
    if not SCRIPT.exists():  # pragma: no cover - depends on checkout layout
        pytest.skip("verify_deals.py not present")
    spec = importlib.util.spec_from_file_location("verify_deals", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The measured 2026-08-02 Sunday post-reset counts. The fixture IS the calibration, so a
# future edit that drifts from reality has to change these numbers deliberately.
# `penny` joined 2026-08-11 at its measured first-parse count (258 offers, 255 after dedup).
HEALTHY_GROCERY = {"aldi": 247, "edeka": 234, "edeka_center": 274, "lidl": 417, "rewe": 390,
                   "penny": 255}


def _offers(store_name: str = "Store", **counts: int) -> list[dict]:
    """Offers carrying only what the gate reads, shaped so EVERY check but the one under
    test passes: unique names (so nothing self-disagrees), one real category (so the `other`
    rate is 0) and a unit price (so the €/kg floor is met)."""
    out = []
    for chain, n in counts.items():
        for i in range(n):
            out.append({
                "chain": chain,
                "name": f"{chain} product {i}",
                "category": "pantry",
                "unit_price_cents": 199,
                "store_name": store_name,
            })
    return out


def test_a_chain_serving_two_offers_still_counts_as_a_chain(gate):
    """2026-08-08: the drugstore vertical served rossmann=2 against 287 the week before, and
    `chains >= 2` passed — it counts presence, with no cardinality behind it, so one surviving
    offer is indistinguishable from a full brochure.

    dm=300 here is load-bearing: it puts the total at 302, clear of the 250 offers floor, so
    every pre-existing check passes and ONLY the new one can fail. Written with dm's real 213
    this test would pass on the old code via the offers floor and prove nothing.
    """
    offers = _offers(rossmann=2, dm=300)
    assert gate.verify(offers, gate.PROFILES["drugstore"], post_reset=True) == 1, (
        "a chain down to 2 offers after a full re-scrape is an incident the gate must name"
    )


def test_the_same_thin_chain_is_only_a_diagnostic_before_the_reset(gate):
    """A chain empties legitimately between brochures — Rossmann's week ends Friday, so on a
    Saturday it really does serve ~2 offers. Enforcing the floor then would train us to ignore
    the alarm. Same fixture as above, so this also proves no OTHER check is doing the work."""
    offers = _offers(rossmann=2, dm=300)
    assert gate.verify(offers, gate.PROFILES["drugstore"], post_reset=False) == 0


def test_a_grocery_chain_on_sample_data_hides_behind_four_healthy_ones(gate):
    """The blind spot is wider than one chain. At the measured counts the total floor is
    carried by the survivors: with penny's 255 the healthy total is 1817, so even after
    three chains fall back to sample data it clears 800 — and the old gate stayed green.
    Adding a sixth chain WIDENS this blind spot, which is exactly why `min_chain_offers`
    rather than the total floor is the instrument that catches it.

    aldi=4 is its real `_sample()` size, not a round number. Verified live in production on
    2026-08-08, where the old gate reported grocery green at 1207 offers with aldi at 4.
    """
    offers = _offers(aldi=4, **{c: n for c, n in HEALTHY_GROCERY.items() if c != "aldi"})
    profile = gate.PROFILES["grocery"]
    assert len(offers) >= profile["offers"], "the old total floor must still pass, or this proves nothing"
    assert len({o["chain"] for o in offers}) >= profile["chains"], "…and so must the chain count"
    assert gate.verify(offers, profile, post_reset=True) == 1


def test_the_measured_healthy_week_stays_green(gate):
    """The anti-flap guard, at the exact measured counts. This is the one test that asserts a
    PASS, and it earns its place: it stops someone ratcheting the floor above a week we know
    was healthy, which is how a gate quietly stops protecting anything."""
    assert gate.verify(_offers(**HEALTHY_GROCERY), gate.PROFILES["grocery"], post_reset=True) == 0


def test_an_absent_chain_is_reported_once_not_twice(gate, capsys):
    """The two chain checks must partition the failure space, not overlap: an absent chain has
    no key to count, so it can only ever trip `chains`, while a present-but-thin one can only
    trip the per-chain floor. Building the counter from an EXPECTED chain list instead of the
    response would report the same outage twice and read as two independent failures."""
    assert gate.verify(_offers(dm=300), gate.PROFILES["drugstore"], post_reset=True) == 1
    fails = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("FAIL")]
    assert len(fails) == 1, f"one outage, one failure line; got {fails}"
    assert "chains:" in fails[0], f"an ABSENT chain belongs to the chains check, not the floor: {fails[0]}"


def test_the_breakdown_is_printed_on_a_healthy_run(gate, capsys):
    """The histogram is the point, not a failure detail. Recalibrating the floor after an
    incident needs the runs from BEFORE it, and those are the green ones — this data otherwise
    has to be reconstructed from a SQLite file, which is exactly what setting the floor cost."""
    gate.verify(_offers(**HEALTHY_GROCERY), gate.PROFILES["grocery"], post_reset=False)
    out = capsys.readouterr().out
    for chain, n in HEALTHY_GROCERY.items():
        assert f"{chain} {n}" in out, f"the green-run breakdown must list {chain}"


def test_the_gate_never_prints_the_postal_code(gate, capsys):
    """`bonial.py` builds store names as f"{store_label} {plz}", so `store_name` embeds the PLZ
    — a secret in this public repo, masked in the Actions log only as `***`. Everything printed
    here is keyed on `chain` for that reason; keying the breakdown on the store would leak it."""
    gate.verify(_offers(store_name="Edeka 99999", **HEALTHY_GROCERY),
                gate.PROFILES["grocery"], post_reset=True)
    assert "99999" not in capsys.readouterr().out


def test_a_truncated_response_is_not_trusted(gate):
    """/api/offers caps at 2000 and truncates AFTER sorting by discount_pct with None last —
    which is disproportionately REWE and ALDI, i.e. the chains nearest the floor. At the cap
    every count in the report is a floor rather than a count, so the per-chain check would be
    the first thing to lie. Fail instead of reporting numbers we know are wrong."""
    n = gate.SERVE_LIMIT // 5
    capped = _offers(aldi=n, edeka=n, edeka_center=n, lidl=n, rewe=n)
    assert len(capped) == gate.SERVE_LIMIT
    assert gate.verify(capped, gate.PROFILES["grocery"], post_reset=True) == 1


def test_the_flag_is_wired_through_the_cli(gate, tmp_path):
    """Every test above calls verify() directly, so all of them stay green if the flag never
    reaches it. This is the only one that exercises the real entry point."""
    path = tmp_path / "offers.json"
    path.write_text(json.dumps(_offers(rossmann=2, dm=300)))
    base = [sys.executable, str(SCRIPT), "--file", str(path), "--vertical", "drugstore"]
    assert subprocess.run(base + ["--post-reset"], capture_output=True).returncode == 1
    assert subprocess.run(base, capture_output=True).returncode == 0


def test_the_offers_floor_is_scoped_to_whether_a_scrape_just_ran(gate):
    """Between Sundays the served set DECAYS by design, so the post-reset floor goes red on
    a healthy system.

    /api/offers filters `valid_to >= today`, so a chain whose flyer week has ended drops out
    on schedule. Measured 2026-08-15, four days after the last scrape: drugstore served 201
    against the 250 floor. Nothing was broken — Rossmann's weekly had expired (its 302 offers
    were measured on 08-12), leaving 5 rows from a supplement dated 08-21, while dm's
    clearance rows never expire. That red is the mirror of a gate reporting green while
    evaluating nothing: a gate reporting RED while measuring something it cannot judge.
    """
    midweek = _offers(rossmann=5, dm=196)
    assert gate.verify(midweek, gate.PROFILES["drugstore"], post_reset=False) == 0, (
        "a mid-week reading must be judged against the floor that survives flyer expiry"
    )


def test_scoping_that_floor_did_not_loosen_the_sunday_one(gate):
    """The compensating half. `offers_stale` exists so a mid-week run is judgeable, NOT so the
    weekly gate gets easier — right after a wipe-and-re-scrape, 201 drugstore offers really is
    an incident, and this is the assertion that stops the new key becoming a way to soften it.
    """
    # BOTH chains sit above the per-chain floor on purpose, so the offers floor is the only
    # check that can fail. A `rossmann=5` fixture would fail post-reset on the per-chain floor
    # instead, and the assertion would hold whatever the offers number was — proven: loosening
    # `offers` to 150 sailed past that version of this test.
    borderline = _offers(rossmann=110, dm=110)  # 220: under the Sunday floor, over the mid-week
    assert gate.verify(borderline, gate.PROFILES["drugstore"], post_reset=True) == 1, (
        "post-reset, a fresh scrape yielding 220 drugstore offers is a real failure"
    )
    assert gate.verify(borderline, gate.PROFILES["drugstore"], post_reset=False) == 0, (
        "the same 220 mid-week is expected decay, not an incident"
    )
    # And the mid-week floor still has to be breachable, or it is decoration.
    assert gate.verify(_offers(rossmann=5, dm=60), gate.PROFILES["drugstore"],
                       post_reset=False) == 1, (
        "dm collapsing must still fail mid-week — the floor is set from dm alone"
    )
