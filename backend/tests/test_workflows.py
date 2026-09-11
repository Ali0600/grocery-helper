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


# The weekly refresh now has TWO data-quality gates — one after the reset, one for a
# verify-only run — so a substring match like "quality" in the name silently picks whichever
# comes first. Select by exact name and fail loudly on ambiguity: a test that grabs the wrong
# gate would assert the right thing about the wrong step.
RESET_STEP = "POST /api/reset (retry transient failures)"
GATE_AFTER_RESET = "Data-quality gate on the served deals"
GATE_VERIFY_ONLY = "Data-quality gate (verify-only)"
GATE_AFTER_FAILED_RESET = "Data-quality gate after a failed reset"


def _triggers(wf: dict) -> dict:
    """The `on:` block. PyYAML follows YAML 1.1, where a bare `on:` key is the BOOLEAN True —
    so `wf["on"]` raises KeyError and a test written that way fails for the wrong reason."""
    return wf[True] if True in wf else wf["on"]


def _step(wf: dict, job: str, name: str) -> dict:
    steps = wf["jobs"][job]["steps"]
    match = [s for s in steps if (s.get("name") or "") == name]
    assert len(match) == 1, f"expected exactly one step named {name!r}, found {len(match)}"
    return match[0]


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


def test_the_ota_publish_is_not_cancelled_by_the_next_merge():
    """The same lost-release bug as above, one workflow over — and it actually fired.

    2026-08-28: a docs push a minute after a mobile merge cancelled that merge's OTA run,
    which had already logged "mobile/** changed — publishing". Its replacement checked out
    the DOCS commit, correctly found no mobile/** changes, and skipped. The update was never
    published, and both runs are green — nothing anywhere reports a release that simply did
    not happen.

    Grouping by ref is what makes it possible: every workflow_run event for `main` shares one
    ref, so consecutive merges collide, and the survivor evaluates a different commit than the
    one it cancelled. Keying on the commit means two merges never cancel each other, while a
    duplicate run of the SAME commit still collapses.
    """
    concurrency = _load("eas-update.yml")["concurrency"]
    group = str(concurrency["group"])
    assert "head_sha" in group, (
        "group the OTA publish by the commit it publishes, not by the ref — a ref-keyed "
        "group lets the next merge cancel a publish that nothing will retry"
    )


def test_the_ota_publish_only_ever_fires_for_a_push_to_main():
    """`branches: [main]` does NOT mean "a push to our main" — it matches the TRIGGERING run's
    head branch, and a pull request from a fork whose branch is itself named `main` produces a
    run with exactly that head branch.

    CI runs on `pull_request`, so without an event check the chain is: fork the repo, name the
    branch `main`, open a PR, let CI go green on code the attacker wrote — and this workflow
    then checks out `workflow_run.head_sha` (their tree), runs `npm ci` (their lockfile, their
    install scripts) and publishes `eas update --branch production` with EXPO_TOKEN. That ships
    an attacker's JS bundle to every installed app, over the air.

    The sibling repo rpg-template carries this guard with a comment explaining exactly this;
    this workflow was written from the same pattern and did not. `event == 'push'` is the whole
    fix: a push to main requires write access, a fork PR never has it.
    """
    job = _load("eas-update.yml")["jobs"]["update"]
    condition = str(job["if"])
    assert "workflow_run.event == 'push'" in condition, (
        "the OTA publish must require the triggering run to be a PUSH — `branches: [main]` "
        "matches a fork PR whose head branch is named `main`, which would publish a "
        "stranger's bundle to users' phones"
    )
    # And the success gate must survive alongside it: a failed CI run must not publish either.
    assert "conclusion == 'success'" in condition, (
        "the OTA publish must still require the triggering CI run to have succeeded"
    )


