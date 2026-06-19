# Learnings — grocery-helper

Concepts that came up while building this project — a Berlin grocery-deal app
(FastAPI backend + Expo/React Native app, deployed to Render + TestFlight). Each
entry is: **what it is**, **why it came up _here_**, and a one-line **takeaway**.
The general, transferable ones are also promoted to a cross-project TIL repo
(`~/til`).

## Deployment & infrastructure

### Monorepo
One Git repo holding multiple projects. Here, `backend/` (Python/FastAPI) and
`mobile/` (Expo) live in the same repo so they version and ship together.
**Takeaway:** monorepo = many apps, one repo — so tools must be told _which
subfolder_ to act on (build context, Root Directory, etc.).

### Docker build context
The folder Docker treats as the root when building; every `COPY`/`ADD` path is
relative to it, not to where the Dockerfile sits. Our Dockerfile is in `backend/`
and `COPY requirements.txt .` only works if the context is `backend/` — so Render's
**Root Directory = backend** sets that.
**Takeaway:** in a monorepo, point the build context at the sub-app, not the repo root.

### Bind the server to `$PORT`
Hosts (Render/Heroku/Fly) choose the port and pass it via the `PORT` env var. The
Dockerfile hardcoded `--port 8000`; changed it to `--port ${PORT:-8000}` so it uses
Render's port in prod and 8000 locally.
**Takeaway:** listen on `0.0.0.0:$PORT` with a local fallback — hardcoding a port is
the classic "works locally, fails on deploy" bug.

### Choosing a host, and why HTTPS needs a domain
Static hosting (GitHub Pages) serves files only — can't run an API. PaaS (Render/Fly)
runs your Dockerfile and gives free HTTPS on `*.onrender.com`. A raw server (EC2) =
full control but you set up TLS yourself, and a trusted cert needs a **domain you
own** (Let's Encrypt won't issue for `*.amazonaws.com`). iOS requires HTTPS, so we
chose Render for instant TLS.
**Takeaway:** no domain → PaaS for free HTTPS; own box → plan to buy a domain + set up TLS.

### Infrastructure as Code (`render.yaml`)
Declaring the service in a version-controlled file instead of clicking a dashboard,
so it's reproducible, reviewable, and documented. Our `render.yaml` Blueprint
declares the Docker web service, region, health check, and env vars.
**Takeaway:** config-in-a-file beats config-in-a-dashboard; it's reusable and the
diff is reviewable.

### CORS is a browser rule
Cross-Origin Resource Sharing is enforced only by **web browsers** — native apps and
`curl` ignore it. We set `CORS_ORIGINS=*`, which only matters for the Expo _web_
build and the `/stats` page; the native TestFlight app doesn't care.
**Takeaway:** CORS errors are always browser↔server; `*` is fine for a public,
read-only API, lock it down once there's auth/private data.

## iOS / mobile

### Bundle ID vs app name
The app **name** (under the icon) is changeable anytime; the **bundle identifier**
(`com.alihassan.groceryhelper`) is the permanent technical ID — editable until the
first App Store Connect upload, then locked. It's internal, so it needn't match the
name.
**Takeaway:** pick a name-independent bundle ID before the first upload; rename the
app freely after.

### EAS Build → TestFlight
EAS builds the app in the cloud (`eas build`, handling Apple signing) and uploads it
to Apple (`eas submit`); TestFlight distributes the beta to testers. Config lives in
`eas.json` (build/submit profiles) + `app.json` (bundle id).
**Takeaway:** EAS = managed mobile CI/CD; TestFlight = Apple's beta channel (needs a
paid Apple Developer account).

## App architecture (specific to this project)

### Serve-time computed fields (no DB migration)
Derive display/sort fields in the API serializer instead of storing them. Here,
`unit_price_cents`, the product `group`, and the recovered per-unit price are all
computed in `offer_to_out`, so adding them needed **no schema change/migration**.
**Takeaway:** if a field is a pure function of stored data, compute it on read —
fewer migrations, no stale columns.

### Geocode the _right_ coordinate
"Nearby" results are only as good as the center point you measure from. The store
picker centered on the scraped Lidl's coords, which sat ~3 km away in the next
district, so the user's actual local Edeka ranked #27 and got cut. Fixed by
geocoding the PLZ's real centroid (Nominatim).
**Takeaway:** garbage center → garbage "nearby"; geocode the thing you actually mean.

### Deterministic rules over an LLM for structured classification
A curated keyword/brand map classifies offers into categories — repeatable,
debuggable, free. Tuned EDEKA's "other" from 50→11 with zero regressions. Watch
substring traps (`" lamm"` must not match "Fla**mm**kuchen"; no bare `"müll"` so
"Müller" stays dairy).
**Takeaway:** for bounded, repeatable classification, rules beat an LLM — until the
long tail makes them brittle.
