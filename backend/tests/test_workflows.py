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


def test_ci_keeps_a_manual_recovery_hatch_for_a_lost_deploy():
    """The deploy job only fires on a push touching a runtime backend file — and a fix to the
    pipeline itself (a workflow or `tests/` change) is excluded by that filter. Without a manual
    trigger, recovering a cancelled/failed deploy means inventing a backend commit. Twice in two
    days that was the actual blocker, so the hatch is pinned."""
    wf = _load("ci.yml")
    triggers = wf[True] if True in wf else wf["on"]  # PyYAML reads bare `on:` as the bool True
    assert "workflow_dispatch" in triggers, "ci.yml must stay manually re-runnable"
    deploy = next((j for n, j in wf["jobs"].items() if "deploy" in n.lower()), None)
    if deploy is None:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    assert "workflow_dispatch" in deploy["if"], (
        "the deploy job must run on a manual dispatch, or the hatch does not reach it"
    )
    detect = next(s for s in deploy["steps"] if s.get("id") == "detect")
    # The input must arrive via env, not be interpolated into the shell (untrusted text).
    assert "FORCE_DEPLOY" in (detect.get("env") or {})
    assert "${{" not in detect["run"], "never interpolate an input into a run: block"


def test_superseded_is_proven_by_ancestry_not_inferred_from_inequality():
    """The deploy gate may exit 0 without our commit going live in exactly one case: a NEWER
    deploy replaced it. That has to be proven.

    2026-08-04: it was inferred from `live != want` (with a pre-deploy commit as the only
    guard), so when the pre-deploy probe timed out against the sleeping free tier the guard
    could not fire, a build that never landed reported GREEN, and the follow-up step counted
    offers served by the OLD code. Ancestry — is our commit an ancestor of what's live? — needs
    no pre-deploy reading and cannot fail open.
    """
    jobs = _load("ci.yml")["jobs"]
    deploy = next((j for name, j in jobs.items() if "deploy" in name.lower()), None)
    if deploy is None:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    wait = next((s for s in deploy["steps"] if "live" in (s.get("name") or "").lower()), None)
    assert wait is not None, "expected a step that waits for the new code to be live"
    run = wait["run"]
    assert "merge-base --is-ancestor" in run, (
        "the superseded branch must prove ancestry; inferring it from `live != want` fails open"
    )
    # ...and the benign exit must be guarded BY that check, not by a bare inequality.
    assert 'if [ -n "$live" ] && [ "$live" != "$want" ]; then' not in run, (
        "the naive superseded check is back — a failed build would report green again"
    )
