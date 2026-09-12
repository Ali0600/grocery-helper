"""Guards on the CI workflow itself.

The constraints here are invisible at the point they matter: nothing in a green run tells you
that a *different* run was cancelled, or that a deploy never fired. They regressed once
already, so they are pinned.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # a declared dev dependency; see requirements-dev.txt

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _load(name: str) -> dict:
    path = WORKFLOWS / name
    if not path.exists():  # pragma: no cover - depends on checkout layout
        pytest.skip(f"{name} not present")
    return yaml.safe_load(path.read_text())


# The weekly refresh has THREE data-quality gates — one on the scraped week, one for a
# verify-only run, one for a failed scrape — so a substring match like "quality" in the name
# silently picks whichever comes first. Select by exact name and fail loudly on ambiguity: a
# test that grabs the wrong gate would assert the right thing about the wrong step. The same
# trap bit the deploy test below, where "Resolve the live function" started matching a search
# for "live" ahead of "Wait until the new code is live".
SCRAPE_STEP = "Scrape this week's deals into week.db"
DEPLOY_STEP = "Deploy this week's data"
GATE_ON_THE_WEEK = "Data-quality gate on the served deals"
GATE_VERIFY_ONLY = "Data-quality gate (verify-only)"
GATE_AFTER_FAILED_SCRAPE = "Data-quality gate after a failed scrape"
WAIT_FOR_LIVE_STEP = "Wait until the new code is live"


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
    wf = _load("ci.yml")
    if "deploy" not in wf["jobs"]:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    run = _step(wf, "deploy", WAIT_FOR_LIVE_STEP)["run"]
    assert "merge-base --is-ancestor" in run, (
        "the superseded branch must prove ancestry; inferring it from `live != want` fails open"
    )
    # ...and the benign exit must be guarded BY that check, not by a bare inequality.
    assert 'if [ -n "$live" ] && [ "$live" != "$want" ]; then' not in run, (
        "the naive superseded check is back — a failed build would report green again"
    )


def test_the_weekly_gate_enforces_the_per_chain_floor_on_the_scraped_week():
    """2026-08-08: the drugstore vertical served rossmann=2 (against 287 the week before) and
    the same day grocery served aldi=4 — its literal `_sample()` size. Neither showed up as a
    chain outage, because `chains >= N` counts presence with no cardinality behind it and the
    total-offers floor is carried by the healthy chains.

    `verify_deals.py` grew a per-chain floor for that, but it DEFAULTS OFF — a chain empties
    legitimately between brochures, so the floor is only honest right after a scrape. That
    makes this assertion the compensating control: drop `--post-reset` from the workflow and
    the gate silently returns to being blind, with every test in test_verify_deals.py still
    green, because they call verify() directly.

    Since the data became a deployment artifact this gate also decides whether the week ships
    at all, so its POSITION carries a second meaning: after the scrape (or `--post-reset`
    asserts something untrue) and before the deploy (or it is reporting on a week the app is
    already serving, which is what it used to do).
    """
    wf = _load("scrape.yml")
    steps = wf["jobs"]["refresh"]["steps"]
    gate = _step(wf, "refresh", GATE_ON_THE_WEEK)
    assert "--post-reset" in gate["run"], (
        "without --post-reset the per-chain floor never runs and a dark chain reads as green"
    )
    assert "${{" not in gate["run"], (
        "workflow inputs belong in env:, never interpolated into a run: block"
    )
    scrape = _step(wf, "refresh", SCRAPE_STEP)
    deploy = _step(wf, "refresh", DEPLOY_STEP)
    assert steps.index(scrape) < steps.index(gate) < steps.index(deploy), (
        "the gate must sit between the scrape and the deploy: before it, --post-reset claims "
        "a scrape that has not happened; after it, a bad week is already live"
    )
    assert not gate.get("continue-on-error"), (
        "a gate that cannot fail the job cannot stop the deploy"
    )


def test_a_verify_only_run_neither_scrapes_nor_deploys():
    """`verify_only` exists so a stale alert issue can be cleared without touching production.

    Before it, the ONLY way to re-verify the deployed backend was a full re-scrape, so a bug
    fixed on Monday left its `scrape-failure` issue open until Sunday — and that open issue is
    what the self-heal poller consumes, which is how it burned both its attempts on a repo
    that was already fixed.

    Both guards are asserted, not just the scrape: the scrape and the deploy are separate
    steps now, so a verify-only run that skipped only the scrape would package and ship
    whatever happened to be on the runner — an empty week, deployed over a healthy one.
    """
    wf = _load("scrape.yml")
    assert "verify_only" in _triggers(wf)["workflow_dispatch"]["inputs"], (
        "the verify-only path needs its own dispatch input"
    )
    # `inputs` (not `github.event.inputs`) PRESERVES the declared boolean; github.event.inputs
    # stringifies it. So the condition must be plain truthiness — `inputs.verify_only == 'true'`
    # compares a boolean against a string, which GitHub coerces to false, and the guard would
    # never fire. A schedule run has no `inputs` at all, so the negation does the real work.
    for name in (SCRAPE_STEP, DEPLOY_STEP):
        assert _step(wf, "refresh", name).get("if") == "${{ ! inputs.verify_only }}", (
            f"{name!r} must be skipped on a verify-only run, guarded on the TYPED inputs context"
        )


def test_the_weekly_dispatch_cannot_redirect_production_to_another_postal_code():
    """The scrape's output IS production's data now, so a `plz` dispatch input would not be a
    test — it would replace the week every user sees with another region's deals, and the
    per-chain floors are calibrated for this one. It was removed with the reset it belonged to;
    this stops it coming back by habit."""
    wf = _load("scrape.yml")
    inputs = _triggers(wf)["workflow_dispatch"]["inputs"]
    assert "plz" not in inputs, (
        "a manual postal code would overwrite the served week rather than probe it"
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

def test_the_data_verdict_survives_a_failed_scrape():
    """The main gate only runs after a SUCCESSFUL scrape, because a step whose `if:` names no
    status function is skipped once an earlier step failed. So when #184 made the admin
    endpoints fail closed on a host without ADMIN_TOKEN, every Sunday refresh failed and the
    data check stopped running entirely: the alert issue said "refresh failed" and said
    nothing about what production was serving (that week Rossmann was down to 25 offers, found
    by hand). A second gate, conditioned on the scrape having failed, keeps the verdict in the
    log — and it reports on the DEPLOYED function, which is still serving last week.
    """
    wf = _load("scrape.yml")
    steps = wf["jobs"]["refresh"]["steps"]
    scrape = _step(wf, "refresh", SCRAPE_STEP)
    fallback = _step(wf, "refresh", GATE_AFTER_FAILED_SCRAPE)
    assert scrape.get("id"), "the scrape step needs an id for a later step to read its outcome"
    cond = fallback.get("if", "")
    assert "failure()" in cond, (
        "without a status function GitHub skips this step after the very failure it exists for"
    )
    assert f"steps.{scrape['id']}.outcome == 'failure'" in cond, (
        "run only when the SCRAPE failed, not after the gate fails on a scraped week"
    )
    assert "--post-reset" not in fallback["run"], (
        "a failed scrape produced nothing, so the per-chain floor would assert something false"
    )
    assert "${{" not in fallback["run"], (
        "workflow inputs belong in env:, never interpolated into a run: block"
    )
    alert = _step(wf, "refresh", "Alert on repeated failure")
    assert steps.index(scrape) < steps.index(fallback) < steps.index(alert), (
        "the verdict has to be in the log before the alert issue links to it"
    )


def test_every_action_is_pinned_to_a_commit_sha():
    """A floating tag is a supply-chain hole: whoever controls the tag controls what runs in a
    workflow holding this repo's secrets. Tags are mutable; a commit SHA is not.

    Pinned as a ratchet over ALL workflows rather than a review habit, because the failure mode
    is a NEW workflow (or a new step in an old one) written the natural way — `@v4` — and
    nothing about a green run says the difference.
    """
    import re

    sha = re.compile(r"^[0-9a-f]{40}$")
    for path in sorted(WORKFLOWS.glob("*.yml")):
        wf = yaml.safe_load(path.read_text())
        for job_name, job in wf["jobs"].items():
            for step in job.get("steps", []):
                uses = step.get("uses")
                if not uses:
                    continue
                assert "@" in uses, f"{path.name}/{job_name}: {uses!r} has no version at all"
                ref = uses.rsplit("@", 1)[1]
                assert sha.match(ref), (
                    f"{path.name}/{job_name}: {uses!r} is pinned to a mutable ref — use the "
                    "commit SHA with the tag as a trailing comment"
                )


def test_the_scrape_probe_reports_counts_without_leaking_the_postal_code():
    """The Step 0 probe prints what a runner's scrape returned, and its log is world-readable.

    Two traps, both of which read as fine while being wrong:
      * the PLZ interpolated into `run:` — an expression is pasted in as TEXT before the shell
        exists, so the shell's quoting cannot protect it and the value lands in the log;
      * a `schedule:` trigger added later, turning a one-off experiment into a weekly scrape
        of the flyer sites for no consumer.
    """
    path = WORKFLOWS / "probe-runner-scrape.yml"
    if not path.exists():  # pragma: no cover - the probe is deletable once answered
        pytest.skip("the runner-scrape probe has been retired")
    wf = yaml.safe_load(path.read_text())
    triggers = _triggers(wf)
    assert set(triggers) == {"workflow_dispatch"}, (
        "the probe writes nothing and has no consumer — it must stay manual only"
    )
    assert wf["permissions"] == {"contents": "read"}, "a probe needs no write scope"
    step = _step(wf, "probe", "Scrape and report (counts only)")
    assert "PLZ" in (step.get("env") or {}), "the postal code must arrive via env"
    assert "${{" not in step["run"], (
        "an interpolated expression is pasted into the script as text — env, always"
    )
    assert "echo" not in step["run"], (
        "nothing in this step should echo; the script prints counts keyed on chain"
    )


def test_aws_access_is_federated_never_a_stored_key():
    """No long-lived AWS credentials exist in this repo, and that has to stay true.

    Both deploying jobs mint a short-lived token through GitHub's OIDC provider and assume a
    role that only `main` can assume (infra/bootstrap.yaml pins the `sub` claim exactly). A
    stored access key would be a permanent credential in a public repo's secrets, exfiltrable
    by any workflow change that merges — and the natural way to "fix" an OIDC permission error
    is to paste one in, which is why this is a test and not a convention.
    """
    for name in ("ci.yml", "scrape.yml"):
        wf = _load(name)
        raw = (WORKFLOWS / name).read_text()
        assert "aws-access-key-id" not in raw, f"{name}: a static AWS key appeared"
        assert "AWS_SECRET_ACCESS_KEY" not in raw, f"{name}: a static AWS secret appeared"
        for job_name, job in wf["jobs"].items():
            assumes = [
                s for s in job.get("steps", [])
                if "configure-aws-credentials" in (s.get("uses") or "")
            ]
            if not assumes:
                continue
            perms = job.get("permissions") or wf.get("permissions") or {}
            assert perms.get("id-token") == "write", (
                f"{name}/{job_name} assumes an AWS role but cannot mint an OIDC token"
            )
            for step in assumes:
                assert "role-to-assume" in step["with"], f"{name}/{job_name}: no role to assume"


def test_a_code_deploy_carries_the_live_week_forward_and_never_scrapes():
    """The function's database ships inside its package, which makes a code deploy dangerous
    in a way it never used to be: building a package without the live `week.db` would DELETE
    this week's deals, turning a backend merge into a silent data wipe. So the deploy job
    takes the file off the currently-live function, and the only thing allowed to produce new
    data is the weekly pipeline.
    """
    wf = _load("ci.yml")
    if "deploy" not in wf["jobs"]:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    steps = wf["jobs"]["deploy"]["steps"]
    fetch = _step(wf, "deploy", "Fetch the live week's data")
    build = _step(wf, "deploy", "Build the Lambda package")
    assert "get-function" in fetch["run"] and "Code.Location" in fetch["run"], (
        "the live package is where this week's data has to come from"
    )
    assert steps.index(fetch) < steps.index(build), (
        "the week must be in place before the package is built around it"
    )
    body = "\n".join(s.get("run", "") for s in steps)
    assert "app.scripts.scrape" not in body and "app.scripts.package_week" not in body, (
        "a code deploy must not be able to change the data — that is the weekly job's job"
    )


def test_the_postal_code_only_ever_reaches_a_step_through_env():
    """The PLZ is a secret in a public repo, so it may never be interpolated into a shell
    script: an expression in `run:` is pasted in as TEXT before the shell exists, so no amount
    of quoting protects it, and `set -x` or an `echo` would put it in a world-readable log.
    Store names embed it too, which is why every count these steps print is keyed on chain.
    """
    wf = _load("scrape.yml")
    users = [
        s for s in wf["jobs"]["refresh"]["steps"] if "PLZ" in (s.get("env") or {})
    ]
    assert users, "no step reads the postal code — has the scrape moved?"
    for step in users:
        name = step.get("name")
        assert "${{" not in step.get("run", ""), f"{name}: interpolation in a run: block"
        assert "set -x" not in step.get("run", ""), f"{name}: set -x would echo the value"
        assert "echo \"$PLZ\"" not in step.get("run", ""), f"{name}: the PLZ is echoed"


def test_the_deploy_waits_for_the_package_to_build_not_just_for_the_tests():
    """A dependency with no aarch64 wheel, or a package over Lambda's size limits, is a
    deploy-time failure with a green PR behind it. `lambda-package` moves that to the PR,
    where it is cheap — so the deploy must actually depend on it."""
    wf = _load("ci.yml")
    if "deploy" not in wf["jobs"]:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    assert "lambda-package" in wf["jobs"], "the package build must run on every PR"
    assert "lambda-package" in wf["jobs"]["deploy"]["needs"], (
        "the deploy must wait for proof the package can be built at all"
    )


def test_the_ci_path_filter_covers_the_infrastructure():
    """The filter decides whether a merge deploys. It listed only `backend/` when the
    infrastructure lived in another company's dashboard; now a change to the SAM template or
    the build script changes what production runs, and a filter that ignores them would leave
    `main` describing a deployment that was never applied."""
    wf = _load("ci.yml")
    if "deploy" not in wf["jobs"]:  # pragma: no cover - the job is optional by design
        pytest.skip("no deploy job in ci.yml")
    detect = next(s for s in wf["jobs"]["deploy"]["steps"] if s.get("id") == "detect")
    assert "infra/" in detect["run"], "a template or build-script change must deploy"
