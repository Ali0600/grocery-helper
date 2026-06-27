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

### Validate fuzzy matching against the real dataset
Substring keyword matching is only as good as the data you test it on — German
compound words make short keywords match unrelated products you'd never guess from
reasoning alone.
**Why it came up:** the Basket matches a wishlist item's German keywords against offer
names; running it against the *live* offers (not just imagining cases) exposed real
traps — `tee` matched "**Tee**wurst" (a sausage), `weizen` matched "**Weizen**mehl"
(flour), `birne` matched "Glüh**birne**" (a lightbulb). The fixes were a category
pre-filter (drop non-food → kills a whole class at once) plus a few targeted `exclude`
guards — both discoverable only by testing on real data.
**Takeaway:** for fuzzy/substring matching, run it against the actual dataset early;
the false positives you find *are* the spec for your guard list.

### Separate display labels from match keywords (bilingual data)
When the UI language differs from the data language, keep two things apart: the
human-facing labels (for display + search) and the native-language keywords (for
matching).
**Why it came up:** the app's chrome is English but the deals are German, so the
Basket catalog carries an English label ("Strawberry"), a German label ("Erdbeere"),
and the German name-stems ("erdbeer") that actually match offers — a user can quick-add
in either language while matching always happens in the data's language.
**Takeaway:** decouple what you show from what you match on; conflating them forces the
user to speak the database's language.

### Green-gated deployment (deploy on a passing build)
Deploy only after CI passes, not on every push. With a PaaS that auto-deploys on push
(Render), turn its auto-deploy OFF and trigger a **deploy hook** from a CI job that
`needs` the test jobs and runs on the default branch only.
**Why it came up:** Render redeployed on every push regardless of test results; a
`deploy` job gated on `[backend, docker-build]` that curls the Render deploy hook makes
a red build block the deploy.
**Takeaway:** "deploy on green" means CI owns the deploy trigger — disable the
platform's push-auto-deploy so it can't bypass the gate.

### EAS Update (OTA) vs EAS Build
EAS **Build** compiles a new native binary (App Store/TestFlight); EAS **Update** pushes
JS/asset changes over-the-air to already-installed apps — no rebuild, no review. OTA only
reaches a build that embeds `expo-updates` at a matching `runtimeVersion`, so you still
need one build to "activate" updates, and any native-dependency change needs a fresh
build (bump `expo.version` under the `appVersion` runtime policy).
**Why it came up:** wired `eas update --branch production` into CI so mobile JS changes
ship without a full rebuild; the existing TestFlight build won't receive them until
rebuilt with expo-updates.
**Takeaway:** OTA-able = JS/asset-only on a matching runtime; anything native still needs
a build.

### Make secret-gated CI steps skip gracefully
A workflow step that needs a secret (deploy hook, API token) shouldn't fail on a repo
where the secret isn't set yet. Check for it first and exit 0 (or gate later steps on a
step output) so the pipeline is green from day one and "activates" once the secret is
added.
**Why it came up:** the Render deploy and EAS Update steps no-op with a clear log message
until `RENDER_DEPLOY_HOOK_URL` / `EXPO_TOKEN` exist — so CI passed on the very first run,
before any secrets were configured.
**Takeaway:** gate optional integrations on secret-presence and skip cleanly; a missing
secret is "not enabled yet," not a failure.

### Stale-while-revalidate (cache-first UI over a slow/sleepy backend)
Render the last cached data instantly, then fetch fresh in the background and swap it in
— instead of blocking the UI on the network. As a bonus the cache makes the app work
offline.
**Why it came up:** Render free tier sleeps after ~15 min, so a cold open showed a ~30s
spinner; caching the last deals per PLZ (AsyncStorage) and rendering them immediately
killed the spinner, with a small "Updating…" hint while revalidating and a weekly
(Sunday) expiry banner when the cache is old. A failed refresh keeps the cached list
instead of erroring.
**Takeaway:** for read-mostly data that's slow or flaky to fetch, cache-first +
background refresh beats a spinner; give the cache a domain-driven freshness boundary
(here, the weekly flyer expiry) rather than an arbitrary TTL.

### Prompt-to-reload for OTA updates (expo-updates)
By default EAS Updates download silently and apply on the *next* cold start. To offer an
immediate update, check imperatively (`Updates.checkForUpdateAsync` → `fetchUpdateAsync`)
and, when one is ready, prompt the user and call `Updates.reloadAsync()` on confirm.
**Why it came up:** added an "Update available — Reload now?" alert (on launch + on
foreground) so users get the latest JS without a full relaunch.
**Takeaway:** expo-updates is **inert in dev / Expo Go / web** (the fetch API rejects in
dev) — guard with `__DEV__` / `Platform.OS` / `Updates.isEnabled`; and it only runs in a
build that embeds expo-updates at the matching runtimeVersion.

