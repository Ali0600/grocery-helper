# Grocery Helper — agent notes

Berlin grocery-deal finder: Python/FastAPI backend (scrapers → SQLite/Postgres →
API) + React Native (Expo) app. See [README.md](README.md) for the full picture.

## Layout
- `backend/` — FastAPI app + scrapers (`app/scrapers/`), classifier
  (`app/categories.py`), tests (`backend/tests/`, pytest).
- `mobile/` — Expo app (TypeScript); `src/screens/`, `src/components/`,
  `src/api.ts`, `src/storage.ts`.

## Common commands
- Backend **+ web together**: `./dev.sh` (root) — runs uvicorn (:8001) and Expo Web
  (:8081) concurrently, Ctrl-C stops both (kills the process group so uvicorn's reload
  child + Metro workers die too). Preflights venv/node_modules/port-8001-free.
- Backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001`
- Backend tests: `cd backend && source .venv/bin/activate && python -m pytest -q`
  (CI also runs `--cov=app`; add a `DB` migration drift check via `alembic check`).
- Backend lint: `cd backend && source .venv/bin/activate && ruff check .` (`--fix` to autofix)
- DB migration (after a model change): `cd backend && alembic revision --autogenerate -m "msg"`,
  review the file, commit. Runtime auto-runs `upgrade head` at startup (`app/migrations.py`).
- **Weekly audit's contact sheets** (2026-08-17, kept instead of rebuilt ad-hoc each week):
  `SCRAPE_REQUEST_GAP_S=0.15 python -m app.scripts.contact_sheets` — labelled per-category
  sheets of every served product's photo, plus `--manifest` (counts only, no fetch) and
  `--category X`. **Override the gap**: the 0.7s default protects the flyer AGGREGATORS, which
  throttle by answering 200 with less content; the images come from a static CDN, and at the
  default a ~2,000-image run takes ~100 minutes instead of nine. Pillow is a declared dep now —
  it had been installed ad-hoc in the venv and was missing from any fresh checkout.
- Mobile typecheck: `cd mobile && npx tsc --noEmit`
- Mobile tests: `cd mobile && npm test` (jest-expo; CI runs `npm test -- --ci`). **Component tests
  work now** (`__tests__/StoresModal.test.tsx` is the first) — three things had to be true and each
  one fails with a misleading error: (1) `testMatch` must include **`*.test.tsx`** (it was `.ts`
  only, which is why RNTL sat installed-but-unused); (2) `setupFiles` needs
  gesture-handler's own `jestSetup.js` (else `RNGestureHandlerModule.default.install is not a
  function`, since every modal is an `AppModal`); (3) `jest-setup.js` sets
  **`IS_REACT_ACT_ENVIRONMENT`**, which jest-expo doesn't — React 19 then refuses `act()`.
  **RNTL v14's `render` is `async`** (it was sync in v13): `await render(...)`, or `screen` is
  unbound and *every* assertion fails with "render function has not been called". **`fireEvent`
  is async too** (`fireEvent.press` returns `Promise<void>`) — **await it**. An unawaited press
  opens overlapping `act()` scopes ("You seem to have overlapping act() calls") and the state
  update is silently DROPPED: the handler fires, no re-render follows, and the test fails far
  away with "unable to find …". A single press usually survives because the next `await findBy*`
  flushes it — flows with several presses in a row do not. Also: **jest-setup's AsyncStorage
  `clear()` must be awaited**; a dangling clear let one test's storage leak into the next (every
  test that re-seeds its own key masked it, until `hiddenItems` — which isn't re-seeded — silently
  emptied the next test's deals list).
  `jest-setup.js` also wires the official **AsyncStorage in-memory mock** (cleared per test — seed
  via plain `AsyncStorage.setItem`) and stubs **@expo/vector-icons** (renders `icon:<name>` as
  text; the real module needs expo-asset, which Metro resolves but jest can't). CI runs
  `npm test -- --ci --coverage`: `collectCoverageFrom` covers **all of src/** (jest's default
  counts only files tests import — the old "81%" was really 64%), and `coverageThreshold` in
  package.json is a **ratchet** set just under the measured floor — raise it as coverage climbs,
  never lower it to make a PR pass. `__tests__/DealsScreen.test.tsx` pins the cache contract
  (fresh cache = zero backend calls; version mismatch = stale-not-absent; empty refresh never
  clobbers; cold-PLZ on-demand scrape) — proven to fail against the reverted version check.
- Mobile lint: `cd mobile && npm run lint` (ESLint, `eslint-config-expo` flat config)
- Mobile run: `cd mobile && npx expo start` (open on the iOS simulator).
- Web run: `cd mobile && npm run web` (Expo Web / react-native-web; serves the
  **same** app at `http://localhost:8081`). `App.tsx` centers a max-width column on
  web; the backend already sends permissive CORS, so it talks to the local API.

## Important notes / gotchas
- **The app has THREE VERTICALS and opens on a home screen** (2026-07-30; Drinks added
  2026-08-18): `HomeScreen` renders one big button per vertical, and `App.tsx` holds
  `vertical: Vertical | null` (`null` = home). There
  is still **no navigation library** — adding one is a native dep (a new build, not an OTA), and
  the app already navigates by rendering modals over one screen. `DealsScreen` takes its first-ever
  props, `{ vertical, onHome }`. The vertical is **not persisted**: the app always opens on Home
  (the user framed it as *the homepage*, and any section is one tap away — one line to change).
  **The split is load-bearing, not navigation sugar.** `/api/offers` caps at 2000 and the app loads
  the whole set; measured for one Berlin PLZ, grocery is **1674**, Rossmann adds **282** and dm
  **213** → **2169 as one query, i.e. past the cap**. Scoping each vertical to its own query is the
  only reason they fit.
  - **A vertical has TWO SHAPES, and the second one is newer than most of this section.**
    Grocery and Drugstore are **chain sets** — a Rossmann is a drugstore whatever it sells — and
    their chains are disjoint, which is why "a chain's vertical" reads as a fact about the chain
    everywhere below. **Drinks is a CATEGORY set** over the *grocery* chains (`soft_drinks` +
    `alcoholic`), so any sentence here of the form "the vertical is decided from the chain slug"
    is now true only of the first two. The user asked for drinks out of the food list ("I'm just
    looking for food and it's distracting"), and the cap made it the right answer anyway:
    measured 2026-08-18, grocery **alone** had reached **1926 of 2000** (96%), and the carve-out
    takes it to **1689** with Drinks at **237**.
  - **`DRINK_CATEGORIES` is named ONCE and used twice** — as Drinks' `categories` and as
    Grocery's `excluded_categories` — because those are one statement seen from either side. A
    second literal would be a partition that can drift, and both drift directions are silent: a
    drink served in **both** sections, or in **neither**. `tests/test_verticals.py` asserts the
    agreement generically over `VERTICALS`, not over the two names that exist today, so a fourth
    section inherits the check. Both failures are sabotage-proven.
  - **`verticals.py` cannot import `categories.py`** (it is a leaf module that `scrapers/run.py`
    and `store_locator.py` import), so a typo'd slug in `DRINK_CATEGORIES` would be a filter
    matching nothing, silently. That is what `test_carved_out_categories_are_real_category_slugs`
    buys back.
  - **Coffee deliberately stays in Grocery** (the user's call): a bag of beans is an aisle you
    cook from, not a bottle you drink. Pinned by a test, because it is exactly the kind of thing
    a later "tidy-up" folds in.
  - **Backend**: `app/verticals.py` (`VerticalSpec`, `VERTICALS`, `CHAIN_VERTICAL`) — a frozen
    constant, **no DB column**: a chain's vertical is a fact about the chain, not about a `Store`
    row, so there's no migration and it can't drift per-row. A leaf module with no app imports, so
    `api/offers.py`, `store_locator.py` and `scrapers/run.py` can all use it without a cycle.
  - **`vertical` is a query param** on `/api/offers`, `/api/categories`, `/api/offers/payloads`
    and `/api/offers/category-traces`. Built as a `Query(pattern=…)` from `VERTICALS`, so an
    unknown value **422s** rather than silently widening to every chain. The two bulk endpoints
    take it because they promise to mirror `/api/offers` — without it a drugstore session
    downloads every grocery payload and that contract quietly stops holding. Their test is
    **parametrized over `VERTICALS`**, so a section added later inherits the promise.
    **That 422 is why a new section ships BACKEND-FIRST**: an app asking for one the deployed
    backend doesn't know gets an error, not a fallback. Merge and deploy the backend, confirm
    `?vertical=<new>` serves, *then* publish the OTA.
  - **Omitting it = GROCERY** (changed 2026-07-30 when dm landed; it used to mean *no filter*).
    All chains together is now **2169**, so an unfiltered read would silently truncate at 2000.
    Grocery is the right default rather than a bigger cap because the only clients that omit the
    param are builds older than the vertical release — they predate Drugstore entirely, have no UI
    for it, and were being served Rossmann rows inside a grocery list. Every vertical-aware
    endpoint applies the default through the single `_scoped()` helper in `api/offers.py`
    (renamed from `_vertical_chains` on 2026-08-18 — it now applies a category filter as well as
    a chain one), so `/categories` chips can't advertise a vertical `/offers` won't serve.
    Since 2026-08-18 the grocery default also **excludes the drink categories**, so an old client
    sees no drinks — the same bargain as above, since it has no UI for that section either.
    `Offer.category` is `NOT NULL`, which is what makes the `notin_` safe; a nullable column
    would need an explicit `IS NULL` arm or it would silently drop rows. **A further chain
    still needs server-side `q` search** — the per-vertical queries are what bought the headroom.
- **Rossmann is the drugstore vertical's chain** (`bonial.py` `RossmannScraper`, publisher
  **`DE-1064`**, page `/rossmann-de`). The shipped `MeinprospektScraper` parses it with **zero
  parser changes**: measured 282 served offers for a Berlin PLZ, 100% images, 58% €/kg-sortable.
  It runs in the same `run_scrapers` pass as the grocery chains — one scrape fills both verticals;
  the vertical is decided at serve time from the chain slug.
  - It publishes **up to THREE** brochures at once, and this line said "two" until 2026-08-09,
    when the third cost the chain a week: the weekly "Mein Drogeriemarkt" (23–26 pages), a
    ~2-month "Schulaktion" (18 pages, dropped by `MAX_FLYER_DAYS`), and — intermittently — a
    **small multi-week supplement** ("Mein Drogeriemarkt" too, 6 pages, 11-day span, 2 offers).
    **`MAX_FLYER_DAYS` cannot separate the last two from the weekly**: 11 days is under the
    limit, because span is the wrong discriminator. `_select_brochures` used to early-return on
    *any* active brochure, so the supplement shadowed the 26-page weekly starting that evening
    and Rossmann served **2 offers of 302** — for the whole week, since the Sunday reset is the
    only scheduled scrape. It now unions the active set with brochures starting **today or
    tomorrow (Berlin)**; see that function's docstring for why the two sets can never overlap.
    Only the new per-chain floor in `verify_deals.py` made it visible — `chains >= 2` passed.
  - Its offers carry a **per-offer `publicationProfiles` window** that starts a day AFTER the
    brochure's own `validFrom` (Mon vs Sun), so the parser's per-offer validity is load-bearing
    here: taking the brochure dates would advertise the whole flyer a day early.
  - **dm is NOT a flyer chain and never can be** — but it IS a deals chain, via its clearance
    API (see the dm note below). Its publisher `DE-909` (`/dm-de`) exists and lists a brochure,
    but that brochure's `/pages` returns **`{"contents": []}`** — zero offers, ever. **Don't
    re-probe meinprospekt for dm.** Rossmann is the mirror image: its flyer works perfectly while
    its own web shop is bot-walled (a Fastly JS challenge on every path).
  - **OSM tags a Drogerie `shop=chemist`, not `shop=supermarket`.** `_overpass_query` takes a
    `tags` argument (default unchanged **byte-for-byte**, pinned by a test) and the real callers
    pass `ALL_OSM_TAGS`, the union across verticals — without it the store directory silently
    lists no drugstore at all, whatever `CHAINS` says.
  - **Drugstore categories are resolved INSIDE the layer-1 non-food branch** (2026-07-30):
    `_DRUGSTORE_PATH_MAP` (source node → slug) then `_DRUGSTORE_RULES` (name/brand tokens),
    via `_drugstore_hit`, running after `_FOOD_RESCUE` and before the fall to `household`.
    11 new slugs appended to `CATEGORIES`: hair/face/body/dental/makeup/fragrance/baby/
    health/cleaning/laundry/pet. **0-regression BY CONSTRUCTION** — the step is only
    reachable where the answer was already `household`, so nothing food can move; the
    full-DB diff agreed (**638 rows moved, 0 out of a food category**). Drugstore
    `household` went **91% → 36%**; grocery's shrank 19% (a Nivea deo at Lidl is body care,
    which is the point, not a side effect). `makeup` currently serves 0 — no make-up in this
    week's flyers — and `/api/categories` simply omits it.
    - **Order inside layer 1 is load-bearing**: food rescue → drugstore → veto → household.
      A `_RESCUE_VETO` word must NOT block a drugstore aisle: `maschine` is a veto token
      (for Kaffeevollautomaten) and a substring of "Finish Spül**maschinen**-caps", which
      really is Cleaning. And the food rescue must stay first, or `Waschmittel` claims the
      spare ribs the source files under it.
    - **`_DRUGSTORE_VETO` is checked before the PATH map**, because the path decides first:
      the source hangs a RAMA Cremefine (cooking cream) and an AMICELLI Milchcreme
      (chocolate wafer) off `Körperpflege > Creme`. They stay `household` — the honest
      "can't tell" — rather than a confidently wrong Body & Shower.
    - **Six candidate rules were rejected, every one caught by the diff, not by reading**
      (the same score as the image audit): three BRAND CONTAINERS — `Marken Parfum` made
      *Axe Duschgel* a fragrance, `Marken für Tiere` made an *EDEKA Feine Pastete* and a
      *REWE Salatschale* cat food, `Marken Baby`; `Hautpflege` (spans face AND body —
      "NIVEA Pflegedusche" is a shower gel); `Babynahrung` (a FOOD node — *Huel
      Trinkmahlzeit* is an adult meal drink); `Textilreinigung` (covers drying hardware —
      a *LEIFHEIT Wäscheschirm*, even a *WORKZONE Konstruktionsschnur*). Plus three token
      traps: `mund` ⊂ **Mund**harmonika (a harmonica), a bare `vitamin` (an ingredient claim
      across cosmetics — it made a Garnier face serum a supplement), and `müllbeutel`
      (bin bags were deliberately routed to household by an earlier audit).
      **Only the path nodes that NAME A PRODUCT KIND are safe. Simulate every candidate over
      the full DB before keeping it — the editor cannot see these.**
  - **`verify_deals.py` is now PER VERTICAL** (`PROFILES`). One global gate would be wrong both
    ways: `chains >= 5` goes red the moment the set is scoped, and a floor loose enough for a
    one-chain drugstore couldn't detect a grocery collapse. Grocery keeps its measured thresholds;
    drugstore is **chains ≥2 / offers ≥250** (this line said "≥1 / ≥150" until 2026-08-08 — it had
    drifted from the script and cost a wrong diagnosis; read `PROFILES`, not this file), with
    **no €/kg floor** — Rossmann measures 48–58%, straddling grocery's 50% floor, and €/kg means
    little for cosmetics. Every vertical runs even after one fails, so a red grocery can't hide a
    collapsed drugstore. **Drinks** (2026-08-18) is chains ≥6 / offers ≥120 / **€/kg ≥80%** — the
    strictest coverage floor in the file, deliberately: everything in that section is sold by the
    litre and carries a Grundpreis (measured 98.3%), so a drop is a parse regression, not a bad
    flyer week. Its `other_pct` is **structurally 0** — `_scoped` serves only the two drink
    categories, so no `other` row can reach it; the key exists so every profile has the same
    shape, not because it gates anything, and `test_every_profile_has_the_same_shape` is what
    stops a future section omitting `min_chain_offers` (read with a plain subscript, so the
    omission is a Sunday-morning `KeyError` against production).
  - **`chains >= N` counts PRESENCE, so a nearly-empty chain reads as a healthy one** — hence
    `min_chain_offers` (100 for the two chain-set verticals; **15** for Drinks, whose whole
    section is 237 offers), added 2026-08-08 after the drugstore vertical served
    `rossmann=2` against 287 the week before and grocery served `aldi=4` (its literal `_sample()`
    size) on the same day. Neither registered: the total floor is carried by the survivors, so at
    the measured counts **three of five grocery chains could fall back to samples and still clear
    800** (1562−247−234−274+4+5+5 = 821). Sample sizes are tiny and per-scraper (**dev only
    since 2026-08-17** — see `scrape_sample_fallback`): lidl/aldi 4,
    rewe/edeka/edeka_center/rossmann 5, dm 6.
    - **Gated behind `--post-reset`, which `scrape.yml` passes**, because a chain empties
      legitimately between brochures (Rossmann's week ends Friday, so on a Saturday it really does
      serve ~2). Right after the weekly wipe-and-re-scrape every chain should be full, so a thin
      one there is an incident. The flag **defaults off**, so `test_workflows.py` pins that the
      workflow passes it AND that the gate step runs after the reset — otherwise the gate silently
      goes blind again with every `test_verify_deals.py` case still green.
    - **An ABSENT chain can never appear here** (it has no key to count), so the two checks
      partition cleanly: absent → `chains`, present-but-thin → `min_chain_offers`. That's why this
      check can't print a `0` — a property, not a gap.
    - **Calibrate on SUNDAY POST-RESET counts only.** `/api/offers` filters `valid_to >= today`
      with **no `valid_from <=` clause**, so a chain's day-limited windows all serve from day one;
      measuring with a `valid_from` clause reads ALDI as 150 instead of its real 247 and sets the
      floor far too high. Healthy min is 213 (dm) / 234 (edeka); the worst observed failure is 38
      (Lidl's partial parse on 2026-07-19). The binding constraint is **dm**, not ALDI.
    - **Everything printed is keyed on `chain`, never `store_name`** — `bonial.py` builds
      `f"{store_label} {plz}"`, so store names embed the PLZ secret. Pinned by a test.
    - A response of exactly the 2000 serve cap now **fails**: truncation happens after a sort by
      `discount_pct` with nulls last, which is disproportionately REWE and ALDI — the chains
      nearest the floor — so at the cap the per-chain numbers would be the first thing to lie.
  - **The three caches are keyed PER VERTICAL** (`dealsCache:grocery`, `dealsCache:drugstore`, same
    for `payloadCache`/`traceCache`). Sharing one key would make every switch a cache miss — a
    cold-start round trip on the free tier, for a control the user taps constantly. `clearDealsCache`
    and `clearAllData` build their `multiRemove` lists from the vertical list so they can't miss one.
    Verified live: switching Drugstore → Grocery makes **zero** network calls.
  - **Persisted prefs stay SHARED and that's correct**: `hiddenStores`/`storeLens` hold chain slugs,
    `myCategories`/`sortByCategory` hold category slugs, and the two verticals' slugs never collide.
    The existing only-when-present guards (`activeStoreLens` intersects with available chains,
    `buildMineSections` skips slugs with no offers) already make a cross-vertical value **inert**.
    **The one place inertness isn't enough is the LANDING rule** — a user whose picks are all
    grocery would open Drugstore straight into "None of your categories have deals this week". So
    `dealFilters.shouldLandOnMine(myCategories, cats)` gates it on a category actually served here,
    and it is decided **once**, when categories first arrive (a later refresh must not yank the user
    out of a view they chose). Basket/History/hidden are shared deliberately — one basket spanning
    both shops is one shopping trip.
  - **Recipes is grocery-only** (`verticals.hasRecipes`): they're authored from grocery ingredients,
    so the surface would be empty — and hiding it is what frees the header slot Home now occupies.
  - **The header is FULL.** Measured at 375pt: chevron 17–43, pin 55–93, six actions 105–373 — the
    header is exactly **373 of 375** wide, i.e. **2px of slack** in Grocery (Drugstore ends at 358).
    Anything added here overflows. Measure rects, don't eyeball.
- **dm is the drugstore vertical's 2nd chain, from its CLEARANCE API — not a flyer**
  (2026-07-30, `app/scrapers/dm.py`). `GET product-search.services.dmtech.com/de/search/crawl
  ?isSellout=true&pageSize=1000&currentPage=0` is the site's own "Ausverkauf" page: **the whole
  feed in ONE request** (measured `count: 251`, `totalPages: 1`), of which **213–214 are in-store**.
  This does not contradict "dm's catalog isn't a deals source" — the *catalog* (21k products,
  everyday prices, no validity) still isn't. The **sellout facet** of it is.
  - **Best discount coverage of any chain we scrape: 100% carry a struck `previous` price**
    (median 48%, range 9–62%, 0 inverted) — REWE and ALDI mostly carry none. Also 100% image,
    100% category, 100% `gtin`/`dan`; 35% €/kg-sortable after unit conversion.
  - **`netPrice` is NET OF VAT — never read it as the price.** Every product carries both
    `price` (7,95 €) and `netPrice` (6,68 €), at a rate that varies by product class (19%
    cosmetics, 7% food). A test pins the gross value; reading `netPrice` fails it.
  - **The Grundpreis' leading number is the PACK SIZE**: `"0,036 kg (81,94 € je 1 kg)"`. The
    per-unit price is the *parenthesised* one, and `je 1 kg` matches none of `unit_price.py`'s
    patterns, so the scraper emits the canonical `"1 kg = 81.94"` itself. `g`/`ml` fold onto the
    kg/l axis so they sort; `St`/`Wl`/`m` keep the source's casing and stay unsortable.
  - **"Nur Online" items are skipped** — 37 of 251, flagged per-product on `eyecatchers`. They
    aren't stocked in a branch, and the app is about deals you can walk in and buy.
  - **It runs OUTSIDE `run_scrapers`' `if store.lat is not None` guard**, unlike every flyer
    chain. dm's prices are **national** (verified identical with and without `storeId`), so it
    needs no coordinates — and gating it there would delete the whole chain, with no error, on
    exactly the runs where Lidl already degraded to samples. Pinned by a test.
  - **New `Offer.source = "clearance"`** (a third value beside coupon/flyer); `/api/offers`'
    `source` query pattern had to be widened or filtering on it 422s.
  - **`valid_from`/`valid_to` are NULL** — dm publishes no end date; an item runs until sold out.
    NULL passes every serve-time validity filter, so the **weekly Sunday `/api/reset` is what
    clears sold-out items**; between resets `/api/scrape` only upserts, so the set can only grow.
  - **The clearance list is volatile** (251 → 250 within an hour of probing), so
    `verify_deals.py`'s drugstore profile leans on **`chains >= 2`**, not a tight offers floor:
    a size swing is normal, a chain dropping to 1 is not. Only one week has been observed.
  - **dm's own category leaf is mapped in `_DRUGSTORE_PATH_MAP`** (2026-07-30). dm sends ONE
    flat leaf per product with 100% coverage, and `_path_nonfood` treats any path whose root
    isn't the food root as non-food — so layer 1 always decides for dm, which is why the
    drugstore step reaches it at all and why unmapped leaves blob. 40 leaves mapped: **60 rows
    moved, 0 unexplained regressions**, dm `household` **54% → 28%**, drugstore chip household
    44% → 33%, Make-up 56 → 80.
    - **Prefer dm's leaf over its product NAME.** dm's cosmetics names are shade-heavy and
      collide with tokens tuned for grocery flyers: a CATRICE blush in shade "Coral Cutie" was
      matching `_DRUGSTORE_RULES` `coral` — the Henkel DETERGENT brand — and served as Laundry.
      The path map is consulted before those tokens, so mapping the leaf fixes the class.
    - **A path-map entry for something `_FOOD_RESCUE` already catches is DEAD CODE.** Layer 1
      runs food rescue → drugstore → veto → household, so a rescued product never reaches the
      map. `Saaten & Körner` (dm's GARDEN SEED packets, "Saaten, Zucchini (Zuboda)") looked like
      a map entry and changed nothing — `zucchini`/`rucola`/`feldsalat` are rescue tokens, so the
      packets were being served in the **Vegetables** chip. The fix is a `_RESCUE_VETO` token,
      and it is the **brand** (`stadt land blüht`), not a bare `saaten`: that is a substring of
      "Meisterbrot mit Saaten" and "Kerne-Saaten-Granola", and the bakery rescue exists precisely
      to pull breads out of a non-food path.
    - **The drugstore step MAY return a food slug** — `_food_rescue` already does from the same
      branch — and must, for `Tee`/`Herzhafte Brotaufstriche`/`Bonbons & Fruchtgummi`: layer 1
      can never fall through, so nothing downstream could rescue them. The
      "every drugstore slug is a real category" test now carries an explicit allowlist for these
      rather than being relaxed, so a typo'd slug still fails.
    - **Three leaves simulated and REJECTED**: `Beautyhelfer` (a CONTAINER — refill bottles AND
      a makeup tool that already resolved correctly; mapping it DEMOTED a right answer),
      `Selbstbräuner` (spans face and body), and `Lipbalm` (would move 8 already-correct rows
      body→face for no blob reduction and disagree with the `lippenbalsam` rule; the face/body
      split on lip care is pre-existing and needs its own diff).
- **Local API port is 8001**, not 8000 (8000 is usually already taken on the dev
  machine). `mobile/.env` → `EXPO_PUBLIC_API_URL=http://localhost:8001`. The iOS
  simulator reaches the Mac via `localhost`; a physical phone needs the LAN IP.
  **`api.ts` defaults to the Render URL** (not localhost) when `EXPO_PUBLIC_API_URL` is
  unset, so device/OTA builds reach production out of the box — `.env` overrides it for
  local dev. This default is load-bearing because **`eas update` does NOT read eas.json's
  build-profile `env`** (Expo SDK 55+), so OTA bundles have no injected URL and fall back
  to it; eas.json's `env` only applies to `eas build`. A "Couldn't reach the API at
  localhost:8000" on a device = a build/OTA made before this default (rebuild fixes it).
- **The default PLZ is env-driven — never hardcode a personal postal code.** The committed
  default is a neutral central-Berlin **`10115`** (`backend/app/core/config.py` `default_plz`;
  `DealsScreen.tsx` `DEFAULT_PLZ`). The real local PLZ lives only in **gitignored** `.env`
  files: backend `backend/.env` (`DEFAULT_PLZ=…`, read by pydantic-settings) and mobile
  `mobile/.env` (`EXPO_PUBLIC_DEFAULT_PLZ=…`, inlined by Expo). Prod overrides off-repo too:
  Render dashboard env (`render.yaml` has `DEFAULT_PLZ` as `sync: false`, not committed) and the
  weekly scrape's optional **`SCRAPE_PLZ`** GitHub Actions **secret** (`scrape.yml`, else
  `10115`). It's a *secret*, not a variable, on purpose: this is a public repo and the scrape
  job's logs are world-readable, so a variable would leak the PLZ — secrets are masked (`***`).
  The repo was history-rewritten on 2026-06-30 to purge a personal PLZ — do NOT reintroduce one
  in any committed file (code, docs, tests, CI, compose, blueprint).
- **ALDI is TWO companies, and the feed will not tell you which one is yours**
  (`bonial.py` `AldiNordScraper`/`AldiSuedScraper`, routed in `run.py` via
  `store_locator.aldi_division`). ALDI Nord (publisher **`DE-75`**, page `/aldinord-de`) and
  ALDI SÜD (**`DE-77`**, `/aldisued-de`) are independent companies with **disjoint**
  territories (the "Aldi-Äquator"; Berlin is Nord). **Both publisher pages are NATIONAL**:
  measured, each serves the *identical* brochure to Berlin and Munich and ignores the
  `location` cookie — unlike REWE/EDEKA, which correctly return different brochures per city.
  So nothing upstream stops us showing a Berlin user ALDI SÜD deals from ~300 km away. We pick
  the division from **OSM** (`aldi_division` → nearest branch whose brand/name/operator carries
  "Nord"/"Süd"; Berlin→nord, Munich/Frankfurt→sued, verified live) and scrape only that one.
  **If the division can't be determined, ALDI is skipped + logged — never guessed** (fail
  closed: a missing chain is visible, wrong-region deals are not). A resolved division is
  cached 24h; a **failure is never cached**, so one Overpass blip can't drop ALDI all day.
  Both scrapers deliberately share **`chain = "aldi"`** (the two never coexist, so there's
  nothing to compare — unlike EDEKA vs E center); the division shows in the *store name*
  ("ALDI Nord 10115"). Don't re-probe the publisher IDs. ~244 offers/Berlin PLZ, of which
  **~37% are household** (Aktionsartikel: leggings, tools) — correct, and hidden by the
  existing "+ Non-food" toggle. Its `Marken > Marken Aldi Süd` path nodes inside a *Nord*
  brochure are a meinprospekt taxonomy quirk, **not** a routing leak (`_collect_brochures`
  filters on `publisher.id`).
