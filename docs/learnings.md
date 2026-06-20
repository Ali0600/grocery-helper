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

### Free-tier PaaS: cold starts + ephemeral disk
Free PaaS tiers **sleep after idle** — the first request then cold-starts the
container (slow) — and give an **ephemeral filesystem** that resets on every
deploy/restart. Our Render backend re-runs its boot scrape on each cold start, and
its SQLite is wiped + recreated by `create_all` on deploy (so new columns auto-apply
there, unlike local).
**Why it came up:** the first `/health` after a sleep took 22 s; a new `Offer` column
needed no migration on Render (fresh schema each deploy) but did need a local DB
recreate.
**Takeaway:** on a free PaaS, never rely on local disk for persistence and expect a
slow first request after idle — use a managed DB / persistent disk for real data.

## iOS / mobile

### Bundle ID vs app name
The app **name** (under the icon) is changeable anytime; the **bundle identifier**
(`com.groceryhelper.berlin`) is the permanent technical ID — editable until the
first App Store Connect upload, then locked. It's internal, so it needn't match the
name. It must also be **globally unique across all Apple accounts**, so generic ones
like `com.groceryhelper.app` are often already taken (Apple rejects them at build
setup) — add a distinctive segment.
**Takeaway:** pick a name-independent, distinctive bundle ID before the first upload;
rename the app freely after.

### EAS Build → TestFlight
EAS builds the app in the cloud (`eas build`, handling Apple signing) and uploads it
to Apple (`eas submit`); TestFlight distributes the beta to testers. Config lives in
`eas.json` (build/submit profiles) + `app.json` (bundle id).
**Takeaway:** EAS = managed mobile CI/CD; TestFlight = Apple's beta channel (needs a
paid Apple Developer account).

### Expo slug vs name vs bundle ID
Three different identifiers: `expo.slug` names the project on Expo/EAS
(`@account/slug`); `expo.name` is the display name under the icon; the iOS
`bundleIdentifier` is Apple's app id. `eas init` proposed `@mhassan0600/mobile`
because the `create-expo-app` scaffold left `slug: "mobile"` (the folder name);
changed it to `grocery-helper` before creating the project.
**Takeaway:** set a meaningful `expo.slug` *before* `eas init` — it's your project's
name on Expo and is annoying to change after it's created.

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

### Audit the source's full payload — you may be dropping value
Structured data sources often carry more than you parse; periodically dump the raw
response and diff it against what you read.
**Why it came up:** the EDEKA flyer's app price (Milka 2,99 € vs the 3,29 € we showed)
was sitting in an ignored `SPECIAL_PRICE` deal the whole time — a field-level audit
surfaced it and confirmed what's genuinely unused (page position, variants) vs empty.
**Takeaway:** enumerate every field the source returns; "we already fetch it" ≠ "we
use it."

### Additive API changes are forward-compatible
Adding a new field to a JSON API response doesn't break existing clients — they
ignore keys they don't know — so you can ship a backend change *before* the client
that uses it.
**Why it came up:** adding `app_price_cents` to `/api/offers` and redeploying didn't
break the already-installed TestFlight build (it ignores the field); the badge only
appears once a new app build reads it.
**Takeaway:** additive API changes deploy safely on their own; only *removing* or
*renaming* fields breaks old clients.

### Client-side faceted filtering
Load the full dataset once and filter/sort it in the client across several axes,
instead of a server round-trip per filter change. The app fetches all of a PLZ's
offers (cap 2000) and does category, search, store, and sort filtering in JS —
instant, and search covers everything.
**Why it came up:** the category chip, €/kg sort, store filter, and search bar all
derive from one loaded list; the plan is to move search server-side only if a 4th
chain pushes a PLZ past the 2000 cap.
**Takeaway:** for a bounded dataset, client-side faceting is simplest and snappiest;
switch to server-side queries once it outgrows a single fetch.