### Don't cache empty/failed responses in stale-while-revalidate
A cache-first UI must only commit a *good* refresh to the cache. If the background fetch
can return empty or fail transiently, writing that result overwrites the cached data and
poisons it — the next launch shows the cache (deals), then the refresh wipes it.
**Why it came up:** on a sleepy free-tier backend, `/api/offers` returns `[]` during a
cold start (empty ephemeral DB); the revalidate was caching the `[]`, so deals vanished
on relaunch. Fix: never replace shown data with an empty result, only cache non-empty
payloads, add request timeouts, and trigger an on-demand repopulate (scrape) when empty.
**Takeaway:** in SWR, treat empty/error as "keep what you have," not "new truth" — only
the happy path updates the cache; and add a timeout so a hung request can't stall the UI.

### A taxonomy breadcrumb's leaf is often a brand, not a category
Third-party category paths (here Bonial `categoryPaths`) look authoritative but the
**leaf is frequently a brand node** (`… > Marken > Marken Lebensmittel > Heinz`), useless
for "what kind of product is this." The category usually lives in an **intermediate**
node, and only for some chains — others bury everything under a brands subtree.
**Why it came up:** asked to "use all categoryPaths," I surveyed the live taxonomy across
all 3 chains, mapped every real intermediate node (scanning the path most-specific-first,
not just the leaf), and added single-category brands for the brand-leaf cases — cutting
"Other" from ~11% to ~1% with zero test regressions.
**Takeaway:** don't trust a path's leaf — survey the real vocabulary, map the
intermediate nodes, and fall back to brand/keyword logic where the path bottoms out at a
brand; measure the win on the actual dataset, not a few hand-picked examples.

### Verify categories against product images — the source taxonomy lies
A third-party category path can be flat-out wrong, not just unhelpful. Auditing the
"fruits" bucket against the **product images** (image + name + category) found a peach
*aperitif*, banana *chips*, *lemonade* and a *yogurt* — and the source had even tagged
"Bananenchips" under **Obst** (fruit). So a definitive *form* word in the name
("…limonade", "…chips", "…joghurt") must beat even the path; a mere *flavour* word
("…chocolate") must not beat a brand (Häagen-Dazs chocolate is ice cream). Tooling: a
Pillow contact-sheet of all the category's images, viewed in one shot, makes the wrong
ones obvious.
**Why it came up:** the user spotted "drinks in Fruits"; an image audit confirmed 4
mis-files and drove a `_FORM_OVERRIDES` layer (form words → before the path) distinct
from flavour overrides (→ after the brand map).
**Takeaway:** for classification QA, look at the actual product images, not just names;
and order your override layers by how *definitive* the signal is (form > path > brand >
flavour > keyword).

### Match the change to its delivery channel
Where a change *lives* decides how it reaches users — pick the wrong channel and it never
arrives. App JS → OTA; native deps → a new build; **backend/data → a server deploy** (the
API decouples it, so the app needs no update at all).
**Why it came up:** a categorization fix (backend `categories.py`) didn't trigger the OTA
workflow and the user asked why. OTA only ships the mobile JS bundle; a server-side change
reaches the app through the **Render deploy + the app's next API fetch**, not OTA — and the
app's weekly cache means even then it shows only on pull-to-refresh.
**Takeaway:** before asking "why didn't my change ship?", map it to its channel — most
backend/data changes need no app update, just a deploy and a refetch.

### Choose a cache strategy by how often the source changes
Stale-while-revalidate (refetch on every open) suits frequently-changing data, but it's
wasteful and flaky for data with a known refresh cadence — make the cache *authoritative
for the period* instead.
**Why it came up:** the app re-hit a sleepy free-tier backend on every open even though
the grocery flyers only change weekly; the user pointed out "you don't need new data until
next week," so the cache became authoritative for the week (zero backend calls until past
the cached week's Sunday, plus a manual pull-to-refresh).
**Takeaway:** match revalidation frequency to the data's real change rate — for
weekly/periodic data, serve the cache for the whole period and only refetch when it
expires (or on explicit refresh).