- **Two sources × six grocery chains, tagged `Offer.source` / `Store.chain`**: `coupon`
  (Lidl Plus app endpoints, `app/scrapers/lidl.py`) and `flyer`
  (meinprospekt weekly Prospekt, `app/scrapers/bonial.py`). `bonial.py` is a
  publisher-parameterized engine (`MeinprospektScraper`): `BonialScraper` =
  **Lidl** (publisher `DE-1013`, page `/lidl`), `ReweScraper` = **REWE**
  (publisher `DE-1062`, page `/rewe-de`), `EdekaScraper` = **EDEKA** (publisher
  `DE-220164`, page `/edeka`), `EdekaCenterScraper` = **E center** (EDEKA's
  hypermarket format — its OWN publisher `DE-3443181`, page `/edekacenter-de`;
  deliberately a separate `chain="edeka_center"` so it can be compared against
  regular EDEKA — but see the **E-center duplicate filter** below: the two flyers overlap
  heavily, so the deals *list* hides the E center copies that merely repeat EDEKA).
  The flyer feed is location-gated and reuses the lat/lng the
  Lidl Plus lookup resolves; REWE/EDEKA/E center are **separate stores** reusing
  those PLZ coords (a Berlin PLZ → one brochure region). **Strike prices come from
  THREE payload shapes** (`bonial.py` `_parse_offer`): `REGULAR_PRICE` deals, then
  **`RECOMMENDED_RETAIL_PRICE`/UVP deals** (branded/non-food items print ONLY this —
  ~21% of offers; guarded `rrp > sales`; the 2026-07-14 payload audit found EDEKA/
  E-center carry UVP on ~half their items, so the old "EDEKA has no regular price"
  note was wrong), then a `discountLabel` fallback. **REWE remains the outlier** —
  its "Dein Markt" flyer carries none of the three on most items, so most REWE
  offers still have no `discount_pct` (they sink under discount-sort but the
  optimizer ranks by absolute price). ALDI is the same story (~72% carry no strike price).
  **`PennyScraper` = Penny** (publisher **`DE-1050`**, page `/penny-de`) is the sixth grocery
  chain, added 2026-08-11. **Regional like REWE/EDEKA** (Berlin `2501215484` vs Munich
  `2501215489`, measured), so the location-cookie pinning is what makes it correct — no
  ALDI-style division. Parses with **zero parser changes**: 258 offers / 255 deduped, 100%
  image, 99.2% path, 98.4% caption, 43.8% strike price, **73.6% €/kg-sortable**, and 53%
  day-limited (Penny runs a lot of day specials).
  **Six chains serve 1712 for a Berlin PLZ, under the `/api/offers` cap of 2000.** The old note
  here predicted a sixth chain would cross it and prescribed server-side search — **both halves
  were wrong** and the correction is worth keeping. Penny fits; Netto (461 raw, `DE-1034`) and
  Kaufland (723 raw, `DE-424316869`) do not, and were probed and deferred for exactly that.
  And **server-side `q` would not fix truncation**: search is one of ~12 passes over the loaded
  array — chip counts, `presentChains`, `facetCounts`, Basket matching, Compare and Recipes all
  read the same list — so a truncated BROWSE list makes all of them quietly wrong. Raising the
  cap is the real fix when a 7th chain comes; see `docs/DECISIONS.md`. Truncation is why the cap
  matters at all: `/api/offers` slices **after** a discount sort with nulls last, so the dropped
  rows are disproportionately the chains that publish no strike price.
  **Two Nettos publish** (`DE-1034` Marken-Discount and `DE-1122` "mit dem Scottie") and
  `store_locator` prefix-matches both into one `netto` slug — a second problem to solve before
  that chain can land. Don't re-probe these publisher IDs.
- **Offers are de-duplicated at serve time** (`app/dedup.py`, used by both
  `/api/offers` and `/api/categories` so list and chip counts agree). A chain
  publishes several weekly brochures, so the flyer feed repeats a product across
  them (distinct content ids → distinct `external_id`s in the DB), and a product
  can be in both a coupon and the flyer. `dedup_offers` collapses by
  `(store, normalized-name, price_cents)` — name norm drops apostrophes
  ("Butcher's"/"Butcher’s"), strips German quotes + a produce quality-grade
  ("…Avocado »Hass«, Kl. I" vs "…Avocado Hass"), and maps remaining punctuation to
  spaces, so cross-brochure spelling variants match — keeping the **richest** copy (has
  `price_per_unit`, then a discount, then flyer). Cut a Berlin PLZ ~1322→~738 live
  offers. The DB still stores the dups (serve-time only); a scrape-time
  reconcile/purge would also shrink the table but risks wiping real data on a
  sample-fallback, so it's deferred.
- **Nearby-stores directory is separate from deal scraping** (`app/services/
  store_locator.py`, `GET /api/nearby-stores`): finds the nearest branch of each
  allowlisted chain (lidl/rewe/edeka/aldi/netto/penny/kaufland) via **OpenStreetMap
  Overpass** — `node/way["shop"="supermarket"]` + haversine, brand-prefix
  normalization (Aldi Nord→aldi, Netto Marken-Discount→netto — the *directory* collapses both
  ALDIs into one chain; `aldi_division` reads the same tags to route the **scrape**).
  `active` = chain in
  `ACTIVE_CHAINS` (lidl/rewe/edeka/edeka_center/aldi/penny + rossmann/dm — the ones we scrape;
  netto and kaufland are in the directory but still read "Deals coming soon"). Public Overpass instances 504 a lot → tries
  mirrors in order + caches per-area (24h) + returns `[]` on total failure. **The endpoint
  is globally rate-limited** (`app/throttle.py` `RateLimiter` token bucket → `_NEARBY_LIMITER`
  in `api/offers.py`, ~30/min, burst 30): it fans out to Overpass/Nominatim on a cache miss, so
  leaving it unthrottled let a stranger iterate coordinates and make *our* server hammer Overpass
  → our IP rate-limited. Over budget it returns `[]` (same graceful contract as mirrors-down);
  a single real user (~1 call opening Stores / tapping Change) never hits it. `/api/scrape` keeps
  its own separate cooldown throttle. These
  are **not** persisted as `Store` rows; the app's "My stores" saved list lives
  client-side (`mobile/src/storage.ts`, key `myStores`, **one entry per chain** —
  the branch the user picked). `GET /api/nearby-stores?chain=<slug>` returns **every
  branch of one chain** near the PLZ (nearest first, wider 6 km radius, deduped
  node/way) — the app's "Change" picker (`StoresModal`); without `chain` it's the
  nearest-per-chain list as before. **The picker (`chain` set) centres on the PLZ's
  real centroid via Nominatim** (`plz_centroid`, cached), NOT the scraped-store
  coords: the scraped Store reuses the nearest *Lidl*, which can sit a district away
  (a Wilmersdorf PLZ → a Schöneberg Lidl ~3 km off), which buried the user's actual
  local Edeka past the 12-cap. The **general list keeps the scraped-store coords** so
  its Lidl/REWE stay consistent with the deals (deliberate split). Pure logic
  (`_select_nearest`, `_all_branches`, `plz_centroid` parsing) is fixture/fake-client
  tested — no live API in tests.