def test_the_deploy_job_still_depends_on_the_test_jobs():
    """A deploy racing CI is the other way this pipeline can ship something unverified."""
    jobs = _load("ci.yml")["jobs"]
    deploy = next((j for name, j in jobs.items() if "deploy" in name.lower()), None)
    if deploy is None:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    assert deploy.get("needs"), "the deploy job must wait for the test jobs, not run beside them"


def test_dependabot_raises_prs_only_for_security_updates():
    """Version updates are OFF by choice: a PR should mean "there is a CVE", nothing else.

    `open-pull-requests-limit: 0` is GitHub's documented way to disable version updates while
    leaving security updates (which come from the repo's alerts, not this file) untouched. Both
    assertions below guard a trap rather than a preference:
      * a missing/raised limit quietly turns routine bumps back on;
      * `target-branch` on an entry silently disables SECURITY updates for that ecosystem — the
        one setting that would defeat the whole point while looking like a harmless tweak.
    """
    path = WORKFLOWS.parent / "dependabot.yml"
    if not path.exists():  # pragma: no cover - depends on checkout layout
        pytest.skip("no dependabot.yml")
    cfg = yaml.safe_load(path.read_text())
    assert cfg["updates"], "expected at least one ecosystem entry"
    for entry in cfg["updates"]:
        eco = entry.get("package-ecosystem")
        assert entry.get("open-pull-requests-limit") == 0, (
            f"{eco}: version updates are back on — a PR should only ever mean a CVE"
        )
        assert "target-branch" not in entry, (
            f"{eco}: target-branch disables SECURITY updates for this ecosystem"
        )


def test_ci_keeps_a_manual_recovery_hatch_for_a_lost_deploy():
    """The deploy job only fires on a push touching a runtime backend file — and a fix to the
    pipeline itself (a workflow or `tests/` change) is excluded by that filter. Without a manual
    trigger, recovering a cancelled/failed deploy means inventing a backend commit. Twice in two
    days that was the actual blocker, so the hatch is pinned."""
    wf = _load("ci.yml")
    triggers = _triggers(wf)
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


def test_the_weekly_gate_enforces_the_per_chain_floor_after_the_reset():
    """2026-08-08: the drugstore vertical served rossmann=2 (against 287 the week before) and
    the same day grocery served aldi=4 — its literal `_sample()` size. Neither showed up as a
    chain outage, because `chains >= N` counts presence with no cardinality behind it and the
    total-offers floor is carried by the healthy chains.

    `verify_deals.py` grew a per-chain floor for that, but it DEFAULTS OFF — a chain empties
    legitimately between brochures, so the floor is only honest right after the weekly wipe-
    and-re-scrape. That makes this assertion the compensating control: drop `--post-reset`
    from the workflow and the gate silently returns to being blind, with every test in
    test_verify_deals.py still green, because they call verify() directly.
    """
    wf = _load("scrape.yml")
    steps = wf["jobs"]["refresh"]["steps"]
    gate = _step(wf, "refresh", GATE_AFTER_RESET)
    assert "--post-reset" in gate["run"], (
        "without --post-reset the per-chain floor never runs and a dark chain reads as green"
    )
    assert "${{" not in gate["run"], (
        "workflow inputs belong in env:, never interpolated into a run: block"
    )
    # The flag asserts "a re-scrape just finished", so it is a lie if the gate outruns the reset.
    reset = _step(wf, "refresh", RESET_STEP)
    assert steps.index(gate) > steps.index(reset), (
        "the gate must run AFTER /api/reset, or --post-reset claims something that isn't true"
    )