### Dev DB and prod serve different datasets — don't compare counts across them
The local backend (`localhost:8001`, the web view) and Render (the iOS build) hold
*independently scraped* data, so a category count on one won't match the other.
**Why it came up:** the user saw "29 fruits" on iOS but "2" on web and expected them to
agree — but the web hit the dev `grocery.db` (only PLZ 10115/10115 ever scraped, partly
stale) while iOS hit Render's current-week scrape. The numbers were never comparable.
**Takeaway:** when a count looks "off," first establish *which backend/dataset* produced
it; reproduce against that exact source before debugging logic.

### Weekly-refreshed sources re-introduce data-quality bugs every cycle
A categorizer (or any data-cleaning rule) tuned on one week's data will face brand-new
edge cases next week, because the upstream feed churns its items.
**Why it came up:** last week's confirmed mis-files (Bellini, Bananenchips…) were gone
from this week's flyer, replaced by four *new* substring traps (Mango Sorbet, Vilsa water,
Pflaumentomaten, Apfelessig). The fix is always in the *classifier* (durable), not a
one-time data edit.
**Takeaway:** for a periodically-refreshing source, treat data-quality rules as
never-"done" — encode each fix as a tested rule so the next cycle's variants are caught,
and re-audit after each refresh.

### Don't define a component inside another component's render
A function component declared in the body of another component is a brand-new type on
every render, so React unmounts/remounts its subtree (losing state) — the React Compiler
lint flags it as "Cannot create components during render."
**Why it came up:** the Options modal had an inner `Action = (...) => <View>…</View>` helper
used as `<Action .../>`; ESLint errored. Renaming it to a plain `renderAction({...})`
function *called* (not used as JSX) fixed it with no behaviour change.
**Takeaway:** hoist sub-components to module scope, or if a render-local helper closes over
state, make it a lowercase function you *call* (`{renderRow(x)}`), never a capitalised one
you mount (`<Row/>`).

### Guard a destructive public endpoint with an optional, env-gated token
A maintenance endpoint (DB wipe) on an unauthenticated public API should be gated, but the
gate can be opt-in so local dev stays friction-free.
**Why it came up:** `POST /api/reset` wipes all offers — fine for the owner, risky as an
open public hit. It checks `ADMIN_TOKEN` only when that env var is set (otherwise open, like
the existing `/api/scrape`), so dev needs no token while prod can lock it down by just
setting the env.
**Takeaway:** for owner-only destructive actions, enforce a token *conditionally on its
presence* — zero-config in dev, lockable in prod without code changes.

### Geo-personalized sites are driven by an IP-seeded cookie — pin it for determinism
A site that shows "local" content usually resolves your location from your IP on first
visit and stores it in a cookie/header; later requests read that, not the IP. So the same
URL returns different content from different hosts unless you set the location yourself.
**Why it came up:** the same grocery PLZ scraped ~1506 offers from Render (Frankfurt
datacenter) but ~1087 locally (Berlin) — meinprospekt's publisher page picked *regional*
brochures from each host's IP geo. The decisive test: a `location` cookie with Munich
coords returned Munich brochures *from a Berlin IP*, proving the cookie overrides IP.
**Takeaway:** when scraping geo-personalized content, never trust the host's ambient
geo — discover the location mechanism (usually a cookie or header) and pin it to the
*target* location, so results are correct and identical regardless of where the scraper runs.

### A non-deterministic upstream count needs deduping at the source, not just at serve time
If an upstream returns overlapping/duplicated records whose *quantity* varies by request,
any count you report off the raw rows will look unstable even when the real (unique) data is
the same.
**Why it came up:** two scrapes of one PLZ reported 1087 vs 1509 "offers" — alarming until
dedup showed the unique sets were nearly identical; the extra rows were duplicate brochures.
Deduping only at serve time hid it from users but left the raw count (and the DB) noisy.
**Takeaway:** dedup at ingestion (not just at read) when the upstream's record count is
non-deterministic, so stored size and any reported counts reflect distinct entities.

### Don't assume a payload field is redundant — measure it
A field that looks like a duplicate of data you already have can carry finer-grained truth.
**Why it came up:** each flyer offer has a `publicationProfiles[].validity` window that the
notes had dismissed as "redundant with the brochure dates." It wasn't — it's the *per-offer*
on-sale window, so ~56% of Lidl deals are actually day-limited (Thu–Sat etc.) while we'd been
stamping all of them with the whole-week brochure window (overstating validity, never
expiring mid-week). A quick scan of the raw payload revealed the real signal.
**Takeaway:** before discarding a payload field as redundant, scan its real values across the
dataset — finer-grained per-record data often hides behind a field you assumed duplicated a
coarser one.

