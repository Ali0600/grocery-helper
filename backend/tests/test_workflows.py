"""Guards on the CI workflow itself.

The constraints here are invisible at the point they matter: nothing in a green run tells you
that a *different* run was cancelled, or that a deploy never fired. They regressed once
already, so they are pinned.
"""
from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _load(name: str) -> dict:
    path = WORKFLOWS / name
    if not path.exists():  # pragma: no cover - depends on checkout layout
        pytest.skip(f"{name} not present")
    return yaml.safe_load(path.read_text())


def test_main_runs_are_never_cancelled_by_a_newer_push():
    """A superseded PR run is waste; a superseded `main` run is a LOST DEPLOY.

    2026-08-03: a docs commit pushed one minute after a backend merge cancelled that merge's
    run, and the Render deploy died with it — the fix sat on `main`, absent from production,
    with a green tick on the merge commit and no failure anywhere to notice. `cancel-in-progress`
    must therefore be conditional on the event, never a bare `true`.
    """
    concurrency = _load("ci.yml")["concurrency"]
    cancel = concurrency["cancel-in-progress"]
    assert cancel is not True, (
        "cancel-in-progress: true cancels main runs too, which silently discards a deploy"
    )
    assert "pull_request" in str(cancel), (
        "expected the cancel to be gated on the event being a pull request"
    )


def test_the_deploy_job_still_depends_on_the_test_jobs():
    """A deploy racing CI is the other way this pipeline can ship something unverified."""
    jobs = _load("ci.yml")["jobs"]
    deploy = next((j for name, j in jobs.items() if "deploy" in name.lower()), None)
    if deploy is None:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    assert deploy.get("needs"), "the deploy job must wait for the test jobs, not run beside them"