def test_a_verify_only_run_skips_the_destructive_reset():
    """`verify_only` exists so a stale alert issue can be cleared without wiping prod.

    Before it, the ONLY way to re-verify the deployed backend was the full wipe-and-re-scrape,
    so a bug fixed on Monday left its `scrape-failure` issue open until Sunday — and that open
    issue is what the self-heal poller consumes, which is how it burned both its attempts on a
    repo that was already fixed. If this guard goes, "verify" quietly becomes "wipe" again.
    """
    wf = _load("scrape.yml")
    assert "verify_only" in _triggers(wf)["workflow_dispatch"]["inputs"], (
        "the verify-only path needs its own dispatch input"
    )
    reset = _step(wf, "refresh", RESET_STEP)
    # `inputs` (not `github.event.inputs`) PRESERVES the declared boolean; github.event.inputs
    # stringifies it. So the condition must be plain truthiness — `inputs.verify_only == 'true'`
    # compares a boolean against a string, which GitHub coerces to false, and the guard would
    # never fire. A schedule run has no `inputs` at all, so the negation runs the reset.
    assert reset.get("if") == "${{ ! inputs.verify_only }}", (
        "the reset must be skipped on a verify-only run, guarded on the TYPED inputs context"
    )


def test_the_verify_only_gate_never_claims_a_reset_just_ran():
    """--post-reset arms the per-chain floor by asserting "every chain has a fresh brochure".

    That is true right after the weekly wipe and false at any other moment — a chain empties
    legitimately between brochures (Rossmann's week ends Friday). Passing the flag on a
    mid-week verify-only run would make the gate fail on healthy data, and the natural "fix"
    for that red is to loosen the floor, which is the compensating control for a dark chain.
    So the two gates must stay genuinely separate commands, not one step with a conditional
    built inside `run:` — that would leave the literal flag in the step body and let the
    sibling test above pass while the flag never applied.
    """
    wf = _load("scrape.yml")
    gate = _step(wf, "refresh", GATE_VERIFY_ONLY)
    assert "--post-reset" not in gate["run"], (
        "a verify-only run has not just re-scraped, so --post-reset would assert something false"
    )
    assert gate.get("if") == "${{ inputs.verify_only }}", (
        "the verify-only gate must run only on a verify-only dispatch"
    )
    assert "${{" not in gate["run"], (
        "workflow inputs belong in env:, never interpolated into a run: block"
    )
    # Both gates must still feed the same alert/close machinery, or a green verify-only run
    # would prove prod healthy and leave the issue open anyway — the whole point of the path.
    names = [s.get("name") or "" for s in wf["jobs"]["refresh"]["steps"]]
    assert names.index(GATE_VERIFY_ONLY) < names.index("Close recovery issues")

def test_the_data_verdict_survives_a_failed_reset():
    """The scheduled gate only runs after a SUCCESSFUL reset, because a step whose `if:` names
    no status function is skipped once an earlier step failed. So when #184 made the admin
    endpoints fail closed on a host without ADMIN_TOKEN, every Sunday reset returned 403 and
    the data check stopped running entirely: the alert issue said "refresh failed" and said
    nothing about what prod was serving (that week Rossmann was down to 25 offers, found by
    hand). A second gate, conditioned on the reset having failed, keeps the verdict in the log.
    """
    wf = _load("scrape.yml")
    steps = wf["jobs"]["refresh"]["steps"]
    reset = _step(wf, "refresh", RESET_STEP)
    fallback = _step(wf, "refresh", GATE_AFTER_FAILED_RESET)
    assert reset.get("id"), "the reset step needs an id for a later step to read its outcome"
    cond = fallback.get("if", "")
    assert "failure()" in cond, (
        "without a status function GitHub skips this step after the very failure it exists for"
    )
    assert f"steps.{reset['id']}.outcome == 'failure'" in cond, (
        "run only when the RESET failed, not after the gate fails on a successful reset"
    )
    assert "--post-reset" not in fallback["run"], (
        "a failed reset re-scraped nothing, so the per-chain floor would assert something false"
    )
    assert "${{" not in fallback["run"], (
        "workflow inputs belong in env:, never interpolated into a run: block"
    )
    alert = _step(wf, "refresh", "Alert on repeated failure")
    assert steps.index(reset) < steps.index(fallback) < steps.index(alert), (
        "the verdict has to be in the log before the alert issue links to it"
    )