### Convert UTC day-boundaries to the target timezone (and bundle tzdata)
Timestamps at "midnight somewhere" are stored in UTC at an offset that shifts with DST, so
deriving the local *calendar day* needs the real zone, not a fixed offset.
**Why it came up:** offer validity boundaries arrive as UTC `T22:00` (Berlin midnight in
summer) / `T23:00` (winter); a fixed +2h offset got the start right but the exclusive end
wrong in winter. `zoneinfo("Europe/Berlin")` handles DST — and adding the `tzdata` pip
package keeps it working on slim Docker images that strip the system tzdb (host-independent).
**Takeaway:** for "local day" math, convert through the IANA zone (`zoneinfo`), never a fixed
offset; ship `tzdata` so it's deterministic across dev, CI, and slim production images.

### Move LLM work to authoring time, not runtime
If generated content changes on a slow, known cadence, an LLM can author it *offline* and you
ship the result as static data — no runtime model call, API key, cost, or cold-start latency.
**Why it came up:** the "AI Recipes" feature. Instead of a backend endpoint calling Claude per
request, Claude Code authored recipes from the current deal DB into a bundled `recipes.ts`,
shipped via OTA, and the app renders them fully offline — regenerated weekly when flyers
refresh. Zero runtime secrets/cost, works on a sleeping free-tier backend.
**Takeaway:** for content that refreshes on a periodic cadence, prefer build/author-time LLM
generation + static delivery over a runtime API call — cheaper, simpler, offline-capable.

### Ground LLM output to your structured data with a deterministic matcher
An LLM names entities in free text; a deterministic matcher links those names back to your
real records so the UI shows verified facts (prices, IDs), not the model's guesses.
**Why it came up:** recipe ingredients are LLM-authored German terms; the app reuses the
Basket keyword matcher (`bestMatch`) to resolve each to an actual on-sale offer and show its
live price/store — the LLM never invents a price.
**Takeaway:** let the LLM produce the prose/structure, but compute anything factual
(prices, links, availability) deterministically from your own data at render time.

### Retrofit Alembic onto an existing database by stamping the baseline
`alembic upgrade head` on a DB that already has the tables (created by `create_all`)
but no `alembic_version` table will try to re-create them and crash. The fix: detect
that case and `alembic stamp head` (record the baseline revision without running it),
after which normal upgrades apply.
**Why it came up:** we replaced startup `create_all` with `alembic upgrade head`
(`app/migrations.py`). Render's ephemeral SQLite is always fresh (upgrades from base),
but an existing dev `grocery.db` (and any persistent Postgres made the old way) would
have crashed — so `run_migrations()` stamps when it sees tables-but-no-version.
**Takeaway:** when adding migrations to a pre-existing schema, baseline it with
`stamp`, don't let the first `upgrade` re-create what's already there. Use
`render_as_batch=True` so autogenerated ALTERs also work on SQLite.

### jest-expo: unit-test pure logic without rendering
An Expo app's pure modules (no React/RN imports) are testable with the `jest-expo`
preset alone — no component rendering, no native mocks needed. Two config gotchas:
restrict `testMatch` to `*.test.ts` so a `__tests__/fixtures.ts` helper isn't run as
an (empty) suite, and add a `/// <reference types="jest" />` d.ts so `tsc --noEmit`
sees the jest globals without restricting `compilerOptions.types` (which would drop
other ambient types). Install SDK-matched versions via `npx expo install jest-expo
jest @types/jest --dev` (per `mobile/AGENTS.md`).
**Why it came up:** adding the first mobile tests — basket/recipe/format/catalog logic
is all pure, so the suite is fast and needs no RN test renderer.
**Takeaway:** test pure logic at the function level (cheap, fast); keep test fixtures
out of `testMatch`; satisfy `tsc` with a triple-slash ref, not a `types` whitelist.

### Expo SDK lockstep vs per-package auto-updates (Dependabot)
Expo manages react / react-native / expo-* / jest-expo as one version-locked set; bumping any of
them individually breaks the others.
**Why it came up:** Dependabot's weekly npm version-updates opened PRs bumping react-native
0.85.3 → 0.86.0, which `ERESOLVE`-failed `npm ci` because `jest-expo@56` peer-requires
`@react-native/jest-preset@^0.85.0`. All 4 mobile npm PRs failed the same way. We removed npm
*version*-updates from `dependabot.yml` (kept pip + actions) and rely on `npx expo install` for SDK
bumps; Dependabot *security* updates (CVE-driven) still cover npm.
**Takeaway:** don't run a per-package version-updater on an Expo (or any framework-pinned) npm
project — version those deps via the framework's installer. `0.x` "minor" bumps are breaking, so
group/minor filters won't save you.