- **Outbound calls are counted, paced, and backed off** (`app/metrics.py` + `app/http.py`):
  every scraper/locator builds its httpx client via `tracked_client()`, which (1) tallies each
  call by host via a request hook, (2) **paces** every send by a global min-gap + jitter
  (`settings.scrape_request_gap_s` 0.7 + `scrape_request_jitter_s` 0.6) via a custom transport, so
  a scrape's ~15 requests don't hit the flyer aggregators as one datacenter-IP burst (the exact
  shape they soft-throttle), and (3) **retries** a 429/502/503/504 up to `scrape_max_retries` (2),
  honoring `Retry-After` (secs or HTTP-date) capped at `scrape_retry_cap_s` (30s so the weekly job
  can't hang), with exponential backoff otherwise — **403 is never retried** (a hard block; retrying
  worsens it). When retries are exhausted (or on a 403) it calls `metrics.record_throttle(host,
  status)` and hands back the last response, so the scrapers' existing fail-soft-to-samples still
  fires but the throttle is now **logged + metered** instead of vanishing (a 429 was previously
  indistinguishable from "served samples"). Pacing is a **module-global** lock (shared across the
  per-chain clients; process-local, matches the single free-tier worker); **tests set the gap+jitter
  to 0** (`tests/conftest.py`) so the suite never sleeps (retry logic is still tested via
  `test_http.py`, which monkeypatches `time.sleep`). `GET /api/scrape-stats` (JSON) shows totals
  (since startup), `throttled_total` + `throttles` (by host), and `recent` — the latest ~20
  individual calls (newest first, each with a UTC timestamp + friendly source), so a standalone
  Overpass call (opening Stores) shows up too, not just scrape runs; `GET /stats` is an HTML
  dashboard (`app/stats_page.py`, served from `main.py`) with relative "Xs ago" times and an
  on-demand **Refresh** button. Counts are in-memory (reset on restart). **Reference numbers**
  (measured 2026-07-15): browsing = 0 external calls; one scrape run = **~15** (2 Lidl Plus + ~12
  meinprospekt: **5** publisher pages — Lidl/REWE/EDEKA/E center/ALDI — + ~7 brochure-pages, varies
  with active-brochure count — plus **1 Overpass** for ALDI's Nord/SÜD division, cached 24h), now
  **spread over ~15–30s** by the pacing (same call count, measured 30s for 1646 offers); opening
  Stores = 1 Overpass call; tapping **Change** = 1 Nominatim (PLZ centroid) + 1 Overpass, all cached
  24h. New external client code should use `tracked_client` so it's counted **and** paced/backed off.
- **Categorization is path-aware** (`app/categories.py`): for flyer offers,
  Bonial's `categoryPaths` is the primary signal (non-food level-1 node →
  household; product node → category); coupons + brand-only flyer food fall back
  to the keyword/brand layer. `category_path` is stored, so the recategorize
  backfill (`python -m app.scripts.recategorize` / `POST /api/recategorize`)
  reproduces results without re-scraping. Watch for substring traps (e.g. "li**mett**e")
  and flavour words ("Mango"/"Pfirsich") stealing categories — guard them.
  **Don't hand-trace the layers — ask `explain()`** (2026-07-28). `categories.explain(name,
  brand, path, unit)` returns the category PLUS a per-layer verdict: which rule decided (with
  the matched token and its `table` + `index`, since repeated slugs mean a slug names no
  rule), which layers were **skipped and why** (`no_category_path` for 1/3, `no_unit` for 2b),
  and — the useful part — what the **losing** layers would have said. "Heinz Tomatenketchup"
  reports L5 winning `pantry` via `_OVERRIDES[5]` "ketchup" while L6 would have said
  `vegetables` via "tomate": that's how you tell a wrong rule from one correctly holding the
  line. Surfaced as **`GET /api/offers/{id}/category-trace`** (adds `stored_category` vs
  `computed_category` + a **`stale`** flag — categories are persisted at scrape time, so a row
  can predate a rules change) and **`GET /api/offers/category-traces?plz=`** (bulk, mirrors
  `/api/offers`' dedup+validity so ids line up; trimmed to ~1.3 MB by dropping nulls, `name`,
  `where`-on-misses and all `inputs` but the path — the per-offer one keeps the full shape).
  In the app it's the **"Why this category?"** button in the deal detail, prefetched into its
  own `traceCache` beside `payloadCache`. This also **closes the old `category_path` gotcha**:
  `OfferOut` still doesn't expose it, but the trace does — so "this offer has no path" is no
  longer a guess. **`classify()` and `explain()` share one table walk** (`_layers()` generator
  + `_winner()`); `classify` stays lazy and short-circuits, `explain` pulls every layer. Never
  rewrite `classify` as `explain(...).category` — measured ~3x on a path that runs once per
  scraped offer, and a test counts the table scans to stop exactly that.
  **`_PATH_MAP` was expanded from a live taxonomy survey** (beverage spirit/…marken
  nodes, bread types, produce, sausage subtypes, würzmittel/salatdressing, …) + more
  single-category brands → **"Other" ~11% → ~1%** (12/1056 live). The leaf is *often a
  brand* (Lidl/EDEKA dump into a `Marken > Marken Lebensmittel > {brand}` subtree), so
  the path only helps when an *intermediate* node is a real category; brand-leaf paths
  stay on the brand/keyword layers (multi-category house brands like Gut&Günstig /
  Deluxe / Dr.Oetker / Milbona / **MILSANI / Trader Joe's / Meine Metzgerei** are deliberately
  left there). **ALDI leans on those layers hardest**: its paths dead-end at *generic* nodes
  (`… > Marken > Marken Lebensmittel`, `… > Produkte > Lebensmittel`) carrying no category —
  not a *mis-file*, so it needed brand/keyword entries, **not** `_FORM_OVERRIDES` guards
  (9.4% → **0.8%** "other"; it also rescued 25 stored offers on the OTHER chains — Philadelphia
  ×11, Storck, and Nürnberger Rostbrat**würste**, which the bare `wurst` keyword missed on the
  umlaut plural → now `würst`). Space-guarded keys are load-bearing: `"tuc "`/`"joie "` (brands
  are matched as **substrings**, so a 3–4 letter key fires mid-word — cf. `"lorenz "`/`"wasa "`)
  and `"suppe "` (pantry is second-to-last, so a bare `suppe` would swallow Suppengrün). To re-survey, fetch a
  publisher's brochure pages and tally `products[].categoryPaths`.
  **The flyer CAPTION is a classification signal — `classify(name, brand, path, unit)`**
  (2026-07-17, `_CAPTION_SIGNALS`, layer **2b**): the product NAME is a marketing string that lies
  — a flavour word in it steals the product ("Bauer Diplomat Paprika" is a **cheese**, "Müller &
  Müller Truthahnbrust mit Paprika**rand**" is **poultry**, "GUT&GÜNSTIG Apfeldreieck" is a
  **pastry**) — while `Offer.unit` holds the source's caption, which states the product's own
  designation ("55% Fett i. Tr.", "der leckere Geflügel-Aufschnitt", "Blätterteig mit einer
  Füllung aus Apfelstückchen"). It was stored all along and unread. Runs **after** the name
  form-words (proven/specific) but **BEFORE the path**, because the path is frequently mis-filed (a
  cheese under `Gemüse > Kohl`, a pastry under `Obst > Weintrauben > Rosinen`). Signals must be
  **designations, not ingredients**, and each was diffed over all stored offers before being kept —
  **deliberately rejected and pinned as tests**: bare `frischkäse` (moves a Coppenrath *cheesecake*),
  bare `schmelzkäse` (a snack box that merely *contains* some), `plunderteig`, `gebäck`,
  `rindfleisch` (hits mixed Bratwurst, which is legitimately pork). `unit` is optional, so old
  callers are unaffected; `run.py` passes `raw.unit`, `recategorize` passes `offer.unit`. Full-DB
  diff: **107 offers moved, 0 regressions**; live `other` 7.4%→6.5%. **Poultry sausage was the
  biggest cluster** (~20): the source files it under `Wurstwaren > Wurst > Brühwurst` /
  `Fleisch > Fleischzubereitungen` → pork, and a path beats a keyword, so `geflügel`/`hähnchen`/
  `putenbrust`/`truthahn` are now L2 form words (proven: the *same* product is poultry via a brand-leaf
  path and pork via a Wurstwaren path).
  **Substring guards + multi-category brands (2026-07-17, PR2 of the audit, 78 offers moved, 0
  regressions, `other` 6.9%→6.8%)**: German compounds mean a keyword *should* usually fire mid-word
  (`Bratwurst`→pork), so only *coincidental* matches get a space guard, each pinned to the product
  that proved it AND the sibling that must survive: `"milka "` (vs Milkana, a cheese), `"trolli "`
  (vs Trollinger, a wine), `"limo "` (vs Limonaie, an ALDI lemon *biscuit*), `" spezi "` (vs
  Spezialsalz/-mehl/Käsespezialitäten), `" sekt"` (vs In**sekt**enabwehr), `" angus"` — **left
  UNPADDED on purpose** because the real beef hyphenates (`Black-Angus-`) and the plant it clashes
  with (`Lavendel angustifolia`) is already caught by its non-food path, so a guard would cost a row
  and save none. New L2 form words rescue mis-filed *paths*: `dicksaft`/`goldsaft`→pantry (a syrup,
  not a juice — `saft ` only guards the trailing side), `ganze bohnen`/`iced coffee`→soft (coffee a
  multi-category brand was filing as ice cream), `weinschorle`/`oder alkoholfrei`/`auch alkoholfrei`
  →alcoholic (a multi-variant *beer* offer is not an alcohol-free product), `lachsschinken`/
  `fleischkäse`→pork, `croissant`→bakery, `topfpflanze`→household (an artificial plant the source
  files under `Würzmittel`). **Multi-category brands** removed from `BRAND_CATEGORY` (a brand entry
  beats every keyword, so it mis-files every brand-leaf-path product): `rondo` (Bahlsen biscuits AND
  Röstfein coffee → all live rows coffee). **Deliberately KEPT despite spanning categories** (each
  pinned by a test so the "cleanup" can't land silently): `mövenpick` (ice cream AND coffee — its
  coffees are rescued a layer *earlier* by the `ganze bohnen`/`iced coffee` form words, while a bare
  "Edle Komposition" has no other signal and would fall to `other`) and `kerrygold` (butter AND
  cheese — its cheeses are saved by a Käse *path* (L3) or `reibekäse` *caption* (L2b), both before
  the brand map; **not** by "Käse" in the name, which is L6, after the brand). New brand-indexed
  drink-path fix: the source indexes some paths as `Bier > Biermarken > <brand>`, dumping a ham
  (`Radeberger Premium-Lachsschinken`) or fish (`Golden Seafood …`) into alcoholic — 117 offers sit
  under those nodes, the L2 form words rescue the ~6 wrong ones. **REJECTED and pinned**: a bare
  `alkoholfrei` *caption* signal (~30 real beers carry "auch/teilw. alkoholfrei" as a variant note →
  would empty the beer aisle into soft_drinks). Also a **free CI gate**: `verify_deals.py` now flags
  self-disagreeing products (same name, two categories) — see the CI/CD note. **`classify` order
  (7 layers)**: non-food path→household, **`_FORM_OVERRIDES`** (limonade/saft/joghurt/
  chips + the poultry words above — definitive *form* words that beat even a *mis-filed* food path, e.g. the source
  tags "Bananenchips" under Obst; also guards mis-files of `jägermeister`→alcoholic and
  `möhre`→vegetables that the source dumps under `Dessert>Eis`. **The 2026-07-15 cleanup added
  more L2 guards** for items the source buries under a food node so only L2 can beat the path:
  premixed/spirits →alcoholic (`havana club`, `nordhäuser`, `hard seltzer`), pet →household
  (`dental`, `hello my cat`, and **pet food** — see below), and `drumstick`→poultry (breaded chicken dumped in
  `Knabberzeug>Sticks`). Also: `"knusper"` was **removed** from the snacks keywords — it's a
  coating adjective (matched cat food/nuggets/bread, 0 real snacks); specific `knusper*` lines
  are pinned (`knusperdino`→poultry, `knusperjung`→bakery). And `BRAND_CATEGORY` `"lorenz"` →
  `"lorenz "` (trailing space) so it stops swallowing `Lorenzo` (cf. `"wasa "`)), food taxonomy
  node, brand map,
  **`_OVERRIDES`** (flavour words like sekt/choco — after the brand so Häagen-Dazs Chocolate
  stays **ice_cream**, not sweets), keyword rules.
  **The 2026-07-29 IMAGE audit** (contact sheets of all 1086 distinct food-category products,
  built from `Offer.image_url`, 100% coverage) found the class a keyword audit structurally
  cannot: a product whose name, brand, path AND caption all read plausibly for the wrong
  category. 4 PRs (#115–#117 + #118), **~230 rows / ~105 distinct products, 0 regressions**;
  live "other" 4.3% → ~2%. Examples that only a photo settles: `Apfeltasche` (apple-turnover
  PASTRIES) and three `Apfelmus` (JARS) in Fruits, `Milsani Erdbeere` (a rack of SKYR pots) in
  Fruits, `Pick Paprika Kolbasz` (Hungarian SALAMI) in Vegetables, `Berliner Buletten`
  (MEATBALLS) and `Tillman's Toasty` (breaded CHICKEN) in Bakery, `Käsewiener`/`Käsebeißer`
  (cheese-FILLED SAUSAGES) in Cheese, `Metten Roastbeef` (BEEF) in Pork, and EDEKA's
  `Mais-/Dinkel-/Reiswaffeln` (savoury crispbread) in Sweets.
  **A new trap class: the source sometimes attaches a path from an ENTIRELY unrelated domain**
  — a rucksack under `Schaumwein > Sekt` (served as Alcoholic), a Zott Monte under `Hautpflege
  > Creme` and Capri-Sun syrup under `Reinigungsmittel > Spülmittel` (both buried in
  Household). The classifier follows it faithfully. They're findable because the *same*
  product arrives with a correct path from another chain — so the **self-disagreement check is
  a detector, not just a CI gate**. Run `classify(name, brand, None, unit)` vs
  `classify(..., path, ...)` and look at the disagreements.
  **Sharpen that detector by keeping only the CONFIDENT contradictions** (2026-07-31): raw, it
  returns ~1220 groups, almost all of them the path correctly improving on a nameless product
  (a T-shirt `other`→`household`). Drop every pair where either side is `other`/`household` and
  it collapses to **148 groups / 370 rows**, where one of the two answers must be wrong — that
  is the reviewable list.
  **A path node that names a CUT or a FORM instead of a product kind is the same bug as a
  brand-container node.** User-reported: "Schweine-Nackensteaks" served as **Beef**, because
  `_PATH_MAP["steak"] = beef` (L3) beats the `schwein`/`nackensteak` keywords (L6) — but a
  steak is a cut, and pork/turkey/salmon all come as steaks. Same for `Knabberzeug > Sticks`,
  which holds coffee sticks, cheese sticks AND ice sticks. **The fix is the SPECIES (or the
  real kind) at layer 2, not deleting the node**: deleting `steak` drops "Scotland Hills Cowboy
  Steak" onto its parent `Fleischzubereitungen` → pork, trading one wrong answer for another,
  and deleting `sticks` is a measured **no-op** (its parent answers `snacks` identically).
  Both are pinned by tests. Also watch for a leaf that isn't in `_PATH_MAP` at all —
  `Alpenmilch` (Milka chocolate → dairy) and `Lichtenauer` (Zespri kiwi → soft_drinks) inherit
  from a mapped PARENT, so only L2 can reach them; and `puten-` with a hyphen missed the
  source's un-hyphenated `Putenhackfleisch` leaf.
  **Order is part of these rules**: the new `schwein` entry sits AFTER the pet guard, or a
  Meer**schwein**chen food becomes pork. **`bananen` was simulated and REJECTED** (pinned):
  it fixes bananas mis-filed under `Milchprodukte > Milch` but drags a
  "Bananen-Kirsch-Getränk" out of soft_drinks — it needs a negative guard the L2 table can't
  express.
  **Preserved produce leaves the FRESH chips** (user's convention): jarred/canned → pantry,
  frozen → frozen, at layer 2 for *named* products (canned is a definitive *form* and must beat
  the produce path and brand — `Bonduelle` is mapped to vegetables, so a layer-5 override never
  gets a turn), **plus a POST-LAYER caption redirect for the rest** (2026-08-15, `_redirect`).
  Every rule answering `fruits`/`vegetables` matches the NAME or the PATH, and neither can tell
  a jar from loose produce, while the caption states it outright — so the redirect runs after
  the walk, in `_decide`, which `classify` and `explain` BOTH call. That shared call is now the
  thing keeping them in agreement: once an answer can be overridden post-walk, `_layers` +
  `_winner` no longer guarantee it. It cannot be a layer — `_winner` takes the FIRST decided
  layer, so anything after L3/L6 is unreachable and reaching it would exhaust the generator,
  which is exactly the de-lazification a test forbids. **The gate is the winning SLUG, not the
  token, and that is load-bearing**: `-glas` is not right-bounded and really does fire inside
  "Bubble-Gum-Glasur", a stored ice lolly. It outranks every layer, so a future layer-2 guard
  meaning "this jarred thing really IS a vegetable" would be silently overridden. Layer 1's old
  special case is **gone** — verified redundant by blinding `_preserved_caption` and re-running
  over all 17,018 stored rows for an identical result, and its removal *improves* the trace
  (layer 1 now reports the rescue token it actually matched, with the override recorded beside
  it). `ClassifyTrace.redirect` carries it; `layers` stays exactly `LAYER_ORDER`. Full-corpus
  diff: **20 rows / 15 distinct products moved, 0 regressions.**
  **Three signals were simulated and REJECTED, each pinned by a test** — the simulation is the
  point, all three looked obviously right: a bare `brotaufstrich` caption (a USE, not an
  identity — it moved Fleischsalat/Eiersalat out of pork and the Brunch spread out of cheese);
  a bare `tiefgefroren` caption (**84 rows** — it emptied ice_cream, fish and poultry into
  frozen: *the freezer is a shelf, not a category*); and a bare `grilltaler` (Grillmeister's is
  a MEAT patty, only Milram's `hotties` is cheese). **A `_FOOD_RESCUE` substring trap nearly
  shipped**: `weine` is inside `Schweine-`, so an unguarded token made a Schweinebraten under a
  pet path ALCOHOLIC — rescue nouns that are substrings of a common compound need a space guard.
  **Two more structural causes the later sheets exposed.** (1) **A BRAND at layer 4 beating the
  truth**: `mövenpick`→ice_cream sent its whole *coffee* range (`Kaffee`, `Kaffeekapseln`, `Der
  Himmlische`) to Ice Cream, and `baileys`→alcoholic made `Baileys Muffins` a liqueur. The
  documented "its coffees are rescued a layer earlier by `ganze bohnen`/`iced coffee`" only
  covered part of the range — a mitigation that looked complete and wasn't. Multi-category
  brands need their *other* categories pinned at **layer 2**, which is the only layer above the
  brand map. (2) **A brand-container PATH node**: the source files regional Thüringen food under
  `Wasser > Wassermarken > Thüringer Waldquell`, so Senf/Leberwurst/Rostbratwurst/Schinken/
  Mirabellen were served as **soft_drinks**. **Deleting the offending node from `_PATH_MAP` does
  NOT fix that** — the leaf→root scan falls through to the parent (`Wasser`, also mapped). Only
  layer 2 beats a path; removing a node helps only when its parent is unmapped.
  **The 2026-07-31 PHOTO AUDIT re-ran the contact sheets over all 1403 served products** (PRs
  #132–#134, ~102 products, 0 regressions) and found two whole blocks the earlier pass had
  never looked at. **`household` is where food hides** — the app puts it behind the Non-food
  toggle, so an edible product there is invisible: Babybel, a 5 l beer keg, Senseo pads, two
  poultry bratwursts, fresh peppers, hummus. Each needs a `_FOOD_RESCUE` token, because layer 1
  decides on a non-food path and never falls through (so a test for one MUST pass a non-food
  path — a pathless call proves nothing).
  **Pet food now resolves to the `pet` chip, not `household`** — measured, not assumed: `pet`
  IS served in the grocery vertical, so the guard (written before that category existed) was
  disagreeing with itself, some pet products reaching the chip while 16 sat behind the toggle.
  `topfpflanze` and bare `dental` stay household so a houseplant and human dental care aren't
  dragged along.
  **Ready-meals convention (user's call, widened twice): `ready_meals` is anything served as a
  finished single serving** — canned Eintöpfe, deli salads (Eiersalat/Fleischsalat, 2026-08-03),
  and a counter **`fischbrötchen`** (2026-08-03). A *spread* stays `pantry` and a cake **mix** is
  an ingredient. `fischbrötchen` must sit **above** the `matjes` guard in `_FORM_OVERRIDES`, or
  "Fischbrötchen Rauchmatjes" is claimed by it and the same product lands in two chips — the diff
  caught that, reading the table did not.
  **Drinking yoghurt and kefir are `dairy`** (user's call, reversing PR #105's placement of
  MILSANI Activedrink in soft_drinks) — listed with the sibling forms so it's a convention, not
  a one-product patch. A juice or an isotonic drink must still be `soft_drinks`; both pinned.
  **A token rejected at one LAYER can be correct at another** (2026-08-03): `nutella` stays
  rejected as an L2 form word (it claims the ice cream and the biscuit) but ships as a
  `_FOOD_RESCUE` token, because that table only runs inside the layer-1 non-food branch — the
  ice cream and biscuit arrive on FOOD paths, so the gated rule cannot reach them. Record the
  layer a rejection applies to, not just the token.
  **The last four conventions (user's calls, 2026-08-03)**: **breaded cheese is `frozen`**
  (Mozzarella-Sticks / Back-Camembert / Mini-Backkäse — it was split, served as `cheese` at one
  chain and `snacks` at another, so leaving it alone was not a stable answer; plain *baked*
  cheese is not breaded and stays `cheese` — Ofenkäse, Grillkäse, Pfannenkäse). **Industrially
  packaged, individually-portioned cake is `sweets`** — only the FORMATS are named (`muffin`,
  `donut`, `kuchenriegel`, `mini-kuchen`; baklava already resolved there) because *shelf-stable*
  has no signal in the feed: the fresh ones say "Gekühlt" and the packaged ones say nothing, and
  **absence of a word is not evidence**. A bare `kuchen`/`torte` was simulated and REJECTED — it
  drags the savoury Flammkuchen, the chilled Schichttorte/Frischkuchen and the in-store-bakery
  Kuchenglück out of `bakery`. The `donut` token needs a **`pizza-donut` guard above it** (a
  savoury cheese-filled snack whose `Hartkäse` path L2 would otherwise beat). **Every rice cake
  stays in `snacks`, chocolate-coated included** — one product line in one chip; pinned so a
  later audit doesn't "fix" it.
  **A living plant named after its fruit is not produce — and the guard must be a `_RESCUE_VETO`
  token** (2026-08-03). "Heidelbeere im Topfcover", a 50 cm blueberry BUSH, was served in the
  **Fruits** chip: `heidelbeere` is a rescue token, the plant arrives on a garden path, and layer 1
  decides and never falls through — so the `topfcover` → household entry added at layer 2 by an
  earlier audit **could never reach the product it was written for**. Pathless it worked, which is
  exactly why a pathless test would have passed. Same probe found a porcelain **`Kaffeebecher`** in
  the Coffee chip (the deliberately-bare `kaffee` rescue token). A bare `becher` is unusable —
  Becherovka is a liqueur, Knorr Snackbecher is pantry, Jacobs Instant-Becherportionen is real
  coffee — and `im topf` was rejected as too broad for future "X im Topf" meal names.
  **Grocery chains sell drugstore goods, and nothing was routing them** (2026-08-03 photo
  audit, 86 products): ~60 cosmetics/cleaning/pet products sat in the GROCERY vertical's
  `household` chip. `_DRUGSTORE_RULES` gained tokens for fragrance/hair/face/body/health/baby/
  cleaning/laundry/pet, **appended not inserted** — at the front, a new `duschgel` token beat
  the existing `shampoo` rule and sent a "2in1 Shampoo & Duschgel" to body.
  **A broad token is only shippable if its false positives are NAMEABLE**: `bananen` went from
  rejected to shipped because `bananen-kirsch` could be guarded above it, while `nutella` (jar
  vs ice cream vs biscuit) and `yogurette` (chocolate bar vs Stieleis) stay rejected because no
  substring separates their forms. All three are pinned with the reasoning.
  **A brand whose names are what it IMITATES needs layer 0 or 2**: Violife sat in the brand map
  as cheese and a MYVAY "Chicken-Style" tub was poultry — both are vegan-only, so they belong in
  `vegan.py` (layer 0), which also pulled 6 more MyVay products out of household.
  **`bananen` ships now, and a blanket `brotaufstrich` still does not.** The flat table can't say
  "not a drink" / "not margarine", but a GUARD ENTRY ABOVE the token can — that is how `bananen`
  went from rejected to shipped. `brotaufstrich` was re-simulated and still drags Rama out of
  butter and Brunch out of cheese, so the specific products are named instead.
  **A repeated key in a dict literal silently keeps the LAST one** — a second
  `_FOOD_RESCUE["poultry"]` ate the first with no error, and a redefined test function dropped a
  previous audit's cases from the run. A test now parses the module and fails on duplicate keys
  in `_FOOD_RESCUE`/`_PATH_MAP`/`BRAND_CATEGORY`; ruff's F811 covers the test-file half.
  **An ordered table can hide a rule that CANNOT FIRE, and two tests now catch it** (2026-08-04,
  after the class showed up three times in one day — the potted blueberry bush, a porcelain mug,
  and toilet roll). Both live in `test_categories.py`:
  - **`test_no_rule_is_shadowed_by_an_earlier_one_with_a_different_slug`** — these tables match
    `token in text`, so a later token is unreachable when an EARLIER token is a **substring** of
    it. Substring, not equality: `torte` swallowed `tortellini` (a brandless, pathless Tortellini
    served as **bakery**), `shampoo` swallowed `babyshampoo`, `feuchttücher` swallowed
    `feuchttücher baby`, and `protein-pulver` swallowed `high-protein-pulver`. A **same-slug**
    repeat stays legal — that's the guard-restated-in-its-semantic-block idiom used throughout.
  - **`test_the_two_drugstore_tables_do_not_drift_further`** — a RATCHET. A drugstore product
    reaches layer 1 only by arriving on a non-food path, and layer 1 never falls through, so a
    drugstore token that lives only in `_FORM_OVERRIDES` is unreachable **by construction** (it
    still fires for a pathless copy, which is why the drift is silent). 31 of 40 were in that
    state; the allowlist names them, a 32nd fails, and a **stale** entry fails too. Mirroring one
    into `_DRUGSTORE_RULES` needs the usual full-corpus simulation — `vogelfutter` would turn a
    "Vogelfutterhaus" (a bird feeder) into pet food.
  **`other` is NOT hidden by the app's Non-food toggle — only `household` is** (2026-08-08, the
  finding behind that week's audit). `dealFilters.ts` filters exactly one slug
  (`o.category !== 'household'`), so any non-food product that lands in the `other` FALLBACK
  renders in the middle of the grocery list. Of the 25 served `other` offers that week, **8 were
  non-food** — two Pokémon toys, a deck chair, two children's books, a craft set, a set of plastic
  boxes and a **mobile-phone plan**. So the `other` chip is worth auditing even when its *rate* is
  healthy (it was 1.7%, unchanged from the previous audit): the number says nothing about whether
  the contents belong. Audit it by contents, not by rate. **Non-food fixes go in the LAST `_RULES`
  tuple (`household`)**, where a token can only ever catch a product that would otherwise fall
  through to `other` — zero-regression by construction, the same argument as the drugstore step
  inside layer 1. 25 → **2** served, 0 regressions over 8,310 stored products.
  - **A food-root path can hide a non-food product from layer 1 entirely**: the source files Lidl's
    SIM under `Lebensmittel und Getränke > … > LIDL Connect Classic`, so the non-food branch never
    sees it and only a name rule can reach it. A pathless test would pass without proving that.
  - **The caption can be the ONLY handle**, because the source truncates titles: "EDEKA
    Genussmomente" is the entire stored name — the flyer's "Teigwaren" line is dropped — and
    `versch. Ausformungen` (pasta SHAPES) resolves it. 21 of the 22 stored offers carrying that
    word were already pantry, which is about as strong as caption evidence gets.
  - **Rejected, each pinned with its counter-example**: `kohl` (fires inside Holz**kohl**e, and
    household runs LAST so charcoal would land in produce); `kräuter` (54 rows across **13**
    categories — Kräuter*likör*, Bresso, Kräuterbaguette); a `saucen` CAPTION (matches "Chicken
    Nuggets **mit Pommes und Saucen**" — the sauce is an accompaniment, the standing
    designation-not-ingredient rule); `pizzateig` (spans four categories, rejected before too).
  - **Two mechanism claims I wrote were wrong and the sabotage harness caught both** — worth
    knowing because each *reads* as obviously right: the Alesto pecans are protected from a
    `pekannuss` rule by the **brand map at layer 4**, not by bakery-before-snacks ordering (an
    UNBRANDED pack has nothing above layer 6 and is the real discriminator); and the Florette goat
    cheese is held by **two** independent cheese captions, so no single-token sabotage can prove
    that test bites — it takes dropping the caption block.
  - **Deliberately left in `other`, both real judgement calls**: "CHEF SELECT Mini Schnitte"
    (photo: breaded chicken — but the source truncated "…/Schnitzel Hähnchen" out of the name, so
    the only evidence is one flyer image, and `schnitte` spans 8 categories incl. Milch*schnitte*);
    and "Süßes Frühstück", an in-store café breakfast set whose siblings are split household/other
    in the stored data, so there is no stable answer to copy.
  **The 2026-08-09 week refilled `other` to 63 (4.3%) and one pass emptied it to ~1** (86 distinct
  products moved over a 9,582-product corpus, **0 regressions**). Nearly every row sat on a
  brand-leaf path, so only name/caption rules could reach them. Three durable lessons:
  - **A "rescue" out of `other` is NOT automatically a right answer, and the simulation scores it
    as a free win.** A candidate `président` → cheese read CLEAN against the corpus — no product
    left a real category — because the product it was about to break, **"Corsaire Réserve du
    Président" (`Frankreich trocken 0,75-l-Fl.`, a WINE)**, was already sitting in `other`. It
    only surfaced from reading the list of what actually MOVED. Shipped as `président carré`.
    So: read the moves, don't just count the conflicts.
  - **Check which layer really holds a product before writing the reason down.** The comment for
    `oreo` → sweets first claimed the Oreo *Stieleis* was protected by `ice_cream` being an
    earlier `_RULES` tuple. `explain()` says layer **2** decides (`stieleis` in
    `_FORM_OVERRIDES`), so those tuples never get a turn. `stieleis` also appears **five** times,
    so — like the Florette cheese — no single-token sabotage can prove that test bites.
  - **Distinguish a load-bearing rejection from a precautionary one.** `carré`, `président` and
    `lyttos` genuinely collide (their products carry no usable path). `paula`, `cashew` and
    `beren` are each held by a real layer-3 path today, so the narrower tokens that shipped buy
    independence from that path rather than fixing a live collision — say which is which.
  **The 2026-08-09 PHOTO SWEEP over all 1,843 served products** (4 reviewers, 109 contact
  sheets) found ~150 candidates; the shipped subset moved **146 distinct products, 0 unintended
  regressions**. Three structural results worth more than the rows:
  - **`household` is still where food hides, and it is decided at LAYER 1.** 26 edible products
    were sitting there — raw pork chops, chicken legs, prawns, plums, grapefruit, coffee pads,
    an iced tea — because the source hangs them off absurd non-food nodes (chicken legs under
    `Elektronik und Technik > Marken > Samsung`, prawns and plums under `Tierbedarf > Marken für
    Tiere`). Layer 1 never falls through, so **only `_FOOD_RESCUE` can reach them** and a
    pathless test proves nothing. Same for pet food on a `Tierbedarf` path: it needs
    `_DRUGSTORE_RULES`, not the layer-2 pet guard, which never gets a turn.
  - **The counter sandwich was ONE CLASS scattered over five categories** — a filled roll sold
    by the Stück read `fish` / `pork` / `poultry` / `cheese` depending on which filling word
    won. One `ready_meals` entry fixes the class, extending the existing `fischbrötchen` call.
    It must sit in the TOP guard block: appended at the end of `_FORM_OVERRIDES` it was dead
    code for every product it was written for.
  - **Two rules I appended were dead on arrival and the RATCHETS caught both**: `joghurt
    dressing` (shadowed by `joghurt` above it) and a layer-2 `pet` token that needed mirroring
    into `_DRUGSTORE_RULES`. Write guards ABOVE the token they protect, and re-read the two
    ratchet tests before appending anything.
  **What a photo CANNOT settle, and must not be guessed**: Carlsberg 0.0 and Peroni 0.0 show
  "0.0" only on the image — the stored name is "Carlsberg BEER", and both brands also sell real
  beer, so there is no text signal and they stay as they are. `clausthaler` shipped because that
  brand makes nothing else. Deferred with findings recorded but not yet shipped: Sol & Mar's
  Spanish range (cured meats/paella/croquettes scattered across pantry and bakery), five
  in-store bakery breads sitting in `pantry`, preserved produce in the fresh chips, and ~29
  drugstore-aisle products still in `household`.
  **Drugstore `household` at 63% was CORRECT, not a mapping gap** (same week; corrects a note in
  this file that guessed "dm's leaves rotated"). Broken down by source leaf, **102 of 131** rows
  were children's clothing (`Kinderpullover & -shirts` 45, `Kinderhosen` 32, …) — dm was running a
  clothing clear-out, and household is the right answer for a T-shirt. Only 4 rows were real
  misses, all from `_DRUGSTORE_PATH_MAP` being an **exact per-node lookup**: dm sends ONE flat
  leaf, so `Gesichtspflege für Männer` shares no key with the `gesichtspflege` entry sitting right
  above it and has no parent to fall back to. A test now pins the clothing as correct, so a future
  audit doesn't chase the percentage.
  **A drugstore product with NO path could not reach its aisle at all, and the ratchet was
  guarding the smaller half of the drift** (2026-08-09). `_DRUGSTORE_RULES` runs INSIDE layer 1,
  which only a **non-food path** reaches, so **226 of its 237 tokens were dead for a pathless
  product** — a pathless "Formil Feinwaschmittel" matched `waschmittel` in the `_RULES`
  household tuple and stopped there. `test_the_two_drugstore_tables_do_not_drift_further` only
  ever checked the opposite direction (31 layer-2 tokens dead for a *pathed* product).
  - **The fix is data, not a new layer.** `_RULES` is already ordered first-hit-wins with
    `household` LAST, so `_RULES[-1:-1] = …` splices the aisles in immediately before it: every
    food tuple has had its turn, and an aisle token can only catch what was going to be
    `household`/`other` anyway — zero-regression by construction. Splicing (not copying) keeps
    ONE source of truth so the two placements cannot drift.
  - **Live impact is small and that is worth knowing before repeating the work**: 5 products
    moved (Formil, two Pampers, a dishwasher salt, a body mist). Nearly every drugstore product
    really does arrive with a non-food path. The value is that the 226 tokens stop lying.
  - **German compounds hide a toiletry inside a food word**, so the aisles need GUARDS above the
    food tuples: `mundwasser`/`gesichtswasser`/`mizellenwasser` (vs `wasser`), `zahnpasta` (vs
    `pasta`), `körpermilch`/`sonnenmilch`/`muttermilch`/`scheuermilch` (vs `milch`),
    `hustenbonbon` (vs `bonbon`), `wasserenthärter` (vs `wasser`). Every one is already correct
    today via its path — which is exactly why the guard is needed now, since the failure is
    invisible until a chain ships one without a path.
  - **Nine tokens were DELETED from the household tuple** (`shampoo`, `duschgel`, `zahnbürste`,
    `rasierer`, `windel`, `weichspüler`, `spülmittel`, `spülmaschinen`, `waschmittel`): they
    predate the drugstore aisles, which now own them, so the copies were dead code.
  - **Still open**: `BRAND_CATEGORY["nivea"] = "household"` decides at layer 4 and outranks these
    guards, so a pathless "Nivea Sun Sonnenmilch" is still household. Nivea spans body/face/sun,
    so re-pointing it needs its own corpus diff.
  **The 2026-08-11 pass shipped the queue the 08-09 sweep had adjudicated but held back**
  (100 offers moved, 0 unintended). Two structural notes:
  - **~50 drugstore products were sitting in `household` needing TOKENS, not reachability.**
    They carry a `Drogerie und Haushalt` path, so they already reached layer 1 — the opposite
    half of what PR #155 fixed. Any test for them MUST pass a non-food path; a pathless call
    proves nothing about `_DRUGSTORE_RULES`. **Brands that span aisles stay out** (garnier →
    hair/face/body, isana → face/body/health, cien → makeup/tools, lacura → body/makeup); the
    product-type word is used instead. Single-aisle brands are safe (Colgate, Elvital, Pantene,
    Taft, Tetesept).
  - **Feminine hygiene resolves to `body`, and that was the corpus's ANSWER, not a new call**:
    all 9 stored Slipeinlagen rows already said body while the Camelia/Carefree strays sat in
    household. Same for Weleda Skin Food (body on one row, household on another). When a
    convention is already implied by the majority of stored rows, align to it rather than
    inventing a third answer — and say in the test that it is an alignment.
  - **Two substring traps**: no bare `insektenschutz` (LIVARNO's Dachfenster-/Alu-Insektenschutz
    are window and door SCREENS), and `raid essentials` in full because a bare `raid ` sits
    inside "Hyd**raid ** Hydration Helper", a drink. On the food side, no bare `kruste` —
    Krustenbraten/Krustensteaks/Krustenschinken are all pork.
  - **Both ratchets fired and both were right**: the shadowing test caught `wasser` (soft_drinks)
    swallowing `reinigungswasser` and `essig` (pantry) swallowing `essigreiniger` — the
    documented German-compound class, invisible until a chain ships one without a path — and the
    drift ratchet demanded its allowlist be re-derived (31 → **27** tokens).
  - **The preserved-produce redirect SHIPPED 2026-08-15** — see the `_redirect` note above.
    Still deferred: the mixed "Tapas Selektion"/"Tapasplatte", which the sweep read as cured
    meats but whose names do not say so — pinned as a decision rather than left as an oversight.
  **Don't hardcode absolute `_FORM_OVERRIDES` indices in tests** — inserting a guard shifts them
  all; derive the index instead (two trace tests were fixed this way).
  **`_FORM_OVERRIDES` is first-hit-wins, so ORDER is part of the fix.** Two guards had to be
  appended *before* the tokens they protect: `edelbrand`/`obstgeist` before `mirabelle` (a
  Mirabellen Edelbrand is a fruit BRANDY) and `matjes` before `senf` (a "Matjes Honig-Senf" is
  herring). Both were caught by the full-DB diff, neither by reading the code.
  **Seven signals were simulated and REJECTED across the audit** — all seven read as obviously
  correct while being typed, and six were only caught by the diff: the three above plus
  `% vol` (a substring of `20% Vollmilch` — it made a chocolate brioche alcoholic) and a
  `fast food` `_PATH_MAP` node (dragged 15 pizzas/burgers/nuggets out of frozen and beef).
  **Simulate every candidate signal over the full DB before adding it; the editor cannot see
  these.** Rebuild the contact sheets from `Offer.image_url` (Pillow + a paced httpx fetch,
  ~16 min for ~1100 images) to re-run the audit on a new flyer week.
  **Pet food never lands in a food chip (2026-07-28, user-reported: "Orlando in Chicken is dog
  food")**: the pet veto (`_RESCUE_VETO`) only ran INSIDE the non-food-path rescue, so a **pathless**
  pet product with a meat word — "Orlando Hundetrockennahrung **Rind**" → beef; "ROMEO Kauknochen aus
  Kaffeeholz" → coffee; "Coshida Knabbersnacks" → snacks — sailed to the keyword layer. A **layer-2
  `_FORM_OVERRIDES` household** guard now catches pet food before the meat/coffee/snacks keywords AND
  before a mis-filed food PATH ("Sheba Katzennassfutter Filets" sits under a `Fisch` node → was fish,
  L2 beats L3). Tokens are the animal-only `-nahrung`/`-futter` stems (`trockennahrung`,
  `nassfutter`, …; baby food is *Anfangs-/Säuglings-/Trink*-nahrung, no match), the chew words
  (`kausnack`/`kaurollen`/`kauknochen`/`kaustange`), `katzenstreu`, and the single-category pet
  **brands** `coshida`/`sheba` — NOT `orlando` (which also sells human Mexican food; its pet lines
  are caught by the tokens). 15 offers moved, all → household, 0 regressions.
  **The same 2026-07-28 audit cleaned five more clusters out of Other/Household** (PRs #103–106, each
  a 0-regression full-DB diff; live "other" 6.9% → **4.4%**): cheese (Rücker/Grünländer→BRAND;
  `maasdamer`/`badejunge`/`tolle rolle`/`harzer` keywords; `reibekäse` rescue); sausage/cured meat
  (`tyrolini`/`sucuk`/`salametti`/`pancetta`/`spanferkel`/`die thüringer`→pork, `teres major`→beef —
  **Block House stayed OFF the brand map**, it also sells garlic bread, the full-suite catch); drinks
  (`bellacrema`→coffee; `rotbäckchen`/`gemüsesaft`/`iso light`/`activedrink`→soft); the Bier-path fish
  rescue gained `lachsfilet`/`backfisch`/`thunfischfilet`, plus `kaugummi`→sweets and `fassbutter`→
  butter; and the long tail (`oatly`/`simply v`/`like döner`→vegan; `bagel`/`simit`/`zwieback`/
  `croutons`→bakery; `pfifferling`/`portobello`→vegetables; `chokis`/`hitschies`/`nippon`→sweets;
  `little moons`/`mochi`→ice_cream; `_FOOD_RESCUE` snacks/pantry += `cashew`/`walnusskern`/
  `reiswaffel`/`quinoa`/`agavendicksaft`). Left in Other on purpose (couldn't reach 0 regressions):
  `mars`/`paula` (Paulaner clash), bare `mandel`, `zetti` (Mazzetti), a blanket Trader-Joe's brand map.
  **Non-food evicted from the produce chips (2026-07-29, L2 `_FORM_OVERRIDES`, 13 rows / 7 products,
  0 regressions)**: the source files **scented bin bags under `Obst > Melone`** (the bags are
  watermelon-scented — it filed the SCENT, not the product), a herb cream cheese under `Gemüse >
  Kohl > Kraut`, and two breads under Obst/Gemüse. `müllbeutel`/`frischhaltebeutel`/`gefrierbeutel`
  →household, `flatbread`/`couronne`→bakery, `remoulade`→pantry, `bresso`→cheese; two bonus rescues
  out of `other` fell out (Schär Flatbreads, POWER FORCE Frischhaltebeutel). This is worth more than
  tidiness now that produce is fully sub-grouped: a sub-group feeds the **Basket's** suggestions, so
  a bin bag left in Fruits becomes a recommendable "fruit".
  **`ice_cream` is split out of `frozen`**
  (the source's `Eis`/`Speiseeis` path nodes + a keyword rule before frozen/sweets with the
  space-padded standalone word `" eis "` — safe vs Fleisch/Reis/Eisberg/Eistee/Eiweiß — plus
  ice-cream brands); `frozen` keeps savoury (pizza/Pommes/fish). ~40 ice_cream vs ~28 frozen/PLZ.
  **`beverages` was split (2026-07-05) into `soft_drinks` (all non-alcoholic — soda/juice/water/
  tea) + `alcoholic` (beer/wine/sekt/spirits)** across all 5 maps (`_PATH_MAP`, `_RULES`,
  `BRAND_CATEGORY`, `_FORM_OVERRIDES`, `_OVERRIDES`); `alkoholfrei` is a `_FORM_OVERRIDES`→soft
  guard so alcohol-free beer/wine isn't filed alcoholic. ~214 soft / ~252 alcoholic for a Berlin
  PLZ.
  **`coffee` was split out of `soft_drinks` (2026-07-19, user-reported)** — it was **27% of the
  category** (117 of 441 stored offers) and a bag of beans isn't a soft drink. Moved across the
  layers: `_PATH_MAP` `kaffee`, a `("coffee", …)` `_RULES` tuple placed **before** soft_drinks,
  `BRAND_CATEGORY` nescafé/nescafe/röstfein, and the L2 `iced coffee`/`eiskaffee`/`ganze bohnen`
  form words (which still beat `mövenpick`→ice_cream). **127 offers moved, 0 regressions**
  (121 from soft_drinks, 4 from household, 2 from other). **Tea deliberately stays in
  soft_drinks**: what the feed carries is ready-to-drink Eistee/Bubble Tea/Kombucha, which really
  is a soft drink. **Two brands measured and REJECTED as coffee keywords** (pinned by tests):
  **`tchibo`** — 7 of its 11 stored rows are household (Tchibo Top, Palazzohose); its clothing is
  shielded by a non-food path, but the *pathless* "Tchibo Snack-Piekser" would follow the keyword
  into coffee. **`melitta`** — also filters and machines ("Melitta Barista" is an appliance).
  **`_FOOD_RESCUE["coffee"]` is a bare `"kaffee"` on purpose**, not the narrower
  `kaffeepad`/`kaffeekapsel`: both give the same answer today, but the narrow form made
  `_RESCUE_VETO` **dead code no test could exercise**. With `kaffee`, removing the veto leaks 7
  machines (Kaffeevollautomat ×3, Filterkaffeemaschine ×2, DeLonghi ×2) — so the guard is real and
  measurable. `"espresso"` is NOT a rescue token: it drags in a "CROFTON Espressokocher" (moka pot).
  `product_group` gains a `coffee` map grouping by **FORM** (Kapseln/Pads/Ganze Bohnen/Instant/
  Eiskaffee/Gemahlen — capsules and beans aren't substitutes, so "cheapest" is only fair within a
  form); the old `Kaffee` group under soft_drinks is gone. Mobile is data-driven (chips come from
  `/api/categories`, and `DISCOUNT_DEFAULT_CATEGORIES` is a denylist so coffee gets the €/kg sort
  default free) — the only mobile edit was `catalog.ts`'s `coffee` item, whose `category` fed
  `basketResolve`'s specificity tie-break. **Three categories added 2026-07-17 (PR3 of the audit, 72 offers moved, 0 regressions,
  `other` 6.8%→6.4%)**: **`other_meat`** ("Lamb & Other Meat" — lamb/rabbit/game; `" lamm"`+
  `kaninchen` MOVED out of `pork`, and it runs before `fish` so **`Lammlachs`** — a lamb loin the
  source files under `Fleisch > Lamm` — stops being caught by the `lachs` fish rule); **`eggs`** (a
  deliberately **thin** chip — only ~2 branded egg offers a week — space-padded `" eier "` so the
  `Eier…` compounds stay put: Eierlikör→alcoholic, Eiersalat→pork, Eierkuchen→bakery, Eierkocher→
  household); **`ready_meals`** ("Ready Meals" — Fertiggerichte/sushi/Maultaschen/döner). ready_meals
  is a **layer-2 `_FORM_OVERRIDES` entry**, not a keyword: the source scatters prepared meals under a
  mis-filed path (`Sushi4You`→Feinkost, `Curry King`→Würzmittel, `iglo Fertiggerichte`→Nudeln) AND
  brands that would win (`frosta`→frozen, a `YOUCOOK … Chicken`→poultry), so only L2 consolidates
  ALL Fertiggerichte into one aisle. **`gekühlt` is NOT a ready-meal signal** — it means "chilled"
  and sits on ~100 fridge staples (butter/cheese/cold cuts); chilled pizza deliberately stays in
  `frozen`. Also **margarine → `butter`** (Rama/Lätta/Deli Reform/Kærgården, an L2 override beating a
  `Margarine` path node that maps nowhere; `"rama "` is trailing-space-guarded vs Ramazzotti, and
  RAMA Cremefine is caught at L1 by its Drogerie path) and **Valess → `cheese`** (vegetarian-not-vegan
  filed by main ingredient, an L2 override beating its `Fleisch > Schnitzel` path). **Chip order =
  `CATEGORIES` dict insertion order** (`GET /api/categories` iterates it), so `vegan` was moved to the
  back of the food chips (per the user); the new chips sit with their neighbours (`other_meat` by the
  meats, `eggs` by dairy, `ready_meals` by frozen). New food categories get the €/kg per-category sort
  default for free (`sort.ts` `DISCOUNT_DEFAULT_CATEGORIES` is a **denylist** = `{household}`), so no
  mobile change is needed — new chips are fully data-driven. Both are a re-classification →
  need a recategorize / re-scrape to backfill (Render's deploy boot-scrape does it).
  **`vegan` is a cross-cutting category that wins FIRST** (`app/vegan.py` `is_vegan`, a layer-0
  check in `classify` before the household path): explicitly-vegan products (word `vegan`/
  `pflanzlich`, or a **vegan-only** brand — Vemondo/Like Meat/Garden Gourmet/Beyond/…; NOT mixed
  brands like Rügenwalder) move into `vegan`, *out of* their natural category (a vegan cheese is
  filed under vegan, per the user's choice). Running first also rescues plant-based food the
  source mis-files under a non-food path (REWE → household). `vegetarisch` ≠ vegan. ~42/PLZ. No
  serve-time field / mobile change (a plain category, unlike the Bio *filter*).
  **High-confidence food RESCUE from a non-food path** (2026-07-17, `_food_rescue`, gated inside the
  layer-1 non-food check — `_path_nonfood(path) → _food_rescue(name, brand) or "household"`): the
  source dumps real food under **generic** non-food leaves that carry no category — pet-brand nodes
  (`Tierbedarf > Marken für Tiere`), promo/loyalty nodes (`Saison und Events > Payback`), or a bare
  brand (`Marken > REWE Beste Wahl`) — so REWE's regional produce, Deutsche See fish, poultry salads
  etc. became household. `_FOOD_RESCUE` is a curated set of **specific** food nouns (rispentomate,
  nektarine, maishähnchen, roggenmischbrot, deutsche see…) — deliberately NOT the generic produce
  keywords (`salat`/`tomate` would catch a Salatschleuder / Tomatenpflanze). Guarded by `_RESCUE_VETO`
  (plant/garden/clothing/wood/pet words — Traubenhyazinthe, Mango *Kleid*, Kirschholz, "…Knabbermix"
  cat treats). **The gate on the non-food path is what makes it safe**: it fires ONLY when the path is
  non-food, so a *food*-path Erdbeer-Joghurt is never dragged into fruits. 63 offers rescued
  household→food, **0 regressions** (every move was household→a food category), self-disagreement
  1.2%→1.0% (it resolved the Aprikosen/Nektarinen split — some copies were household, some fruits).
  Wholesale root reclassification was **rejected**: `Marken`/`Saison` each also hold genuine non-food
  (Tchibo clothing, SIM cards, grills, gift cards, plants) that would regress to `other`. New produce
  under a pet/promo node needs a `_FOOD_RESCUE` entry (image-verify first — "Aprikosen" under a garden
  brand was real fruit, but an apricot *tree* would not be). **QA a category against its product images**: re-classify from the DB
  (don't re-scrape — `python -m app.scripts.recategorize` syncs stored rows to the current
  classifier), then build a Pillow contact-sheet of that category's `image_url`s and eyeball
  it (that's how 4 mis-filed "fruits" — a peach aperitif, banana chips, lemonade, a yogurt —
  were caught).
- **Product sub-grouping within a category** (`app/product_group.py`): a *second*,
  coarser layer under `category` — `product_group(name, brand, category) ->
  (group_key, group_label)` keys an offer to a product (e.g. fruits → "avocado")
  from the **name** (the `category_path` leaf is too unreliable: "Aprikosen"→
  Steinobst, "Mix Tafeltrauben"→an attribute node, coupons→no path). Curated
  per-category keyword→German-label map, specific→generic (so "Seelachs" beats
  "Lachs"); produce/meat/fish/cheese/dairy/bakery **+ soft_drinks + snacks** are mapped,
  everything else → `(None, None)`. **snacks** groups by type — Chips/Nüsse/Cracker/
  Studentenfutter (~75% of a Berlin PLZ; Chips before Nüsse so "Erdnussflips"→Chips;
  Studentenfutter before Nüsse so "Alesto Trail Mix"→Studentenfutter, not the "alesto"
  nut-brand keyword). **soft_drinks** groups by beverage *type* — Kaffee/Tee/Cola/
  Limonade/Saft/Wasser/Energy/Schorle/Smoothie (~92% of a Berlin PLZ); since beverage brands
  span types (Volvic → water/tea/juice), the type-word groups come first and each brand's
  keyword sits in its PRIMARY type *after* them (so "Volvic Tee"→Tee, "Volvic naturelle"→
  Wasser). Guard: `" spezi"` (leading space) avoids the "…-Spezialsalz" trap; `"tea"` catches
  English iced teas (Fuze Tea) vs the German `" tee"`.
  **Produce coverage was completed 2026-07-29** (fruits+vegetables **82% → 98%** of a Berlin PLZ,
  32 → 40 distinct sub-groups, 91 rows newly grouped / **0 regressions** over all 10,692 stored
  offers). It matters beyond the deals list: a sub-group is the unit the **Basket** keys on
  (`basketResolve.ts`), so a produce item with no group could not be added as a sub-category at
  all. New: Grapefruit + `piel de sapo`→Melone (fruits); Kohlrabi, Radieschen, Mais, Bohne,
  Edamame, Erbse, Kresse, Ingwer, Chicorée, Pak Choi, Peperoni, and `pfifferling`/`portobello`/
  `shiitake`→**Pilz** — the last of which closes a real drift: PR #106 added those words to
  `categories.py` (to move them *into* vegetables) and nobody added them here. **The two generics
  `Kohl` and `Gemüse` MUST stay last** (`kohl` ⊂ Blumenkohl/Kohlrabi, `gemüse` ⊂ Gemüsezwiebel),
  each pinned by an ordering test. Watch the spelling traps the DB proved: `"pak choi"` alone
  misses the flyer's **`Mini-Pak-Choi`** (hyphens), and `romatom` exists only because the feed
  ships a typo'd "Romatomen". Still ungrouped on purpose: Sauerkraut/Kimchi/Passata (preserved,
  not fresh produce) — they land in the list's trailing bucket, which is honest.
  **The DRUGSTORE aisles are sub-grouped too** (2026-08-04, `_DRUGSTORE_GROUPS`, merged into
  `_GROUPS` at import): 11 categories (body/face/hair/dental/makeup/fragrance/laundry/cleaning/
  baby/health/pet), **73 sub-groups, 2% → 86% coverage, 1173 rows newly grouped, 0 regressions**.
  This is load-bearing, not cosmetic: `BasketModal` only drops `household`, so the other
  drugstore categories DO reach the Basket — and it keys on `offer.group`, so before this a
  shampoo could not be added to a basket at all.
  - **A generic token is far safer here than in the food maps**, because `_GROUPS` is keyed by
    CATEGORY: a bare `reiniger` (cleaning) or `deo` (body) is only ever tested against names in
    that one aisle. `deo` must NOT be space-guarded — "Fa Deo" ends the string.
  - **Order is the rule, as always.** `katzentoilette`/`kratzspielzeug` sit in *Tierzubehör*
    ABOVE Katzenfutter — they contain "katze", so a litter box and a cat toy were being served
    as cat FOOD (caught by auditing what each group swallowed, not by reading). Same shape for
    Trockenshampoo before Shampoo, Aufsteckbürsten before Zahnbürste, Sonnenschutz before
    Bodylotion, and the Fein/Color/Voll-waschmittel trio before the generic Waschmittel.
  - **`_GROUPS.update(_DRUGSTORE_GROUPS)` would silently REPLACE a grocery map** on a key
    collision — no error, just a category that quietly stops grouping. Pinned by a test.
  - **A bare `creme` is deliberately absent from `body`**: that chip still holds a few mis-filed
    FOODS ending in it (a cooking cream, a chocolate). Ungrouped is the honest answer there.
  - `household` **is mapped now** (2026-08-10, `_HOUSEHOLD_GROUPS`, 14 groups, 64.8% of 2,038
    distinct names). It stays out of `_DRUGSTORE_GROUPS` and the Basket still excludes it, so
    this is a deals-list-readability change only — but it was 564 served offers of
    unstructured list, the biggest single block in the app.
    - **The discounters' OWN BRANDS are the signal**: Parkside/Workzone→Werkzeug,
      Livarno/Home Creation/Casalux→Wohnen, Silvercrest/Crofton/Ernesto/Ambiano→Küche,
      Esmara/Lupilu/Up2fashion/Crane→Kleidung, Crivit→Sport, Gardenline/Florabest→Garten,
      Novitesse/Biberna→Bettwaren, Playtive/Toylino→Spielzeug.
    - **The map runs in TWO PASSES and that is the whole design**: every head noun first, then
      the brands. Several brands span aisles, and what a thing IS must beat who made it — a
      CRIVIT Wendejacke is clothing, a LIVARNO Steppbett is bedding, a SILVERCREST
      Dampfreiniger is cleaning. The second pass **repeats the same labels** (legal: same slug,
      one group), which is the only way to express "noun beats brand" in a flat first-hit-wins
      table. A test pins that the fallback pass introduces no NEW label, since a typo'd one
      would silently create a near-duplicate section.
    - **Five substring traps, all found by reading what each group caught**: `blume` ⊂
      "Sonnen**blume**nkerne" (a FOOD — the token is now `blumenstrauß`/`blumentopf`);
      `aster` ⊂ "Pfl**aster**"; `gläser` ⊂ "Wechsel**gläser**n" (sports glasses);
      `tablet` ⊂ "Bett-**Tablet**t" (a tray — Küche carries a `tablett` guard above
      Elektronik); `kleid` ⊂ "**Kleid**erschrank" (a wardrobe — Wohnen carries a guard tuple
      above Kleidung). `schal` is plural-guarded because it is inside "**Schal**e", a bowl.
      `thermo` and `dose` are spelled out (a bare `thermo` caught a blood-pressure monitor).
    - **~63 cosmetics and ~62 edible products in this chip stay UNGROUPED on purpose** — both
      are tracked classifier findings, and adding tokens here would paper over the
      mis-classification. Same call the pantry map makes for the in-store breads. Pinned.
  **EVERY category is being mapped** (2026-08-10, user's call: "I want each category to have sub
  categories"). Measured before starting: **61% of served offers carried no sub-group** — 339 in
  10 unmapped FOOD categories, 564 in `household`, and 247 sitting in the *tail* of maps that
  already exist (cheese 42% ungrouped, dairy 42%, pork 38%, bakery 35%). `other` stays unmapped
  on purpose — it is the classifier's fallback, is driven toward zero by the weekly audit, and
  its contents are unclassifiable by construction.
  - **Adding a map for a currently-unmapped category is 0-regression BY CONSTRUCTION**:
    `product_group` gates on `_GROUPS.get(category)` *before* it reads the name, so a new key
    cannot move an offer in any other category. Only deepening an EXISTING map can regress, and
    that needs the full corpus diff.
  - **`test_every_category_has_sub_groups` is a two-way RATCHET**: a category outside its
    `STILL_TO_MAP` list that has no map fails, AND a `STILL_TO_MAP` entry that has since been
    mapped fails as stale — so finishing one forces its removal. `_GROCERY_GROUP_KEYS` is now
    snapshotted at the `_GROUPS.update()` line so the drugstore-collision test derives its
    grocery set instead of carrying a 12-slug literal that silently stopped covering new keys.
  - **A label the mobile catalog already covers MUST be spelled the catalog's way.**
    `basketResolve.subGroupItem` matches a group label against `GROCERY_CATALOG` by exact
    equality (German name, then each keyword) and a hit wins, because catalog entries carry
    `exclude` guards a synthesized `grp:` item has not. So **"Nudeln"** (not "Pasta"),
    **"Müsli"** (not "Müsli & Cerealien"), "Bier", "Reis", "Mehl", "Zucker", "Speiseöl",
    "Butter", "Schokolade". A label that misses does not merely look different — it mints a
    second basket item and the same product occupies two rows. Pinned by a test.
  - **`alcoholic` (2026-08-10): 12 groups, 98.5% of 615 distinct names.** Two thirds of these
    names are a bare brand with no type word ("Jägermeister", "Aperol", "Heineken"), so each
    type carries its brands after its type words — the convention `soft_drinks` uses for Volvic.
    A brand token is far safer here than in `categories.py` for the usual category-gate reason.
    Four ordering facts, every one caught by reading what each group CAUGHT, none by reading the
    code: **Mixgetränke runs first** (a 0,33 l "Jack Daniel's Cola" can is not a substitute for
    the bottle — the same form-not-brand argument coffee makes for capsules vs beans);
    **Likör before Whisky** (`whisky` fires inside "WhiskyGESCHMACK", so Fireball and Irish Mist
    were being served as whisky); **Sekt and Cider before Wein** (`schaumwein`/`apfelwein` both
    contain `wein`); **Bier before Spirituosen** (or "Salitos Tequila Beer" is a tequila).
    `gin` and `rum` are space-guarded pairs (` gin`/`gin `) because both sit inside "**ORI**GIN**AL**"
    and "t**RUM**pf" — "Havana Club Original" was the tell. `karlsberg` is deliberately NOT a
    Bier token: the brand's only products here are the Mixery and a vodka RTD.
  - **`pantry` (2026-08-10): 22 groups, 90.9% of 484 distinct names.** Ordering did all the
    work: Feinkost-Salate before Konserven AND before Gewürze (else "Hummus Dattel-Curry" is a
    spice), Konserven before Zucker (else "Bio-**Zucker**mais" is a bag of sugar), Speiseöl
    first (`olivenöl` contains `oliven`), Fix & Instant before Nudeln (a cup noodle is not dry
    pasta). Never a bare `öl` (inside "**Köl**ln") or a bare `hefe` (inside Hefezopf,
    Hefe-Röllchen, Hefeweizen). `tortelli` matches neither Tortellini nor Torte**ll**oni —
    the stem is `tortell`.
  - **Bakery breads and the Sol & Mar range mis-filed into `pantry` stay UNGROUPED on purpose**
    — both are known classifier findings, and adding bread keywords to the pantry map would
    paper over the mis-classification and make it invisible. Pinned by a test.
  - **The other 8 food categories (2026-08-10): 97.2% of 573 distinct names.** `sweets` (10
    groups) and `frozen` (6) group by product type; **`ice_cream` groups by FORM like coffee**
    (a Magnum on a stick, a 900 ml tub and a multipack of cones are not substitutes);
    **`vegan` groups by the food each product REPLACES** (Pflanzendrink / Fleischalternative /
    Käsealternative), since the chip is cross-cutting and its members are otherwise unrelated.
    Ordering again did the work: **Kaugummi before Fruchtgummi** (`gummi` ⊂ "**Kau**gummi", so
    chewing gum was serving as jelly sweets), Riegel/Kekse/Waffeln before Schokolade
    (Schoko**riegel**, Schoko**kekse**), Wassereis before Stieleis (`sticks` ⊂ "Fruity Sticks"),
    Kuchen and Kekse before the Nutella jar, Margarine and Kräuterbutter before Butter
    ("**Rama mit Butter**"), Pizza before Backwaren ("Pizza-**Brötchen**").
  - **Three stems that looked right and matched nothing**, each found by diffing the real DB:
    `tortelli` matches neither Tortell**ini** nor Tortell**oni** (the stem is `tortell`);
    `mühlen` misses "Rügenwalder **Mühle**"; `kräuterbutter` misses the hyphenated
    "Kräuter-Butter". Kærgården ships with **æ, ae AND a**, and "Multiplack-Eis" is the feed's
    own typo — both are pinned.
  - **`eggs` and `other_meat` render a single header over the whole chip** (~2 offers/week,
    all "Eier" / all "Lamm"). A `buildSections` guard collapsing a lone group back to a flat
    list was written and then **dropped**: it reverses the deliberate 2026-07-29 decision to
    head single-offer groups, and it does not address the case it was written for (MANY
    singleton groups, where it never fires). One redundant header line is the cheaper answer.
  **The 23 pre-existing maps were deepened last** (2026-08-10), closing the 247-offer tail
  they still carried: cheese 58%→82%, dairy 58%→95%, pork 62%→90%, bakery 65%→95%,
  soft_drinks 65%→85%, poultry 70%→96%, fish 75%→94%. **Overall grouped: 39% → 82%.**
  - **This is the ONLY block that can regress**, since a new token sits beside tokens that
    already place products — so it gets the full corpus diff. But the harness's binary
    "left an existing group = regression" is too blunt here: 46 offers moved from a map's
    GENERIC bucket to a specific one (`Käse` → `Feta`/`Cheddar`/`Bergkäse`), which is exactly
    what deepening means. The diff was re-cut into three buckets — newly grouped /
    generic→specific / **specific→specific or grouped→ungrouped** — and only the third is a
    real regression. It read **zero**.
  - **Three candidates were wrong and only reading the moved rows found them**: `patros` →
    Frischkäse (it is a brined WHITE cheese, so it belongs in Feta), `ofenkäse` → Halloumi &
    Grillkäse (a soft BAKING cheese is not a firm grilling one), `fladenbrot` → Sandwich &
    Wrap (a flatbread is bread).
  - **`hochland` is deliberately NOT a cheese brand token**, though every other big one is:
    the same word sits in "FAIRGLOBE Bio **Hochland** Kaffee", a bag of coffee the classifier
    files into this chip. Its products still resolve via `patros`, which names a real cheese.
    Pinned by a test.
  - **The umlaut plural bites here too** — "Nürnberger Rostbrat**würste**" never matched the
    `bratwurst` stem, exactly as `categories.py` already records for its own keyword layer.
    Both `bratwürst` and `rostbratwürst` are now tokens. Found by a test failing, not by
    reading.
  Computed in the serializer → `OfferOut.group`/`group_label`
  (**no DB column / migration**, like `unit_price_cents`). The app renders a
  `SectionList` **only in a selected category** (not All/search): **every** sub-group gets a
  header, ordered by size then A–Z (`dealFilters.ts` `buildSections`, `components/GroupHeader.tsx`),
  and only offers with **no** sub-group fall into the trailing "More" bucket. Single-offer groups
  are headed too — `Kiwi · 1 offer · from 2,49 €`, singular — because the sub-category is the unit
  the user shops in *and* the unit the Basket keys on, so hiding it below 2 offers made a lone Kiwi
  unnameable (changed 2026-07-29; it costs ~12 extra headers across 8 categories). `buildSections`
  pushes groups **unconditionally**: a `byGroup` entry is created as `[o]` and only grown, so a
  length guard there is a branch no test can fail. `label: null` on the bucket now means "not one
  offer in this category carries a sub-group" — i.e. a category `product_group` doesn't map
  (pantry, sweets, alcoholic…), which must keep rendering as a plain flat list. Grouping makes
  category mis-classification *visible* (a peach-flavoured drink lands under
  "Pfirsich"), so it's a good lens for tuning `categories.py`.
- **A failed scrape serves NOTHING in production, not sample data** (2026-08-17,
  `settings.scrape_sample_fallback`, default **False**). `_sample()` offers carry INVENTED
  prices and plausible validity windows, and nothing downstream can tell them apart — not the
  Basket totals, not Compare, not the `grocery-price-history` collector, which would record
  them as that week's real price. A missing chain is visible (the data gate's per-chain floor
  names it); a fabricated 1,59 € shampoo is not. Local dev opts in via
  `SCRAPE_SAMPLE_FALLBACK=true` in `backend/.env`; the default is off so **Render is correct
  with zero configuration** — a default-on flag would have to be switched off in the dashboard
  and remembered forever, which is the `ADMIN_TOKEN` shape.
  - **What prompted it**: on 2026-08-16 Rossmann's 23–26pp weekly simply **was not published**.
    Upstream had only the `Schulaktion` (correctly dropped by `MAX_FLYER_DAYS`) and a **6-page**
    "Mein Drogeriemarkt" whose `/pages` returns page IMAGES and no product data, so the parser
    correctly yielded 0 offers → `RuntimeError` → 8s retry → samples. `_select_brochures` was
    NOT at fault (the imminent branch does select a Mon-start brochure from a Sunday run —
    walked concretely). It failed twice: the served samples were dated 08-17, and `_sample()`
    uses `date.today()`, so today's cold-start boot scrape produced them, not Sunday's reset.
  - **The reason it took a live upstream probe to diagnose**: `exc_info=True` sat OUTSIDE the
    `except` block in `MeinprospektScraper.fetch`. Both exits are a `break` from inside a
    handler, and CPython clears the exception state on handler exit — so production logged the
    literal `NoneType: None`. `except ... as exc` also unbinds `exc` at the end of the block,
    so the failure must be **captured into a variable** and passed as `exc_info=failure`.
  - **`metrics.record_scrape_failure(chain, reason)`** now counts it into `/api/scrape-stats`
    (`scrape_failures`). `record_throttle` only ever fired for HTTP-status-shaped failures
    inside the pacing transport, so every `RuntimeError` and transport drop read as zero.
  - **The `(sample)` store-name suffix was never a reliable signal** and the belief that it
    marks a degraded run is stale: it existed only in `lidl.py`/`dm.py`, never for the
    meinprospekt chains — and `_get_or_create_store` sets `name` only on INSERT, while
    `/api/reset` deletes `Offer` rows and leaves `Store` rows, so an old name would persist.
  - **The ALDI DIVISION SKIP records nothing, and now that is conspicuous.** When Overpass
    can't resolve Nord vs SÜD, `run.py` skips ALDI and logs — deliberate fail-closed, but it
    never reaches `record_scrape_failure`, so on 2026-08-17 prod served 5 grocery chains with
    `/api/scrape-stats` reporting only `{'rossmann': 1}`. The gate catches it (`chains >= 6`);
    the dashboard does not. Wire the skip into the same counter.
  - **A Lidl failure still costs all six flyer chains**, sample flag or not: the Lidl Plus
    lookup resolves the store COORDINATES and `run_scrapers` gates every meinprospekt chain on
    `store.lat is not None`, and that path has never returned lat/lng. Its log now says so
    explicitly, because the symptom is six dark chains and the cause is one line about Lidl.
    Decoupling it (`services/store_locator.plz_centroid` is the seam) is deferred.
- **Aggregators soft-throttle bursts** (marktguru, Bonial): they return empty
  after many quick requests. Scrape weekly, and `tracked_client` now **paces** every
  outbound call (global min-gap + jitter) and **backs off/retries** on 429/5xx honoring
  `Retry-After` (see the "Outbound calls are counted, paced, and backed off" note above);
  both scrapers **serve NOTHING on failure since 2026-08-17** (see the note below), and a
  throttle is metered
  (`/api/scrape-stats` `throttles`), not silently hidden behind the sample fallback.
  **The throttle's real shape is HTTP 200 with LESS CONTENT, not an error** (proven from Render
  logs, 2026-07-19): the publisher page answers 200 with an **empty brochure list**, or lists a
  brochure whose pages parse to **zero offers**. Nothing fails, so `tracked_client`'s status-retry
  never sees it, `throttled_total` stays 0, and the chain quietly serves samples. `fetch` therefore
  **re-asks once after `settings.scrape_thin_retry_s` (8s) before believing an empty answer** —
  retrying **only** its own `RuntimeError` ("no active weekly brochure" / "returned no flyer
  offers"), never an HTTP error, since 5xx/429 are already retried upstream and a 403 is a hard
  block. Tests set the pause to 0 (`SCRAPE_THIN_RETRY_S`).
  **What triggered the burst is worth knowing**: `/api/reset` on a sleeping free-tier container
  makes it cold-start, run its **own boot scrape of `DEFAULT_PLZ`** (`main.py` `lifespan`, ~13
  outbound calls) and only then serve the reset — which deletes everything that boot scrape just
  wrote and scrapes again, hitting the same five publisher pages a second time inside a minute.
  `scrape.yml` now curls `/health` first (it only answers once startup, boot scrape included, has
  finished) and waits 60s, so the weekly job stops firing a doubled burst. Measured that Sunday:
  lidl/rewe/aldi degraded on the second pass, all five fine ten minutes later.
- **Brochure discovery is location-pinned via a cookie** (`bonial.py`
  `_location_cookie`, `_current_brochures`): meinprospekt's publisher page (`/rewe-de`
  etc.) picks which **regional** brochures to show from a `location` cookie it otherwise
  seeds from the **request's IP geo** — so without pinning, a Frankfurt-hosted Render and a
  Berlin laptop discover *different* brochures for the *same* PLZ (Render was serving
  Frankfurt REWE/EDEKA flyers to Berlin users, and counts differed by host). We send a
  `location={"lat","lng","zip","countryCode"}` cookie built from the scraped PLZ's coords
  (proven to override IP: a Munich-coord cookie returns Munich brochures from a Berlin IP),
  so discovery is correct + deterministic. The brochure *content* endpoint (`/pages`)
  already takes `lat`/`lng`; the cookie fixes the *list*. (REWE/EDEKA are regional; Lidl is
  national, so Lidl is unaffected.) **Between-weeks (Sunday) gap:** `_current_brochures` delegates
  the choice to pure `_select_brochures(found, now, chain)` — normally the currently-valid weekly
  brochure(s) (`validFrom <= now <= validUntil`), but when none is active (Sunday, after last
  week's ended and before next week's `validFrom`) it serves the **soonest already-published
  upcoming** week (`UPCOMING_LOOKAHEAD_DAYS=8`, nearest week only) instead of sample data. Before
  this every Sunday scrape — **local AND Render, it's pure logic not an IP/throttle issue** —
  raised "no active weekly brochure" → samples; the fix pulled ~1174 real offers vs 53 samples for
  a Berlin PLZ. (Meinprospekt publishes next week's brochure Sun with `validFrom` = Mon 00:00
  Berlin = 22:00 UTC, so on Sunday it's listed-but-not-yet-active.)
- **Offers are deduped at scrape time too** (`dedup.py` `dedup_scraped`, called in
  `run.py` `_upsert`): the publisher page can surface several overlapping brochures, so the
  same product repeats across them with distinct content ids → the **raw** scrape count was
  non-deterministic (Render ~1506 vs local ~1087 for one PLZ). Collapsing by
  `(normalized name, price)` per store before upsert makes the stored set + the reported
  `scraped` count depend only on distinct products. This is the scrape-time twin of the
  serve-time `dedup_offers`; serve-time dedup still runs (it also catches cross-*source*
  coupon/flyer dups, which scrape-time — per source — does not).
- **QA principle — check cross-environment parity for host-dependent data.** The
  location-pinning bug above hid for a while because the *same* scrape logic runs on the dev
  Mac (Berlin IP) and Render (Frankfurt IP), and outputs were only ever checked on **one host
  at a time** — each looked plausible; the mismatch only appears side-by-side (the user
  noticing iOS vs web). Lessons baked in here, apply them to any future source: (1) when
  output depends on host/IP/location, verify the **same input yields the same output from
  both local and Render** before trusting it — the hermetic fixture tests can't (no live
  host). (2) A **count that varies by host or run is a bug signal, not noise** — here it
  masked duplicate + wrong-region brochures; serve-time dedup made the app *look* fine, which
  hid it. (3) **Pin location end-to-end**: the content endpoint was lat/lng-gated but
  discovery wasn't — a half-pinned pipeline that read as complete (CLAUDE.md even claimed the
  feed was "location-gated"). (4) **"More rows" ≠ "better data"** — Render's extra offers
  were the wrong region, not a bonus.
- **System Python 3.9's old LibreSSL can't TLS-handshake with some hosts** (e.g.
  marktguru) under `httpx`; meinprospekt/Lidl Plus work fine. For ad-hoc probing
  of TLS-picky hosts use `/usr/bin/curl` (SecureTransport).
- **SQLite-under-a-running-server gotcha**: deleting/recreating `backend/grocery.db`
  while `uvicorn` runs leaves stale pooled connections serving inconsistent data.
  After re-seeding the file, touch a backend `.py`
  (`python3 -c "import os; os.utime('app/main.py', None)"`) to force a reload +
  fresh pool.
- **DB schema is Alembic-managed** (`backend/alembic/`, `app/migrations.py`): the app
  runs `alembic upgrade head` at startup (not `create_all`). A model change → `alembic
  revision --autogenerate -m "…"`, review, commit; CI `alembic check` fails if a model
  drifts from the migrations. env.py drives the URL from settings (one config for SQLite
  + Postgres) with `render_as_batch=True` so SQLite ALTERs work. A pre-Alembic DB (tables
  but no `alembic_version`, e.g. an old dev `grocery.db`) is **stamped** at head on first
  boot, not re-created — so existing DBs (and a persistent Postgres) upgrade cleanly.
  **Tests build schema via `create_all` directly** (in-memory), so they don't touch
  Alembic. The Dockerfile must `COPY alembic ./alembic` (runtime needs the scripts).
- **Per-unit price & loyalty bonus are display-only fields** pulled from data we
  used to discard: `Offer.price_per_unit` = the source's per-unit string
  ("1 kg = 13.33"), from the flyer `priceByBaseUnit` / Lidl `pricePerUnit`
  (formatted client-side by `mobile/src/format.ts` `fmtPricePerUnit`).
  `Offer.loyalty_note` = a REWE card bonus ("1,00 € Bonus"), parsed from an `OTHER`
  deal's description/conditions by `bonial.py` `_loyalty_note` (most bonuses lack
  the `isCard` flag, so match on the "€ Bonus" text, not `isCard`).
  `Offer.app_price_cents` = a chain's **app-coupon price** (EDEKA "App-Preis" 2,99 €,
  the Milka example), parsed by `bonial.py` `_app_price` from a `SPECIAL_PRICE` deal
  whose `conditions[].other` contains "app" — **app markers only** (APP-PREIS / NUR
  MIT APP / …); Payback / "6 für" multibuy / "ab 2 Kisten" bulk / day-only specials
  are skipped (not a simple per-item price). **The app price is the card headline** (2026-07-04):
  when present + below the flyer price it becomes the main price + a gold "Mit App" pill, the
  flyer/regular price is struck through, and the **discount badge is computed from it** — mobile
  pure `src/appPrice.ts` (`hasAppDeal`/`headlinePriceCents`/`headlineStrikeCents`/
  `headlineDiscountPct`; badge base = `regular_price_cents ?? price_cents`, so the ~25/PLZ app
  offers with **no** struck regular finally get a badge too). It also drives the **"Biggest
  discount" sort** (`compareOffers`). The full regular/flyer/app breakdown stays in the **deal
  detail** (`FlyerModal`, "Mit App: …"); ~40–53 EDEKA/E-center offers/PLZ (roughly half with a
  struck regular, half without). **Backend stays display-only** — the basket optimizer, Compare,
  and the "Lowest price"/"Cheapest €/kg" sorts keep the guaranteed flyer `price_cents` (the app
  price is conditional on installing the chain app). Fields already in `OfferOut`, so it's an
  OTA-only change (no re-scrape / no cache-clear).
- **Raw source payload is persisted for "View payload"** (`Offer.raw_payload`, JSON Text): the
  scrapers capture the **full** source object verbatim (`ScrapedOffer.raw` — flyer `content` dict
  in `bonial.py`, Lidl coupon dict in `lidl.py`), written by `run.py` `_upsert`. Served on demand
  by **`GET /api/offers/{id}/payload`** (`{id, source, payload}`) — deliberately **not** in
  `OfferOut` (too big for the 2000-offer list). The app's `FlyerModal` has a **"View payload"**
  button that lazily fetches + pretty-prints it (every field the source returns, incl. ones we
  drop: flyer `parentContent`/`publisher`/`linkOuts`/alt images/`deals[].min`; coupon
  `offerType`/`redemptionChannel`/`productIds`/`featured`). **Set at scrape time** → `raw_payload`
  is null for pre-capture/sample rows (UI shows "not captured yet"); Render's Sunday reset
  backfills prod. Migration `210fa9f3d7a9`. **Payloads are prefetched + cached on-device for
  offline, cold-start-free viewing** (the per-offer fetch otherwise cold-starts the sleepy free
  tier every inspection): **`GET /api/offers/payloads?plz=`** returns *every* deduped offer's
  payload keyed by id (mirrors `/api/offers`' dedup + validity filter so ids line up; ~2 MB; not
  in `OfferOut`). `DealsScreen` `prefetchPayloads()` fetches it in the **background after a deals
  fetch** (Render is warm) — **gated**: only downloads when the `payloadCache` is missing / a new
  flyer week (`dealsStale`) / the deal count changed, so a no-change pull-to-refresh doesn't
  re-pull 2 MB. Stored in its **own** `payloadCache` key (`storage.ts`, single-PLZ ~2 MB, separate
  from the 1 MB `dealsCache`; cleared with the deals cache + on reset). `FlyerModal` reads the
  cache **first** (`key in cache.byId`, so a captured-null shows "not captured" offline too),
  **falling back** to `GET /api/offers/{id}/payload` on a miss — so it degrades safely during the
  deploy window / for an un-prefetched offer.
- **"Cheapest €/kg" sort** uses `OfferOut.unit_price_cents` — `app/unit_price.py`
  `unit_price_cents()` normalizes `price_per_unit` to cents per **kg or litre** on
  one comparable axis (German Grundpreis; per-`Stück`/`wl`/`m`/malformed → None).
  It's **computed in the serializer** (no DB column/migration); the app sorts the
  loaded set client-side, nulls sink to the bottom. Sort is chosen in the **FilterSheet**
  (`SORT_OPTIONS`/`sortLabel` in `sort.ts`) with **3 modes** — *Lowest price* (`price_cents` asc), *Biggest discount*
  (`discount_pct` desc), *Cheapest €/kg* (`unit_price_cents` asc) — all via one
  `compareOffers(a,b,mode)` comparator reused by the flat list, the within-group order, and
  the "More" bucket (so "discount" ranks by % even inside a category, not by price).
- **The sort is PER CATEGORY, not global** (2026-07-16, `sort.ts` `defaultSortForCategory`/
  `resolveSortMode`, both pure + tested): `effectiveSort = sortByCategory[selected] ?? default(selected)`,
  and in **All** the persisted global `sortMode` (default *Biggest discount*). The default inside a
  category is **€/kg for every food category**; only **household** keeps discount. That's measured, not
  taste: on a Berlin PLZ €/kg out-covers `discount_pct` in *every* category except household — overall
  **72% vs 34%**, fruits **77% vs 47%**, pantry 93% vs 18% (REWE/ALDI mostly publish no strike price, so
  most offers have no `discount_pct` to rank by and sink). household is the lone non-food category (the
  classifier's non-food path lands there) and the one place discount wins (36% vs 25%). The rule is a
  **denylist** (`DISCOUNT_DEFAULT_CATEGORIES = {household}`) so `other`/`vegan` and any *future* food
  category get the sensible default with no code change — retune by adding a slug. Changing the sort
  **inside** a category records it for that category only (persisted `sortByCategory`, `storage.ts`);
  changing it in All sets the global. Like `hiddenStores` it's a persisted *preference*, so the sheet's
  **Reset does not clear it** (only "Reset all app data" does). Why per-category at all: one global sort
  can't fit both — picking €/kg for Fruits used to leave household (25% €/kg-covered) sorted by it.
- **The raw Grundpreis is normalized at serve time** (`unit_price.py`
  `normalize_price_per_unit(ppu, price_cents)`, called by the serializer **before** the
  derive fallback). `Offer.price_per_unit` mirrors the feed verbatim and the feed is
  inconsistent — only `"1 kg = X"` parses (both here and in the app's `fmtPricePerUnit`), so:
  **`"(1 kg = 8.05)"`** (parenthesized — ~19% of served offers!) is unwrapped (the anchored
  `_EQ_RE` can't read it, and the card rendered literal garbage `"8,05) €/(1 kg"`); a bare
  **label** `"kg-Preis"`/`"100-g-Preis"` (the price IS the per-unit price) is rebuilt from
  `price_cents`, with per-100g normalized **to kg** (the feed's own convention — EDEKA's
  0,39 €/100 g cherries carry `"1kg = 3,90"`); `"kg-Preis = 4.98"` → `"1 kg = 4.98"`; and the
  German shorthand `"-.90"` → `"0.90"`. A label with no price returns None **so the derive
  fallback can run** (a non-null junk string used to suppress it). Non-kg/l units (`1 WL`,
  `1 m²`) are unwrapped for display but stay unsortable. Lifted €/kg coverage **53% → 72%**
  of a Berlin PLZ (+272), display + sort fixed in one place — **no OTA, no re-scrape**.
  **The leading `1` is optional and the unit may be a word** (`_BARE_UNIT`, added for ALDI):
  `"kg = 5.97"`/`"(Liter = 0.99)"` → `"1 kg = 5.97"`/`"1 l = 0.99"` — ALDI drops the amount every
  other chain prints, so `_EQ_RE`'s `^\s*1` anchor rejected it (only **2%** of ALDI was sortable →
  **66%**). Only an *optional literal `1`* is allowed — `"100 g = 2.19"` must NOT read as per-kg.
  Also: a colon typo'd as the decimal separator (`"Liter = 1:75"`) is substituted **before** the
  value is read (else it silently parses as 1.00 — a wrong €/kg is worse than none); the value is
  cut to its leading number, dropping `ATG` (Abtropfgewicht) and range tails (`"6.64/5.98"` → the
  value the card already showed) while **keeping** the German whole-euro `"4.-"`. This also
  canonicalizes the feed's missing spaces (`"1kg=5,66"`), which **1385 of 3599** stored Grundpreise
  had — they were rendering **`"5,66 €/1kg"`** on the card (`fmtPricePerUnit` strips `^1\s+`, so it
  needs the space). Verified: 0 regressions over all 5505 stored offers, +12 newly sortable.
- **Missing Grundpreis is recovered at serve time** (`unit_price.py`
  `derive_price_per_unit(unit, price_cents)`, used by the serializer when
  `Offer.price_per_unit` is null/unnormalizable), three cases: (1) the Grundpreis is **embedded in
  the description** ("…1 kg = 5.67 150 g") → extract it; (2) the item is sold as a
  **single net weight/volume** → **divide** the price by that amount on the €/kg|€/l
  axis ("500-g-Schale" @ 1,49 € → "1 kg = 2.98", "2,5 l" → €/l, "Klasse I 1 kg" is
  just the num=1 case); (3) anything ambiguous → None (a wrong €/kg is worse than
  none). The division **guards the traps** (`_DIVIDE_TRAP` + a one-token rule): a
  multipack ("3x 400 ml", "20 × 10 g"), an approximate ("Ca. 1,1 kg"), a numeric
  range ("250-300 g", "1,2/1,1 kg"), or any *second* quantity incl. a count ("900 g
  30 Stück", "500 g 1 kg") → None; a lone hyphenated weight ("500-g-Schale") is fine
  because the range rule needs a digit on **both** sides of the separator. Feeds the
  card display + `unit_price_cents`; serve-time only (no DB column/migration), so it
  applies on Render right after deploy without a re-scrape. Lifts live €/kg coverage
  **~52% → ~69%** of offers (+~230). **Scrape-time twin — the `kg-Preis` flag**
  (`bonial.py` `_kg_price`): by-weight items (loose Honigmelone) flag the SALES_PRICE
  deal with a `conditions[].other == "kg-Preis"` while `priceByBaseUnit` is empty — the
  advertised price IS per kg, so the parser stores `price_per_unit = "1 kg = <price>"`
  (the Lidl-coupon shape both `unit_price_cents` and the app already parse). Exact-match
  the normalized condition (a REWE travel offer has "Festpreis" inside a long condition
  and must not match); `priceByBaseUnit` wins when present.
- **Day-limited deals — per-offer validity** (`bonial.py` `_offer_validity`): a flyer offer
  can be on sale only certain days (Lidl Thu–Sat "Wochenend-Kracher", Mon–Fri, single-day).
  The real window is in `content.publicationProfiles[].validity` (`startDate`/`endDate`,
  UTC Berlin-midnight boundaries — convert with `zoneinfo("Europe/Berlin")`, `endDate` is
  *exclusive*); we read it (union of brochure-overlapping profiles, clamped) into
  `Offer.valid_from`/`valid_to` **instead of the whole-brochure window** — so a Thu–Sat deal
  no longer reads as valid all week, and the `/api/offers` `valid_to >= today` filter drops
  ended day-deals correctly. **No schema change** (reuses the date columns), but it's set at
  **scrape time** → Render needs a re-scrape (not just recategorize) to backfill. `tzdata` is
  a dep so the Berlin conversion is host-independent (slim Docker strips the system tzdb).
  `app/validity.py` derives **computed** `OfferOut.valid_days` ("Do–Sa"/"Fr") + `day_limited`
  (window < the Mon–Sat week) in the serializer; the app shows an orange day pill on the card
  (`OfferCard`) + a **"Special days"** option in the FilterSheet (shown only when
  some offer is `day_limited`; filters client-side to `day_limited` offers — every non-week-long
  special, not the device date). Measured (a Berlin PLZ):
  Lidl ~227 day-limited (Do–Sa/Mo–Fr/Do–Fr/Fr–Sa/Fr); REWE/EDEKA all full Mon–Sat.
- **Organic ("Bio") filter** (`app/organic.py` `is_organic` → computed `OfferOut.is_bio`):
  serve-time deterministic detection of organic offers from the name/brand — a word-boundary
  `bio`/`öko`/`organic` + organic brands (Bioland/Demeter/Naturland/Alnatura/dennree); the word
  boundary guards substring traps ("…symbiose", "antibiotikafrei"). **No DB column / migration /
  re-scrape** (like `unit_price_cents`/`valid_days`), so it applies on Render right after deploy.
  The app badges Bio offers (green pill, `OfferCard`) + a **"Bio only"** option in the FilterSheet
  (shown only when some offer is `is_bio`; filters client-side, composes with
  store/category/search/special-days). ~6% of a Berlin PLZ's offers.
- **Store visibility IS "My stores"** (2026-07-15): which chains' deals you see is controlled from
  the **Stores modal** (`StoresModal`'s Add/Added ✓), **not** the FilterSheet — the "Stores shown"
  section was removed. Backed by the **existing `hiddenStores`** key (+ `stores.ts` helpers), NOT by
  `myStores`: it's a *hidden*-set, so an untouched chain is visible, a **newly scraped chain is
  visible automatically**, and the never-hide-the-last guard still applies. Inverting to a
  visible-list would mean "show nothing" on a fresh install and would hide 4 chains the moment you
  added your first store. So a tracked chain reads **"Added ✓" by default** (the user read
  tracked-but-unadded as a bug — it was that `myStores` did *nothing* outside the modal, a pure
  bookmark, while the real switch was buried in a filter sheet). `myStores` now has exactly one job:
  remembering **which branch** you picked via Change (display only). Add/Added is shown **only for
  `active` chains** — an inactive one gets "Deals coming soon" (no deals to show ⇒ no Add). Rows show
  the live `chainCounts` ("244 deals" / "No deals loaded — pull to refresh") so "did adding it work?"
  is answerable. The FilterBar store chip (✕ = show all) stays as the escape hatch, but the sheet's
  **Reset no longer clears `hiddenStores`** — it's a persisted store choice, not a transient filter.
  **Two store controls, two meanings — don't re-merge them** (the user uses both): the Stores
  modal's Add/Added = *membership* (persistent, `hiddenStores`); the FilterSheet's **"Only show"**
  = a **MULTI-select, persisted lens** (`storeLens` in `DealsScreen`, `DealFilterOptions.storeLens`,
  storage key `storeLens`) over the stores you already keep — tap to add, tap again to remove,
  **empty = All**. It scopes the deals list **and the Basket's MATCHING** (2026-07-31) — the
  shopping plan and the per-item deals picker both build from `filterByStoreLens(foodOffers,
  storeLens)`, passed down as `BasketModal`'s `storeLens` prop. If you've said you're shopping
  Lidl and Aldi, a plan drawn from every chain isn't a plan you can act on; measured live, the
  same basket goes E center 1,49 € → Lidl 12,99 € for chicken when lensed. `buildPlan` derives
  its single-store comparison from the array it's handed, so "vs X alone" scopes for free, and
  a pick made before the lens narrowed is silently ignored (falls back to the cheapest in-lens
  match) and returns when the lens clears.
  **What the lens does NOT scope: the ADD vocabulary.** `liveGroups`/`liveShown`/`addFromText`
  and the catalog chips stay on the unlensed `foodOffers`. A basket item is store-agnostic ("I
  want kohlrabi") and an item with no in-lens deal honestly reads "No deal this week" — but the
  load-bearing reason is an invariant: `addFromText` falls through `liveShown` before minting a
  `free:` key, so lensing that path makes a typed add and a swipe-add of the SAME product mint
  different keys and occupy two basket rows. Pinned by tests both ways.
  **Recipes is deliberately untouched** — it has its own persisted "Shop at" (`RecipePrefs.stores`).
  Pass the lens as a prop to `BasketModal`; never pre-lens `modalOffers`, which RecipesModal shares
  (its chip row derives from that array, so narrowing it would silently drop chains).
  **The plan card lists the items per store** (not "N items"): each line is the basket item + its
  price with the matched product name under it, so the card works as a standalone shopping list,
  plus a muted `storeLensLabel` note when the plan is narrowed (or a hidden cheaper store reads
  as us missing the deal). `testID="plan-card"`; the basket row is labelled
  `Choose a deal for <item>` (it had no accessible name at all before).
  **The pure core is in `stores.ts`**: `toggleStoreLens` (uncapped, and deliberately WITHOUT a
  never-empty guard — the mirror of `toggleHiddenStore`'s — since empty *means* All, so clearing
  the last pick is the way back), `activeStoreLens` (intersect with the visible chains) and
  `storeLensLabel` (1–2 names → `Only Lidl · REWE`; 3+ → `Only 3 stores`, since the chip row
  scrolls and a long label shoves the sort button off 375pt).
  Three rules make persisting it safe, all in `activeStoreLens`: the intersect is **partial** (a
  selection whose other chains vanished narrows to what survives), an **empty intersection is a
  no-op** (a stale pick can never empty the list), and **full coverage collapses to All** (picking
  every visible chain filters nothing, so showing a chip whose ✕ does nothing — with "All" dark
  while every pill is lit — would contradict itself). The collapse lives ONLY in the derivation,
  never in the toggle or `filterDeals`: coverage can become total with no tap at all when hiding a
  store shrinks the available set. `DealsScreen` toggles the *derived* value, so the tap after a
  collapse starts from All. **`[]` is truthy** — the chip and `filterDeals` must test `.length`,
  and tsc will not catch it.
  In `filterDeals` it stays **after** `hiddenStores` (so it can't lens a hidden store into view)
  and **after** the E-center dedupe; its only-when-present guard tests `dedupedBase`, **not** the
  raw `offers` arg that special-days/bio use — a chain whose every offer is an E-center duplicate
  is "present" in `offers` but has nothing left to show, so harmonising those guards empties the
  list. The sheet's **Reset clears it** (unlike `hiddenStores`): it lives in the Filters sheet and
  carries a removable chip, so it reads as a filter — and the pre-#69 persisted store filter
  behaved the same way.
  (History: the sheet's old multi-select "Stores shown" was a **hide-set**, so isolating one store
  took four taps — that, not multi-select, is why PR #69 removed it and PR #70 brought it back
  single-select. A *positive* selection keeps one-tap isolation AND allows several, so the
  tradeoff is gone; multi-select + persistence restored 2026-07-28 at the user's request.)
- **The deals cache is versioned** (`format.ts` `DEALS_CACHE_VERSION` + `dealsCacheStale`): the
  weekly cache is *authoritative*, so while it's fresh `DealsScreen` makes **zero backend calls** —
  which meant a newly scraped chain stayed **invisible until Sunday** unless the user knew to hit
  Options → "Clear cached deals" (this hid E center, then ALDI). **Bump `DEALS_CACHE_VERSION` in any
  release that adds a chain** (or otherwise changes served deals a cached week can't represent);
  `setDealsCache` stamps it. A mismatch is treated as **stale, not absent** — the old deals still
  render instantly (no spinner, no cold-start block) while a background `revalidate` swaps them.
- **The Filters sheet's pill counts are FACETED** (2026-07-29, `dealFilters.ts` `facetCounts`):
  every count answers **"how many would I see if I turned this on?"** — each facet is counted with
  **its own filter neutralised and every other one still applied**. That's the only reading that's
  actionable: counting with the facet ON shows 0 for every store you haven't picked, and counting
  the whole set (what these pills did before) over-reports, since it ignores the E-center dedupe,
  hidden deals, non-food, search and the category chip. Live example: E center *278 → 166*, and with
  Bio on the store pills read 2/19/16/11/1 — summing to exactly the Bio count (49).
  **The store counts are additive with the list**: the lens step is a plain per-chain filter and
  everything after it is a per-offer predicate, so picking {A,B} yields `chains[A] + chains[B]` rows
  (the one exception is the lens's own no-op guard — a chain whose every offer is an E-center
  duplicate counts 0 and, picked alone, no-ops to the full list; 0 is the honest thing to show).
  **The section GATES stay whole-set** (`hasDayLimited`/`hasBio`, and `hiddenCount` = the size of
  the hidden set): a section that vanished because a filter excluded everything would strand you —
  notably you'd lose the only route back to un-hide. So a section can render "Special days (0)",
  which is the honest answer, rather than disappearing. Four extra pipeline passes, so it's
  **computed only while the sheet is open** — measured **0.70 ms** for all four over 1635 offers
  (3.5x one list pass). `DealsScreen` builds one `filterOpts` memo that the list, `mineBase` and
  the counts all share, so they cannot drift.
- **Deals-screen filter UI (redesigned)**: secondary filters live in a **bottom sheet**
  (`components/FilterSheet.tsx`) opened from a single **`FilterBar`** (sort summary + a "Filters"
  button badged with the active-filter count + a removable chip per active filter). The sheet holds
  Sort / **"Only show"** (see below) / Special days /
  Bio / Non-food as labelled pill sections **with the per-option counts**; the category-chips row is
  the only inline filter now. Filter state stays in `DealsScreen`; the old
  `StoreFilter`/`SpecialDaysToggle`/`BioToggle`/`SortToggle` row components
  were **retired** (absorbed by the sheet). **The pure pipeline lives in `dealFilters.ts`**
  (presentChains/chainCounts/compareOffers/filterDeals/buildSections, unit-tested) and the screen
  memoizes it — don't re-inline derived filtering into the render body.
- **"My Categories" home — a personalized landing view** (2026-07-17, `dealFilters.ts`
  `buildMineSections` + `components/{CategoriesModal,CategorySectionHeader}.tsx`): pick the categories
  you shop and land on a home of just those, each a **preview shelf** (header + top ~5 deals + a
  `See all ›` that drills into the full category). The current **All** view is kept. The `★ Mine`
  chip + a **pencil** edit chip live in the existing `CategoryChips` row — deliberately **no header
  change** (it's full at 375pt). Persisted as an ordered `myCategories: string[]` (`storage.ts`,
  mirrors `hiddenStores`/`sortByCategory`): **empty = fall back to All** (a fresh install is never a
  blank Mine screen), a stale/renamed slug is inert (skipped when it has no offers), cleared by
  **"Reset all app data" only** (not the Filters-sheet Reset). **Default landing** = Mine when
  `myCategories` is non-empty, else All (`setMine(mc.length > 0)` on hydrate); `mine` is otherwise a
  session view toggle layered on top of the unchanged `selected` (All / one category). **Four render
  branches, in order**: search `q` → flat search list (global, bypasses Mine); `mine` → the shelves
  `SectionList`; `selected` → the existing product-grouped `SectionList`; else → the flat All
  `FlatList`. `buildMineSections(base, myCategories, labels, sortFor)` takes the `filterDeals` output
  with `selected:null, query:''` as its `base`, so every shelf inherits the SAME hidden/stores/
  E-center-dedupe/lens/special-days/bio/non-food filtering as the list and **can't drift**; each shelf
  sorts by that category's own default (`resolveSortMode` → €/kg for food) and `total` drives
  "See all N". In Mine the FilterBar sort summary reads **"Per category"** and the sheet's Sort
  section is hidden (`FilterSheet` `hideSort`) — there's no single sort to attach a pick to. `household`
  is excluded from the editor (non-food, gated by the Non-food toggle everywhere). Mobile-only/OTA.
- **"My Categories" BROWSER — the header button** (2026-07-17, `components/CategoriesBrowserModal.tsx`
  + `dealFilters.ts` `buildCategoryCards`): a second, dedicated surface next to the shelves home —
  every category as a wide card (name centred, "N deals", its **3 most-discounted** deals), tap a card
  to open that category. A **Mine / All** toggle (opens on Mine when `myCategories` is non-empty) and a
  **settings** button that opens the same `CategoriesModal` editor. `buildCategoryCards` shares the
  `filterDeals(selected:null, query:'')` base with `buildMineSections`, so cards, shelves and list can
  never disagree. **The fill rule matters**: only ~2 of 23 categories can fill "3 discounted" (measured:
  Butter 1, Eggs 0), so when fewer than 3 carry a discount the rest is topped up with the category's
  best by its own default sort (€/kg) — filled rows just render no badge. **`Compare stores` moved OUT
  of the header into this view**: a 7th header action computes to ~396px and overflows 375pt (38px
  buttons + 8px gaps + pin + padding = ~350px at six), so the git-compare icon became `grid-outline`
  "My Categories"; Compare is a text-labelled button in the browser (it's category-oriented anyway).
  **Three modal traps this surface hit, all now guarded** (add nothing here without re-reading them):
  (1) the editor is passed in as an `editor` prop and rendered INSIDE the browser's `AppModal` — a
  sibling would be refused by iOS and latch (PR #81); (2) **a nestable modal must use
  `animationType="fade"`, never `"slide"`** — measured on react-native-web, a nested slide-in never
  resolves its transform and the sheet parks fully off-screen (top = viewport + sheet height), which is
  why `CategoriesModal` is now fade like `FlyerModal`/`HistoryModal`; (3) leaving the browser must also
  close the editor (`leaveBrowser`), or it re-mounts at the root branch and covers whatever opened next
  — measured sitting on top of Compare. Compare→browser is a **replace**, sequenced on `onDismiss`
  (iOS) exactly like Compare→EdekaVs. Also: `mineBase` is deliberately **not** gated on "a category
  surface is open" — emptying it on close made the sheet flash "no categories have deals" for the whole
  dismiss animation.
- **E center's duplicates of EDEKA are hidden from the deals list** (2026-07-16,
  `dealFilters.ts` `dropEdekaCenterDuplicates`, always on, no toggle): E center is EDEKA's
  hypermarket format, so the flyers overlap hard — measured on a Berlin PLZ, **103 of E center's
  272 products are also at EDEKA and 98% of those are priced identically**, i.e. pure list noise.
  An E center offer is dropped only when a same-named EDEKA offer exists **and it is not cheaper**;
  a lower price isn't a duplicate but the better deal (Axe Duschgel: EDEKA 2,79 → E center **2,29**
  — note both may carry the same *Mit App* price, so compare the guaranteed `price_cents`, which is
  what the rule does). **That exception is what makes it safe to apply silently: a dropped offer is
  never cheaper than the EDEKA row that survives, so the filter can't remove a best price** —
  Basket totals and Compare cells are provably unaffected. Live: E center **272 → 170** (169
  exclusive + 1 cheaper), EDEKA untouched.
  **Position in `filterDeals` is load-bearing on both sides**: AFTER `filterByVisibleStores` (if
  EDEKA is hidden, suppression must switch off or the shared products vanish from the list
  entirely) and BEFORE the store lens (lensing to "Only E center" strips EDEKA from the set, which
  would disable the guard and bring every duplicate back in the view that most needs them gone).
  Both directions are pinned by tests. Matching reuses `edekaVs.ts`'s exported `normName` +
  `cheapestByName`, so the list and the EDEKA-vs-E-center page can never drift on what "the same
  product" means. **Display-only**: Compare/EdekaVs get the raw `offers` and still show the full
  overlap (that page's "Same item, different price" + "Only at E center 169" is where it lives);
  Basket/Recipes/History use `modalOffers` and are untouched. The **Filters sheet's pill counts now
  reflect this** (see `facetCounts` below) — E center reads *166*, not *272*. The **Stores modal**
  still shows whole-set `chainCounts` on purpose: it's the membership surface ("how many deals does
  this chain have"), where a number shrunk by a hidden store or an active search would be wrong.
  The **category chips** also stay whole-set — they come from the API's `/api/categories`.
- **The Basket suggests the sub-groups actually in this week's flyers** (2026-07-29,
  `BasketModal` "In this week's flyers"): the add-search used to be `GROCERY_CATALOG` alone — 79
  curated items, and its memo didn't even take `offers` as a dependency — so a product like
  **Kohlrabi could not be added at all**. It now also lists every distinct `offer.group` in
  `foodOffers` (~96/week), grouped by category, below the plan inside the ScrollView. **Both paths
  resolve through the one exported `basketResolve.ts` `subGroupItem(group, groupLabel)`**, so a
  chip-add and a swipe-add of the same product produce the SAME key and can never occupy two
  basket rows; `addCatalog` now calls the exported `toItem` too, killing the last inline copy.
  **Key off the backend slug, never `norm(label)`** — `product_group._slug` hyphenates
  ("Ganze Bohnen"→`ganze-bohnen`) while mobile `norm` keeps spaces, and coffee ships that exact
  group today. De-dupe is against **basket keys ∪ the catalog chips above** (a live "Pilz"
  resolves to the catalog `mushroom`, so without it you get two chips), and a catalog hit wins
  over a synthesized `grp:` item because it brings its `exclude` guards. `addFromText` consults
  the live groups before minting a `free:` item — typing "Kohlrabi" used to give `free:kohlrabi`
  beside a swiped `grp:kohlrabi`. **`MAX_LIVE_CHIPS` is a runaway guard (400), not a display
  budget**: it was 30 and that was a bug — the list is ordered by category name, so 30 slots went
  to Bakery→Fish and Fruits/Vegetables fell off the end. Any cap small enough to bite truncates
  alphabetically. Pinned by a test spanning 11 categories; unit fixtures with one category each
  cannot catch it (web QA did). The `liveGroups` memo depends on **`foodOffers` only** — it walks
  ~1600 offers, so adding `text` to its deps would re-run it per keystroke.
- **Swipe-to-basket is NATIVE (runtime 1.1.0)**: `SwipeableOfferCard` wraps `OfferCard` in
  gesture-handler's built-in `Swipeable` (NOT ReanimatedSwipeable — deliberately no reanimated/
  worklets dep); left-swipe adds the offer's sub-category via the pure resolver
  `basketResolve.ts` (`resolveBasketItem`: offer.group → catalog item, else synth `grp:` item,
  else name reverse-match — swipe-add ≡ the Basket "+" add). `react-native-gesture-handler` +
  `expo-haptics` are **native deps** → `app.json` version bumped 1.0.0→**1.1.0** (new
  `runtimeVersion`), so OTAs target the 1.1.0 TestFlight build; a future native dep needs the
  same bump + `eas build`/`submit` (user-run). `GestureHandlerRootView` wraps App.tsx.
  **Gesture callbacks must stay pure** (2026-07-03 freeze fix): setState inside
  `onSwipeableOpen` re-renders the rows mid-gesture and can leave the pan stuck "active" —
  gesture-handler's root then eats EVERY touch (app-wide freeze, no tap/scroll; kill+relaunch
  clears it). The card closes first and defers `onAdd`/haptics via `requestAnimationFrame`;
  rows are memoized and DealsScreen's `onAddToBasket` reads the basket via a ref so its
  identity is stable — don't reintroduce `[basket]` deps or state writes in gesture handlers.
  **Modal freeze (2026-07-05):** RN `Modal` renders its content in a separate native root
  OUTSIDE App.tsx's `GestureHandlerRootView`, so **every modal uses `components/AppModal.tsx`**
  (a `<Modal>` wrapping its content in its OWN `<GestureHandlerRootView>`, per the RNGH docs) —
  never use RN `Modal` directly; a new modal MUST use `AppModal`. **But the freeze rationale
  recorded here was WRONG for iOS, and was corrected on 2026-07-17 by reading the installed
  source**: `GestureHandlerRootView` ships only `.android.tsx` + `.web.tsx` variants, so on iOS
  it falls through to the generic one — a **plain `View`** — and `RNGestureHandlerRootViewCls()`
  returns `nil` (`apple/RNGestureHandlerRootViewComponentView.mm`: *"RNGestureHandlerRootView is
  Android-only"*). **On iOS `AppModal`'s wrapper creates nothing native**, so it cannot have
  fixed an iOS freeze by that mechanism. Keep `AppModal` (load-bearing on Android + the
  dev-time context assert) but **don't reach for this as the explanation** for a future iOS
  freeze — the real cause of the original TestFlight freeze is still unidentified.
- **NEVER render a `<Modal>` as a SIBLING of a modal it can be opened from — nest it inside**
  (2026-07-17, measured on a simulator). RN presents a Modal from **`[self reactViewController]`**
  (`RCTModalHostViewComponentView.mm:154`) — the *first* view controller up the responder chain,
  **not** `RCTPresentedViewController()` — so two sibling modals resolve to the **same root VC**
  and iOS refuses the second. Measured, deterministically: `Attempt to present
  <RCTFabricModalHostViewController> on <EXRootViewController> which is already presenting
  <RCTFabricModalHostViewController>`. Worse, RN sets **`_isPresented = YES` *before* the present
  and never rolls it back on failure** (`:173`), and the `!_isPresented` guard (`:167`) means it
  can **never retry** — so the detail stays dead until `visible` goes false again. In this app
  `active` only clears via the detail's own (unreachable) Close, so **one tap from a sheet killed
  every later deal tap, from anywhere, for the whole session** — the "it worked the first time,
  now nothing opens" report. This hit **Likes (now History), Compare AND EdekaVs** (all three did
  `onOpenOffer={setActive}` with `FlyerModal` as a sibling) and was invisible to web QA, which
  has no VC presentation stack. Fix: `DealsScreen` builds **one** `FlyerModal` element and passes
  it as a `detail` prop into whichever sheet is open (`{likesModal ? detail : null}`), rendering
  it INSIDE that sheet's `AppModal`; children mount into the sheet's VC view
  (`mountChildComponentView`), so it presents from the sheet's VC — which is presenting nothing —
  and stacks correctly. Sheets are mutually exclusive (their triggers sit under any open sheet);
  `{!sheetOpen ? detail : null}` covers the deals-list path, and each sheet's `onClose` clears
  `active` so the element can't change host mid-flight. A **"replace" handoff is the same trap**:
  Compare → EdekaVs swapped both in one commit, presenting while the root VC was still dismissing
  → now chained on Compare's `onDismiss` (**iOS-only**; web has no VC stack and never fires it, so
  web switches immediately). Pinned by `DealsScreen.test.tsx` ("renders the deal detail INSIDE the
  History sheet") — sabotage-proved: rendering it as a sibling fails the test.
- **"Hide" a deal — the deal detail's Hide/Un-Hide button** (2026-07-17, `hidden.ts` + a `Hidden
  deals` section in the FilterSheet): dismisses a deal you're not interested in. Scope was the
  user's call: **this chain's copy, this flyer week** — hiding Edeka's Schnaps leaves Lidl's alone,
  and it returns when the flyers refresh. **NOT keyed on `offer.id`, deliberately**: `/api/reset`
  does `delete(Offer)` + re-scrape and Render's SQLite is ephemeral, so rowids are reused — an
  id-keyed hide would un-hide itself *and* silently hide a different product after any cold start.
  Identity is `` `${chain}:${normName(name)}` `` (reuses `edekaVs`' normName) and the week expiry
  reuses **`format.ts` `dealsStale(hiddenAt)`** — one weekly rule, not a second one. `activeHidden`
  is the single expiry gate every read goes through; expired entries are pruned on write.
  **Hidden applies EVERYWHERE** (deals list, Basket, Recipes, Compare, EdekaVs — they take
  `notHidden`, not the raw set) with **one deliberate exception: the History page**, which keeps
  the unfiltered set — History is a record you built by shopping, so a hidden entry would render "Not on
  sale this week", a lie. In `filterDeals` the hide step runs **first, before the E-center dedupe**:
  hiding EDEKA's copy then surfaces E center's twin instead of losing the product from both (pinned
  by a test). **Pressing Hide CLOSES the deal detail** (2026-07-17): hiding is a dismissal, so one press finishes it — `onToggleHidden` clears `active` when the result is hidden. Un-Hide deliberately does NOT close (it *restores* the deal; you may want to read it) and just flips the button back. Side effect: the `Hidden X` toast renders *under* the detail and was never seen — with the sheet closed it's finally the confirmation.
  Un-hiding is only reachable via the FilterSheet's **"Show hidden (N)"** lens (session-
  only, `showHidden`, guarded `&& hiddenKeys.size > 0`, and disarmed when the last hide goes so a
  later hide can't silently flip the list into only-hidden mode). The sheet's **Reset clears the
  lens, not the hidden set** (a persisted choice, like `hiddenStores`/`sortByCategory`); only
  "Reset all app data" clears `hiddenItems`.
- **History = what you've added to your basket; swipe-RIGHT hides** (2026-07-29, replaced the
  "Likes" feature — `history.ts` + `HistoryModal` + the clock header icon). Adding a deal to the
  basket (swipe-LEFT, or the deal detail's Basket button) records the **exact product** and what
  you paid; the History page re-matches it against the loaded offers each session so you can see
  what it costs now. **APPEND-ONLY** — removing it from the basket doesn't erase it; the page's ✕ is
  the only prune. `HistoryItem`: `key = normName(name)` + brand + group + an added-at price/chain
  memo — **never `offer.id`**, ids churn weekly.
  **Match tiers** (pure `matchHistory`, exclusive, unchanged from Likes): (1) exact `normName`
  equality (reuses `edekaVs.ts`'s exported `normName` — case/punctuation-insensitive, umlauts
  significant, cross-chain), cheapest first; (2) the **brand's** other products when the flyer
  renamed/rotated it ("McCain Golden Longs" → "Golden Long"), brand matched by normName equality OR
  token containment (brand words ⊆ name words; tokens NOT substrings, so `ja!`→"ja" can't fire
  mid-word), ranked by shared-name-token count then price, capped at 8; (3) product **group** for
  brandless items (18% of offers; "Rispentomaten"→ other Tomaten). The **clock badge = entries with
  an exact match on sale now** (`onSaleCount`), not the list size — hides at 0.
  **The History write sits BEFORE the basket de-dupe** in `onAddToBasket`, deliberately: the basket
  key is coarse (two different melons collapse to `melon`) while History keeps the specific product,
  so a second product in an already-basketed sub-category must still be recorded. That line is
  **unreachable from any non-gesture route** — the detail's Basket button is `disabled` once the
  sub-category is in the basket — so jest can't cover it (moving the call passes the whole suite);
  proven instead by web QA, where two Zott yoghurts collapsed to one `yogurt` basket key while
  History kept both.
  **Storage keeps the wire key `'likedItems'`** (same shape, so a rename would only cost a
  migration), but the fields moved `likedPriceCents`/`likedAt` → `addedPriceCents`/`addedAt`.
  `getStoredHistory` **reads either spelling and `setStoredHistory` writes both** for now: the old
  build's shape filter *required* `likedAt`, so writing new-only names would make an **OTA rollback
  silently drop every entry**. Drop the mirror a release or two out.
  - **Each row carries a PRICE TRAIL from the `grocery-price-history` collector** (2026-07-30,
    `priceHistory.ts` + `usePriceHistory.ts` + `components/PriceTrail.tsx`). Read straight from
    `raw.githubusercontent.com/.../data/**index-min.json**` — the collector's `weeks_seen >= 2`
    file, **65 KB over the wire** (389 KB raw) against ~550 KB for the full `index.json`, with
    `access-control-allow-origin: *`. Switched 2026-08-11.
    - **The switch needed a cache discriminator, and that is why upstream published a SECOND
      file rather than replacing the first.** A cached projection carries `misses` and an
      `etag`, and both answer a question the new file asks differently: `misses` used to mean
      "the collector has never seen this", it now means "never seen OR seen once and withheld".
      A device reusing a pre-switch projection would keep answering under the old policy and —
      because `unknownKeys()` then reports nothing missing — **would never even ask**.
      `CACHE_SOURCE` + the exported pure `usableCache()` drop it instead. Bump `CACHE_SOURCE`
      in the same commit as any `INDEX_URL` change.
    - **`MAX_INDEX_BYTES` is 400 KB, not 2.5 MB.** The old ceiling was sized against the full
      index; against the filtered one it was ~38x the real body, i.e. a tripwire the thing it
      guarded could no longer reach. Its test derives both bounds from the measured 65 KB
      rather than restating a literal.
    - **It is TIERED BY EVIDENCE because 93.75% of the collector's 6,588 products have exactly
      ONE data point** (≥2 weeks: 6.25%, ≥3: 0.76%). **Tier 0 renders `null`** — no "no history
      yet" line, no empty chart. A placeholder on 94% of rows reads as a broken feature; the row
      is already complete without it (paid-vs-now is local). Tier 1 states the single sighting,
      tier 2 a signed delta, tier 3 stats + an 8-bar sparkline built from plain Views (no new dep).
    - **Two suppressions, both measured.** `max/min >= 4` = a collapsed `name_key` (dm-style pack
      variants: `edeka_center "coca cola"` runs 399·69·149·1169·799 — can vs bottle vs crate, 29 of
      the 412 multi-week products) → drop the stats, keep the shape, say why. And `min == max`
      renders "always X", because "low X · usual X" is a tautology dressed as insight.
    - **Only the PROJECTION is persisted, never the index** (2.76 MB decompressed → ~20 KB for 100
      items), and **`misses` are mandatory**: without them "absent" is indistinguishable from
      "never looked up" and 94% of rows refetch forever. A **304 does NOT prove a NEW key is
      absent** — the projection discarded everything it wasn't asked for — so `If-None-Match` is
      sent only when every current key is already accounted for. The ETag is **per content
      encoding** (`W/"…"` gzip vs `"…"` plain), so hand-testing with curl and no `--compressed`
      returns a full 200 and looks like the server ignoring the header.
    - **The PLZ falls back to `DEFAULT_PLZ` (now in `src/config.ts`), not to `''`.** The stored PLZ
      is only written when the user *changes* it, so `null` is the normal first-run state — reading
      it as uncovered silently disabled the whole feature while every unit test passed.
  Gesture wiring: legacy `Swipeable`'s `onSwipeableOpen` direction names the **panel side** —
  'left' panel = right-swipe = **Hide**, 'right' panel = left-swipe = basket — routed through the
  exported `handleSwipeableOpen` seam (SwipeableOfferCard.tsx), which is unit-testable since the
  native pan can't run under jest; it follows the freeze contract (close first, rAF-defer, and
  DealsScreen's writers read via `historyRef`/`basketRef` so the memoized rows keep stable props).
  History matches against `historyOffers` (hidden STORES excluded, hidden DEALS deliberately not —
  it's a record you built by shopping, so a hidden+recorded product would read "Not on sale this
  week", a lie) and deliberately does NOT copy BasketModal's drop-household filter (equality
  matching has no keyword traps). `tint.history` (pink) is its colour; `tint.hide` is the calmest
  tint in the file on purpose — hiding is a dismissal, not an achievement.
- **On-card basket marker** (2026-07-20, narrowed 2026-07-29): a small cart (`tint.basket` green)
  in `OfferCard`'s tag row, shown **only** when the product is in the basket — so a glance answers
  "have I got this?" without opening the flyer. The heart (liked) marker went with the Likes
  feature, and History deliberately gets **no** card marker: it's auto-populated from every basket
  add, so the badge would end up on most rows and stop meaning anything. Icon-only to stay calm next
  to the chain/Bio/day pills; the status is folded into the card's **spoken** label (the Pressable
  is the accessible element, so the marker's own label isn't separately focusable). **The lists MUST
  pass `extraData`** — RN `VirtualizedList` cells are PureComponent-like and `data` is referentially
  unchanged on an add, so without it a fresh marker never appears. **jest can't guard `extraData`**
  (it re-renders eagerly, no virtualization — a removed-`extraData` sabotage still passes); the
  live-update path is proven by web QA on react-native-web instead.
- **The header shows ONLY the location pin — no PLZ text** (2026-07-16): six 38px icon actions plus a
  text block don't fit a phone. Adding the 6th (then Likes, now History) collapsed the location control 122px → 76px
  and rendered "PLZ 10713" as **"P…"** at both 375 and 390pt (i.e. most iPhones, not just the SE).
  The chains subline ("Lidl · REWE · …") went with it. **The code is not lost**: the pin opens
  `PlzModal`, which shows it, and the pin's `accessibilityLabel` is
  `` `Change postal code, currently ${plz}` `` — so it stays ANNOUNCED to screen readers and the
  visual removal isn't an a11y regression (a test pins that label; sabotaging it fails). Don't
  re-add text here without re-measuring at 375pt. Removing the subtitle also retired the `chainsSub`
  derivation and the `storeName` **state** (the cache field + its write stay — `revalidate` uses a
  local); `PlzModal` still passes a store name to `onApplied`, which now ignores it.
- **The deal detail carries button counterparts of both swipes** (`FlyerModal`): a swipe is
  unreachable for screen-reader/keyboard users, and **Like had no non-gesture entry point at all**.
  So `FlyerModal` takes `onLike`/`onAddToBasket` + `liked`/`inBasket` and renders **Like** and
  **Basket** buttons (DealsScreen is its single render site and reuses the *existing* stable
  `onLikeOffer`/`onAddToBasket`, so there's no second copy of the dedupe rules). **Add-only and
  `disabled` once added** — `Liked ✓` / `In basket ✓` — so the control is never inert-looking;
  removal stays on the History/Basket pages. Note the DealsScreen toast renders *under* this modal, so
  **the button's state flip is the feedback**, not a toast. `likes.ts` exports `likeKey(offer)` +
  `isLiked(offer, likes)` — use those for the check, never `resolveLike` (it stamps `Date.now()`).
- **Deployment**: backend is live on **Render** (free tier) at
  `https://grocery-helper-sw6c.onrender.com` via the IaC `render.yaml` Blueprint
  (Docker, `backend/Dockerfile`, binds `$PORT`, `/health` check). Render free tier
  **sleeps after ~15 min idle** → cold start re-runs the boot scrape (slow first
  request) and its SQLite is **ephemeral**, so startup `alembic upgrade head` rebuilds
  the schema from migrations every deploy — meaning **new `Offer` columns auto-apply on
  Render** (the migration runs there) while local dev applies them via the same upgrade
  (or a `grocery.db` recreate) + re-scrape. iOS /
  TestFlight config: `mobile/eas.json` (production profile; `EXPO_PUBLIC_API_URL` →
  the Render URL) + `mobile/app.json` (`ios.bundleIdentifier` `com.groceryhelper.berlin`,
  EAS project `@mhassan0600/grocery-helper`, `extra.eas.projectId`). `eas
  login`/`build`/`submit` are **user-run** (their Apple/Expo creds + build credits).
- **Deals are cached client-side** (`mobile/src/storage.ts` `dealsCache` — **one key per vertical**
  since 2026-07-30, see the verticals note above; still one PLZ each +
  `DealsScreen`): the app shows the last good offers/cats/storeName for the PLZ
  **instantly**. **Flyers are weekly, so the cache is authoritative for the week**: a fresh
  cache (not past the cached week's Sunday) is served with **no backend call at all** — the
  app only fetches when there's no cache or the cache is stale, or on pull-to-refresh. So
  Render free-tier cold starts don't block the UI, the app works offline, and a typical
  mid-week open never touches the backend. Only the **last** PLZ is cached
  (one key, ~1 MB cap). Staleness = past the cached week's **Sunday** (`format.ts`
  `dealsStale`, the weekly flyer expiry), surfaced with a "may be expired" banner by
  `components/UpdateStatus.tsx`; a failed refresh keeps the cached list (no error screen).
  The full-screen spinner only shows on a true cold start (no cache for that PLZ).
  **Cold-start gotcha**: Render's ephemeral DB only boot-scrapes `DEFAULT_PLZ`, so
  `/api/offers` returns **`[]` for any other (unscraped) PLZ** until a scrape runs.
  `DealsScreen` `revalidate` therefore **scrapes on demand when the read is empty** (like
  `PlzModal` does via `api.scrape`) then refetches, and — critically — **never caches or
  displays an empty result over good data** (an empty cold-backend refresh used to wipe
  the deals + poison the cache). Fetches have AbortController timeouts (30s reads / 120s
  scrape) so a cold start fails fast, and **`api.ts` `request` retries a cold-start-shaped
  failure** (timeout / network error / 5xx — never a 4xx, gated by the exported `isRetryable`;
  reads retry twice, writes once) so a waking/redeploying free-tier backend self-recovers
  instead of erroring. While a slow load runs, `PlzModal` and the `DealsScreen` cold-start
  spinner show a "waking the server up…" hint (after 4–5s), and the cold-start error is
  friendlier + offers a **Try again** button (revalidate) instead of "Could not load deals".
- **Options view** (`mobile/src/components/OptionsModal.tsx`, ⚙ in the header): maintenance
  actions split **device** vs **server**. Device — *Clear cached deals & reload* (drops
  `dealsCache` then forces `revalidate(true)`, the fix for "deals won't update mid-week"
  since the weekly cache otherwise skips the backend) and *Reset all app data*
  (`storage.clearAllData` → `multiRemove` every key **except the PLZ** + resets state to
  defaults, but **keeps the user's location** — a data reset shouldn't relocate them, so
  `onResetAll` just `revalidate(true)`s the current PLZ instead of jumping to `DEFAULT_PLZ`).
  Server — *Re-scrape* (`api.scrape`, upsert) and *Wipe & re-scrape* (`api.resetDb` →
  **`POST /api/reset`**). Destructive actions use an **inline two-tap confirm** (not
  `Alert.alert`, which drops its buttons on react-native-web). `POST /api/reset` deletes
  **all** offers then re-scrapes one PLZ (unlike `/api/scrape`'s in-place upsert, so it also
  clears stale rows the scrape no longer touches). **Admin guard (2026-07-03)**: `/api/reset`
  AND `/api/recategorize` require **`ADMIN_TOKEN`** *when that env is set* (else open for local
  dev) — sent as an **`X-Admin-Token` header** (query `token` is a deprecated fallback;
  headers stay out of access logs), compared timing-safe, failures logged with the client
  host. The app sends `EXPO_PUBLIC_ADMIN_TOKEN` if present (local `mobile/.env`; OTA bundles
  get it from the `EXPO_PUBLIC_ADMIN_TOKEN` GH secret injected in `eas-update.yml`).
  **`/api/scrape` stays tokenless but throttled**: a PLZ that already has offers re-scrapes at
  most once/10 min + a global 15s min-gap (skip → `scraped=0, skipped=true`); an **empty PLZ
  always scrapes** so the app's cold-start on-demand path never blocks. **Validity filters use
  `berlin_today()`** (`app/validity.py`), not server-local `date.today()` — Render runs UTC.
  The wipe self-heals via the immediate re-scrape but comes back sparse on a
  sample-fallback (re-run when the source is reachable).
- **AI Recipes are offline-authored, OTA-shipped — NO runtime LLM/API** (`mobile/src/data/
  recipes.ts` + `RecipesModal`, "Recipes" header button). Deliberate per the user: no
  `ANTHROPIC_API_KEY`, no Render call, no `/api/*` endpoint. Recipes are authored **ahead of
  time by Claude Code** (the agent — not a metered key) from the current `grocery.db` deals +
  the always-have staples, bundled in the app, and shipped via the `eas-update.yml` OTA push.
  At runtime the app is fully offline: `mobile/src/recipes.ts` `resolveRecipe`/`filterRecipes`
  **reuse the Basket matcher** (`basket.ts` `bestMatch`) to tag each ingredient on-sale (matched
  an offer → live chain pill + price) / have (`staple:true` or in the user's always-have list)
  / buy, and filter by diet/cuisine/**shop-at**/servings/only-on-sale/cheapest-€/kg.
  **"Shop at" — one store, or a mix of two** (2026-07-18, `RecipePrefs.stores`, persisted in the
  existing `recipePrefs`): a chip row (`Any store` + one per **present** chain, drawn from `offers`
  which is already `hiddenStores`-filtered) scoping the whole screen. `filterRecipes` narrows the
  offer pool **before** `resolveRecipe`, so an ingredient on sale elsewhere reads as `buy` — what
  you'd actually do — while a staple still falls to `have` (it never constrains where a recipe is
  shoppable), which makes the existing "Only on-sale" toggle mean "only what I can fully shop here"
  for free. **Capped at 2** (`MAX_RECIPE_STORES`); a third pick **replaces the oldest** rather than
  being ignored, so the chip is never a dead tap. Stale picks self-clear via `activeRecipeStores`
  (the only-when-present guard `filterDeals` uses for its store lens): a chain with no offers loaded
  is a **no-op, not an empty screen**. Each card badges `recipeChains(rr)` — "1 store · Lidl" /
  "2 stores · Lidl REWE" — computed from the **live** match, never an authored tag, and it
  **skips staples** (you don't make a trip for salt you own; without that guard 6 of 15 recipes
  named a store only a staple had matched — `salz` hits salted peanuts, `butter` hits a
  Schweinefleisch-Spieß *Butter*fly). The badge shows in **Any** mode too — "how many shops is
  this?" is worth knowing before you pick one. **An on-sale ingredient row
  opens that deal's `FlyerModal`** (2026-07-17): the row was inert while every other surface showing a
  matched offer opened the detail. Only on-sale rows are pressable — `resolveRecipe` sets
  `offer: role === 'on_sale' ? offer : null`, so "have"/"buy" rows have no deal to open — and the
  **WHOLE row** is the tap target, not the price block (the Likes sheet shipped with exactly that dead
  target: tapping the product name did nothing, fixed in #81). The detail is passed in as a **`detail`
  prop rendered INSIDE `RecipesModal`'s `AppModal`** (the PR #81 nesting rule — a sibling is refused by
  iOS and latches), `recipesModal` is part of `sheetOpen`, and `closeRecipes` clears `active` so the
  element can't change host mid-flight. `RecipesModal` must stay `animationType="fade"` — it now hosts
  a nested modal, and a nested slide never resolves its transform on react-native-web (PR #89). Its
  Close is labelled **"Close recipes"** because the nested detail carries its own "Close".
  **The Basket's per-item picker splits the row into two targets, and the CARD OPENS THE DEAL**
  (inverted 2026-07-31, at the user's request): a card press means the same thing on every surface
  in this app — show me this deal — so the picker no longer overloads it. Each row is
  `[OfferCard (flex 1, opens the flyer)] [✓ button (picks it for the plan)]`, two non-overlapping
  targets (measured at 375pt: card ends x=318, button 32×44 at x=330–362). The icon is
  `checkmark-circle-outline`, **not** a `chevron-forward`: a forward-chevron reads as "go there",
  which is exactly the mislabel this swap fixes. `OfferCard`'s optional `accessibilityLabel` stays
  (generic mechanism) but the picker no longer passes one — the default `"Open deal for …"` is now
  the truth there; the ✓ carries `"Use X in your plan"`. **Picking still closes the picker**, which
  is the only pick feedback (no ✓-selected state on the row) — and it's what makes a leak between
  the two targets observable in a test. Same nesting rules as Recipes: a
  `detail` prop inside `BasketModal`'s `AppModal`, `basketModal` in `sheetOpen`, `closeBasket` clears
  `active`, stays `fade`, Close labelled **"Close basket"**.
  Always-have is seeded
  from `catalog.ts` staples (`storage.ts` `defaultAlwaysHave` / `STAPLE_KEYS`), editable +
  persisted (`alwaysHave` key; `recipePrefs` for filters). **Regenerate weekly** when flyers
  refresh — **automated locally** via `scripts/regenerate-recipes.sh` (scrape → `recipe_seed`
  candidate dump → **headless `claude -p`** rewrites `recipes.ts` → `tsc`/`lint` → commit + push
  to main → OTA), scheduled by `scripts/com.groceryhelper.recipes.plist` (launchd, Sundays). It's
  **local, not CI**, because the keyless design uses your logged-in Claude Code (`claude -p`), not
  a managed `ANTHROPIC_API_KEY`. The deterministic prereqs: `app/scripts/scrape.py`
  (wraps `run_scrapers`) refreshes `grocery.db`; `app/scripts/recipe_seed.py` dumps candidates.
  - **NEVER couple a test to the CONTENT of `mobile/src/data/recipes.ts`.** That file is
    rewritten every Sunday from whatever is on sale, so any assertion naming an ingredient is
    a time bomb: on 2026-07-30 the first regen in two weeks turned `main` red because four
    `DealsScreen.test.tsx` cases were pinned to "Gouda" — and they exist to guard the iOS
    modal-NESTING invariant, which has nothing to do with cheese. Mock `../data/recipes` with
    a fixed fixture (one matchable ingredient + one staple) as that file now does. The CI
    failure also *looks* like two problems — the coverage ratchet reports a miss too — but a
    failed suite contributes no coverage, so fixing the tests restores it; never lower it.
  - **That `claude -p` auth is the schedule's single point of failure, and it broke silently
    for 11 days** (2026-07-26 → 2026-07-30): launchd fired, the scrape and dump succeeded, then
    `claude -p` returned "Not logged in", `set -e` aborted, and *nothing said so*. Fixed by
    **preflighting auth before the scrape** (a failed probe now costs one tiny call instead of
    ~15 requests to the flyer publishers) and by three failure channels — a `.recipe-regen.status`
    file (a local write, so it can't fail), a macOS notification, and a deduplicated
    `recipe-failure` GitHub issue that closes itself on recovery. The issue is deliberately
    **last**: `gh` authenticates via the keyring, the same class of thing that broke here.
    **`./scripts/regenerate-recipes.sh --check`** reports the last outcome and exits non-zero on
    failure. It is NOT a keychain-ACL problem — the item reads fine non-interactively; the stored
    credential itself goes stale, and a desktop-app session keeps working because it uses
    host-provided auth, which is why the breakage is invisible from inside one. See
    `docs/recipes.md`.
  **Recipes are authored PER CHAIN** (2026-07-18): `recipe_seed.py` emits
  `{plz, by_chain: {chain: {category: [...]}}}` and deliberately has **no** flat
  "cheapest anywhere" view — authoring from one picks the globally cheapest item per category and
  scatters the ingredients across four shops *by construction*, which is why the pre-change bundle
  measured **7/10 fully shoppable across all five chains but only 3/10 at the best single chain**
  (E center: 1). The brief (`scripts/recipe-prompt.md`, the single source of truth the automation
  feeds `claude -p`) is ~15 recipes: **2 per chain** whose every non-staple ingredient matches a
  name in *that chain's own* list, plus **5 two-store** pairs. Verify **per chain**, not globally;
  acceptance is **every chain ≥2 recipes fully shoppable alone** (currently 3–5 each).
  A recipe carries **no store field** — see the "Shop at" note above for why. The dump also filters
  `valid_to >= berlin_today()`: the DB accumulates flyer weeks (a scrape upserts, it doesn't wipe),
  and an unfiltered dump fed the authoring step **1580 expired offers alongside 1763 live ones**,
  which its own verification couldn't see because it read the same stale list.
  Full workflow + launchd install + gotchas (git-push-under-launchd, PATH/fnm) in `docs/recipes.md`.
- **CI/CD is GitHub Actions** (`.github/workflows/`): `ci.yml` (backend
  `ruff`+`pytest --cov`+`alembic upgrade head`/`alembic check`, mobile
  ESLint+`tsc`+`jest`, backend Docker build; on green `main` pushes a `deploy` job curls
  the Render deploy hook **only when the merge touched a *runtime* `backend/**` file or
  `render.yaml`** — a `git diff HEAD~1 HEAD` gate (fetch-depth 2) that **excludes lint/test/
  example files not in the image** (`ruff.toml`, `pytest.ini`, `.env.example`, `tests/`; the
  Dockerfile COPYs only `app/`+`alembic/`+`requirements.txt`) via a **denylist** — a *new*
  runtime file still deploys (err toward deploying: a missed deploy ships stale code, an extra
  one just re-scrapes the ephemeral DB), and a mixed `app/`+`tests/` change still deploys. So
  mobile-only / docs / lint-only merges don't redeploy Render and wipe its ephemeral DB; the
  *same* filter idea as eas-update's `mobile/**` gate, inverted). **The deploy job then verifies the OUTCOME, not the trigger** (2026-07-15): `/health`
  exposes the running commit (`RENDER_GIT_COMMIT`), the job polls it until the merged SHA is
  actually live (~15 min bound; a newer deploy superseding mid-poll stands down with a warning),
  then asserts `/api/offers` serves >0 offers — a red here means the boot-scrape failed even
  though the deploy "succeeded". `scrape.yml` additionally runs a **data-quality gate** after the
  Sunday reset (`.github/scripts/verify_deals.py`, offline-testable via `--file`; **covered by
  `backend/tests/test_verify_deals.py` since 2026-08-08** — it loads the script via
  `importlib.util.spec_from_file_location`, because ruff runs with `working-directory: backend`
  and pytest has `testpaths = tests`, so **nothing under `.github/scripts/` is linted or collected
  by default** and the gate had gone its whole life unproven): **chains ≥6** (was 5 until
  Penny landed 2026-08-11 — bump it with every chain, or a dark new chain reads green)
  (a missing chain pages even when the skip was a designed degradation — fail-closed must
  announce itself; the issue auto-closes on recovery), offers ≥800, €/kg-sortable ≥50%, "other"
  ≤15% (~2× the measured 7.4% norm — calibrating this gate corrected an earlier stale ~1%
  belief), and **self-disagreement ≤20% of comparable products** (the same product NAME served in
  two categories = ≥1 wrong row by construction; free to compute, no ground truth needed). The
  **denominator is load-bearing**: the served set is deduped, so only ~16% of offers share a name
  with any other — expressed against the served total the rate is ~2% and a "2× norm" ceiling
  wouldn't trip until a *quarter* of comparable products disagreed (a gate that reads authoritative
  while evaluating almost nothing). It's measured against **names served ≥2×** (11.9% live), skips
  (doesn't pass) below 20 comparable products, and names the offenders on failure. A gate failure
  flows into the existing alert-issue machinery unchanged. Thresholds live at the top of the script;
  recalibrate against measured norms, don't guess), `eas-update.yml` (OTA via `eas update --branch production`, **gated
  on a green CI run**: triggers via `workflow_run` *after* the `CI` workflow succeeds on `main`,
  not on raw push — so a broken bundle can't ship; `workflow_run` can't path-filter, so the job
  pins checkout to the passing commit's SHA and re-applies the `mobile/**` filter via `git diff
  HEAD~1 HEAD`, skipping backend-only commits), `scrape.yml` (**Sunday 06:00 UTC** cron → `POST /api/reset`
  — wipe + re-scrape, *not* upsert, so the prior week's stale offers are cleared; runs Sunday
  because flyers are Mon–Sat so they're spent by then and next week's are already discoverable,
  refreshing before the app's weekly cache expires past Sunday — retries 3× and opens/comments a
  `scrape-failure` issue on total failure; passes the `ADMIN_TOKEN` secret as an **`X-Admin-Token`
  header**, enforced once that env is also set on Render).
  **`ci.yml` must NEVER cancel an in-flight run on `main`** (2026-08-03, cost a week): the
  deploy job lives in this workflow, and `concurrency.cancel-in-progress: true` applies to
  pushes as well as PRs — so a docs commit pushed a minute after a backend merge **cancelled
  that merge's run and its deploy**. Nothing reported it: the merge commit carries a green tick
  from the SECOND run, a cancelled run renders grey rather than red, and the deploy job never
  existed to fail. It was found only by checking live data against merged code. Now gated:
  `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`, pinned by
  `backend/tests/test_workflows.py` (which also re-asserts the deploy job's `needs`).
  **`ci.yml` now carries a `workflow_dispatch` recovery hatch** (2026-08-04) with a
  `force_deploy` input that bypasses the path filter — needed because the *fix* for a broken
  deploy is normally a workflow or `tests/` change, both of which that filter excludes, so
  recovery otherwise meant inventing a backend commit. Passed via `env:`, never interpolated
  into the `run:` block. **Always check `/health`'s commit against `main`** after a backend
  merge; the check colour is not evidence (see below).
  **The deploy gate's "superseded by a newer deploy" branch must PROVE ancestry** (2026-08-04,
  cost a second lost deploy): it used to infer it from `live != want`, guarded only by a
  comparison against the pre-deploy commit. That probe is a 30s curl against a free tier that is
  usually **asleep** — it timed out, `before` was empty, the guard could not fire, and a Render
  build that never landed reported **green**, after which "verify the served deals" happily
  counted 1445 offers served by the *old* code. Now: `git merge-base --is-ancestor "$want"
  "$live"` — a genuinely newer deploy makes our commit an ancestor, a failed build does not.
  Needs no pre-deploy reading, and fails closed. Pinned by `test_workflows.py`.
  **All workflow actions are pinned to
  commit SHAs** (tag as trailing comment; Dependabot updates SHA pins) and `eas-version` is pinned
  (no `latest`) — bump deliberately, don't revert to floating tags. The committed launchd plist
  (`scripts/com.groceryhelper.recipes.plist`) is a **`/Users/CHANGE_ME` template** (install via the
  sed line in `docs/recipes.md`) — never commit a real home path.
  **Dependabot raises PRs for SECURITY updates ONLY** (2026-08-04, user's call): every entry in
  `dependabot.yml` carries `open-pull-requests-limit: 0`, which is GitHub's documented way to
  switch off version updates while leaving security updates untouched (they come from the repo's
  alerts + dependency graph, not from that file — proven by the npm CVE PRs that arrive with no
  npm entry present at all). **So a Dependabot PR now means "there is a CVE", nothing else.**
  Two traps, both pinned by `test_workflows.py`: re-raising the limit turns routine bumps back on,
  and adding **`target-branch`** to an entry *silently disables security updates* for that
  ecosystem. Actions stay listed because the `actions` ecosystem does carry advisories, so a
  vulnerable action still gets its SHA pin bumped. Mobile deps move via `npx expo install` during
  an SDK upgrade — the app is Expo SDK-pinned (react/react-native/expo-*/jest-expo lockstep) and
  per-package bumps break `npm ci` (react-native 0.86 vs jest-expo@56's RN 0.85 peer). And
  **`mobile/.npmrc` pins the public registry** so that security fetch doesn't abort on an
  auto-injected `npm.pkg.github.com` (don't delete it). Deploy + OTA + **Codecov upload**
  **skip gracefully** until their secrets exist (`RENDER_DEPLOY_HOOK_URL`, `EXPO_TOKEN`,
  `CODECOV_TOKEN`), so CI stays green; gated deploy assumes Render **auto-deploy is off**. Python is
  **3.12 everywhere** now — Dockerfile/Render, CI, AND the local dev venv (recreate with
  `/opt/homebrew/bin/python3.12 -m venv backend/.venv`); `backend/ruff.toml` targets **`py312`** to
  match (no `UP`/pyupgrade rule, so the target bump adds no churn). The `requirements.txt` floors
  (`fastapi>=0.138.1`, `uvicorn>=0.49.0`, `pytest>=9.1.1`) need **≥3.10**, so a **fresh** venv must
  be built on 3.12 — a 3.9 venv can't install them (only the old pre-bump 3.9 venv still ran).
  **Lint must pass** before a
  push: `ruff check .` + `npm run lint`; `react-hooks/set-state-in-effect` is intentionally
  a **warning** (legit modal fetch/reset effects), keep real errors at zero. OTA only
  reaches a build embedding `expo-updates` at the matching `runtimeVersion` (app.json
  `appVersion` policy) → bump `expo.version` when native deps change.
- **In-app OTA prompt** (`mobile/src/useOtaUpdates.ts`, called once in `App.tsx`): checks
  for an EAS Update on launch + on every app foreground and, if one is ready, downloads it
  and alerts the user to reload now (`Updates.reloadAsync`). Inert in dev / Expo Go / web
  (`__DEV__` / `Platform.OS` / `Updates.isEnabled` guards), best-effort, once per session.
  Only fires in a build embedding `expo-updates` at the matching `runtimeVersion`.
- **`docs/DECISIONS.md` is the design-fork log** (created 2026-08-09): when a decision with real
  alternatives gets made, record the fork, every option's tradeoff, what was chosen, a **status**
  per rejected option (`deferred — worth trying` / `rejected — <reason>`) and a **revisit hook**
  naming the seam where trying it later would plug in. The `deferred` ones are also listed in a
  **"Backlog — alternatives worth trying later"** block at the top of the file. Write the entry as
  the decision is made, not at wrap-up. Skip cosmetic forks. Sibling of `docs/learnings.md`, which
  holds teachable *concepts* rather than roads not taken.
- **Commits**: author as the user only — no `Co-Authored-By: Claude` trailer.
- **Branching — hybrid by blast radius** (solo dev): **branch + PR + squash-merge-on-green** for
  anything that ships or can break CI (backend/mobile code, migrations, **workflow/CI files**,
  Dockerfile); **direct to `main`** for zero-prod-impact docs/dev-tooling (README, `dev.sh`,
  CLAUDE.md). After landing, leave `main` checked out with the change pulled — don't strand on a
  deleted branch. I own the full path to `main` now: commit→push→PR→wait green→`gh pr merge
  --squash` (the user no longer merges manually).
- **`main` is protected by two rulesets** (GitHub, `gh api repos/.../rulesets`): *protect history*
  (`deletion` + `non_fast_forward`, **no bypass** — no force-push/delete) and *require green PR*
  (`required_linear_history` + `pull_request` 0-approvals squash-only + `required_status_checks`:
  Backend / Mobile / Backend image builds), the latter with **admin bypass** so direct docs pushes
  still work. "Deploy to Render" is **not** a required check (it only runs post-merge on `main`).
