# Infrastructure

The backend is one AWS Lambda function in `eu-central-1` (Frankfurt) serving a week of deals
that ships **inside its own deployment package** — `week.db`, a read-only SQLite file, next to
the code. There is no database server and nothing to keep warm.

## Why it is shaped like this

The previous host slept after 15 minutes and gave the container an ephemeral disk. That
combination meant `app/main.py`'s boot scrape — whose only condition is "the offers table is
empty" — ran on *every* cold start: ~15 paced outbound requests, 30–60 seconds before the API
would answer. The wait users felt was never the host starting up; it was the app rebuilding its
data from scratch because the data had nowhere to live.

Giving the week a home fixes that, and packaging it with the code buys three things a database
server would not:

- **A bad week cannot ship.** The weekly pipeline scrapes, exports exactly what `/api/offers`
  will return, and runs the data gate on *those files*. Only if it passes is anything deployed,
  so last week keeps serving. Previously the scrape wrote straight into the live database and
  the gate could only report damage already done.
- **Rollback is a CloudFormation operation**, because a week is a function version.
- **No cold-start database connection**, and nothing to migrate at startup — Lambda caps the
  init phase at 10 seconds.

The trade is that only pre-published postal codes work; an unpublished one honestly reads "no
deals published yet" instead of scraping on demand. See `docs/DECISIONS.md`.

## Files

| File | What it is |
|---|---|
| `template.yaml` | The SAM/CloudFormation stack: function, Function URL, log group, env. |
| `bootstrap.yaml` | Applied **once by hand**: GitHub OIDC trust, artifact bucket, two IAM roles. |
| `samconfig.toml` | `sam deploy` defaults, so both pipelines deploy identically. |
| `build.sh` | Builds the package: arm64 wheels + `app/` + the week's data. |
| `run.sh` | The Lambda handler — starts uvicorn behind the Lambda Web Adapter. |

## One-time setup

1. **An AWS account on the Paid plan.** The Free plan closes the account after six months; the
   always-free allowances this runs inside (1M Lambda requests, 400k GB-seconds and 100 GB of
   egress per month) continue indefinitely on the Paid plan. Both require a card. Expected
   bill: a few cents of S3 for deployment artifacts.

2. **Apply `bootstrap.yaml`** — CloudFormation → Create stack → upload the file, in
   `eu-central-1`. Parameters: `GitHubOrg`, `GitHubRepo`, `Branch` (`main`), and
   `CreateOidcProvider=false` if the account already trusts GitHub Actions (the provider is
   account-singleton). It is separate from `template.yaml` on purpose: the deploy role it
   creates has no IAM write permissions, so the pipeline cannot widen its own access or the
   function's. The two privileged decisions here are made by a human, once.

3. **Copy the outputs into GitHub Actions *secrets*** (not variables — they contain the account
   id, and this repo is public):
   - `DeployRoleArn` → `AWS_DEPLOY_ROLE_ARN`
   - `ArtifactBucketName` → `AWS_ARTIFACT_BUCKET`

4. **Set a budget alarm.** Billing → Budgets → a $1 monthly cost budget with an email alert
   (the first two budgets are free). Reserved concurrency would be the tighter cost cap, but a
   new account's concurrency quota is too low for Lambda to accept a reservation.

5. **Run the Weekly refresh workflow once** (`gh workflow run scrape.yml`). It creates the
   stack, because it is the job that has data to deploy. Until then the CI deploy job skips
   with a warning rather than failing.

If the first deploy fails with `AccessDenied`, the message names the one action and resource
the deploy role is missing. Add **that** action on **that** resource to `bootstrap.yaml` and
re-apply — never widen a statement to `*` to move on.

## Deploying

Two paths, deliberately unable to do each other's job:

- **Data** — `.github/workflows/scrape.yml`, Sundays. Scrape → export → gate → deploy.
- **Code** — the `deploy` job in `.github/workflows/ci.yml`, on a backend/infra merge. It
  **copies `week.db` out of the currently-live function** before building, so a code deploy
  cannot change what the app is serving. Without that step a backend merge would silently
  wipe the week.

Both wait for the stack to leave `*_IN_PROGRESS` first, since they share it.

## Measuring the cold start

The point of the migration, so measure it rather than quoting an estimate. The CI deploy job
prints it, and by hand:

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/grocery-helper-api \
  --filter-pattern '"Init Duration"' \
  --start-time "$(( ($(date +%s) - 3600) * 1000 ))" \
  --query 'events[].message' --output text
```

`Init Duration` is the cold-start cost: imports plus the adapter's readiness check against
`/health`. If it ever approaches Lambda's 10-second init cap, `AWS_LWA_ASYNC_INIT=true` moves
the wait onto the first request instead.

## Things that will bite

- **`DATABASE_URL` needs both `mode=ro` and `uri=true`.** Without `uri=true`, sqlite3 treats
  the whole string as a filename, creates it, and serves an **empty** database — every
  endpoint 200s with `[]` and nothing reports an error. `app/snapshot.py` refuses to start
  rather than allow it.
- **`week.db` must not be in WAL mode.** A WAL database needs to write sidecars, so it cannot
  be opened at all on Lambda's read-only filesystem. `app/scripts/package_week.py` refuses to
  package one.
- **Do not add a `Cors` block to the Function URL.** The app sets CORS headers itself; two
  owners send the header twice and browsers reject the response outright.
- **Do not add `environment:` to a deploying job.** It changes the OIDC `sub` claim to
  `repo:…:environment:<name>` and the deploy role stops being assumable.
- **The adapter layer ARN is version-pinned** in `template.yaml`. Bump it deliberately.
