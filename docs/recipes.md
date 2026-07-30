# AI Recipes — offline-authored, OTA-shipped

The **Recipes** screen suggests meals built from the week's on-sale items plus the user's
"always have" staples. It is **fully offline** and has **no runtime LLM/API call** — recipes
are authored *ahead of time* by Claude Code, bundled into the app, and shipped via OTA.

## How it works

```
backend/grocery.db (current deals)            mobile/src/data/recipes.ts (bundled)
        │  recipe_seed.py (read-only)                   │  imported by the app
        ▼                                               ▼
   on-sale candidates JSON  ──►  Claude Code authors recipes  ──►  RecipesModal renders +
   + always-have staples         (offline; the agent, not a          matches each ingredient
                                  metered ANTHROPIC_API_KEY)          to the user's offers
```

- **No `ANTHROPIC_API_KEY`, no Render call, no `/api/*` endpoint.** The cost/secret/cold-start
  of a runtime LLM call is avoided entirely — generation happens at authoring time.
- At runtime the app reads `mobile/src/data/recipes.ts` and uses the **Basket matcher**
  (`mobile/src/basket.ts`) to show each ingredient's live on-sale price/store from the deals
  already loaded on the device (`mobile/src/recipes.ts` `resolveRecipe`/`filterRecipes`).
- Ingredients are tagged **on sale** (matched an offer), **have** (a staple / in the user's
  always-have list, or `staple: true`), or **buy** (needs buying). Filters (dietary, cuisine,
  **shop at**, only-on-sale, cheapest €/kg, servings, count) run client-side over the static set.

## Recipes are authored PER CHAIN — one store, or exactly two

The app's **"Shop at"** filter scopes recipes to one store, or a mix of two. That filter can only
surface recipes that were *built* that way, so `recipe_seed.py` groups candidates **by chain** and
deliberately emits **no** flat "cheapest anywhere" list.

Authoring from a global list picks the cheapest item in each category, which lands the ingredients
in four different shops **by construction**. Measured 2026-07-18 on the 10 globally-authored
recipes then bundled (PLZ 10115, 1778 valid offers): **7 of 10** were fully shoppable using all
five chains, but only **3 of 10** at the best single chain (E center: 1), and the average number
of on-sale ingredients fell 5.3 → 3.5. Per-chain lists are what fix that.

**A recipe carries no store field.** The app re-matches every ingredient against the user's live
offers each session and derives the stores from that, so an authored tag would be a claim about one
particular week's flyer that quietly goes stale. Authoring supplies the *supply* — that
single-store recipes exist at all; the runtime decides what actually works this week.

Only **non-staple** ingredients constrain the store: a staple is assumed on hand.

## Regenerating recipes (weekly, when the flyers refresh)

Recipes reference *this week's* deals, so refresh them on the weekly cadence (the flyers
expire each Sunday). This is a Claude Code task — no API key:

1. Make sure the dev DB has the current week's deals:
   `cd backend && source .venv/bin/activate && python -m app.scripts.recipe_seed --plz 10115`
   (or re-scrape first: `POST /api/scrape?plz=10115`). The script prints
   `{plz, by_chain: {chain: {category: [candidates]}}}` — the cheapest on-sale products per
   cookable category, per chain.
2. Ask Claude Code to **rewrite `mobile/src/data/recipes.ts`** from that JSON + the always-have
   staples (`STAPLE_KEYS` in `mobile/src/storage.ts`) — the full brief lives in
   **`scripts/recipe-prompt.md`** (that file is what the automation feeds to `claude -p`, so keep
   it as the single source of truth rather than re-describing it here). In short: ~15 recipes —
   **2 per chain** whose every non-staple ingredient matches a name in *that chain's own* lists,
   plus **5 two-store** recipes drawing from exactly two chains — with a dietary/cuisine spread
   across the set, German match `keywords` (+ `exclude` guards for traps like tomato→ketchup), and
   `generatedFor` taken from the JSON's `plz`.
   **Verify per chain, not globally**: a keyword that only matches under some *other* chain is a
   failure. The acceptance check is that every chain has **≥2 recipes fully shoppable on its own**.

3. `cd mobile && npx tsc --noEmit && npm run lint`, then commit `mobile/src/data/recipes.ts`.
   The push triggers **`eas-update.yml`** → the new recipes reach devices over-the-air. The
   backend is never touched.

## Automating it (local, scheduled)

The weekly loop above is wrapped in **`scripts/regenerate-recipes.sh`**: it refreshes the local
DB (`python -m app.scripts.scrape --plz 10115`), dumps candidates (`recipe_seed`), has **headless
Claude Code** (`claude -p`, your local auth) rewrite `recipes.ts` per `scripts/recipe-prompt.md`,
validates `tsc`+`lint`, and commits + pushes to `main` (→ CI → OTA). It only pushes if the file
actually changed, and aborts before committing if the regenerated file doesn't build.

Run it manually any time:

```bash
./scripts/regenerate-recipes.sh            # PLZ defaults to 10115
```

Schedule it weekly with the bundled launchd agent (macOS):

```bash
# The committed plist is a template (paths use /Users/CHANGE_ME); fill in your home dir:
sed "s|/Users/CHANGE_ME|$HOME|g" scripts/com.groceryhelper.recipes.plist \
  > ~/Library/LaunchAgents/com.groceryhelper.recipes.plist
launchctl load ~/Library/LaunchAgents/com.groceryhelper.recipes.plist
launchctl start com.groceryhelper.recipes   # optional: run once now to test
```

Runs **Sundays 10:00 local**, logs to `.recipe-regen.log`. Notes / gotchas:
- **Keyless by design**: generation uses *your* logged-in Claude Code (`claude -p`), never an
  `ANTHROPIC_API_KEY` — so it stays local and can't run in CI (that's the whole point).
- **git push under launchd**: the schedule's environment may lack your ssh-agent/keychain, so the
  push can fail auth even though `git push` works in your terminal. Verify the script end-to-end
  manually first; ensure non-interactive git auth (HTTPS credential helper / `gh`).
- **PATH**: the plist points `claude`/`node` at this machine's paths (Homebrew + fnm); adjust if
  yours differ (`which claude`, `which node`). The script also re-resolves node via `fnm`.
- The Mac must be awake at the scheduled time; launchd runs a missed job once on next wake.

## When the schedule fails (it did, silently, for 11 days)

**2026-07-26 → 2026-07-30 the weekly job produced nothing and nobody knew.** launchd fired
on time and every deterministic step worked — `git pull`, a 1,638-offer scrape, a 100 KB
candidate dump — then `claude -p` printed `Not logged in · Please run /login` and exited 1,
so `set -euo pipefail` aborted. Failing closed was correct (no broken recipes shipped);
failing *quietly* was the bug, and recipes silently drifted two flyer weeks out of date.

The script now has three failure channels, ordered so the most reliable can't be skipped:

| channel | what it gives you | can it fail? |
|---|---|---|
| `.recipe-regen.status` | one line, `OK`/`FAILED` + reason + timestamp | no — a local write |
| macOS notification | immediate, if you're at the keyboard | best effort |
| GitHub issue, label `recipe-failure` | durable + deduplicated; mirrors `scrape.yml`'s `scrape-failure` machinery, and closes itself on the next healthy run | `gh` authenticates via the **keyring** — the same class of thing that broke here, so it is deliberately last |

Check the schedule's health without reading the log:

```bash
./scripts/regenerate-recipes.sh --check
```

It prints the last outcome and exits non-zero if that was a failure. (It is handled
*before* the `ERR` trap is armed — a check that correctly reports FAILED must not itself
raise a new alert.)

### Auth is preflighted before the scrape

`claude -p` is now probed *first*, before anything expensive. The scrape is ~30 s and ~15
requests to the flyer publishers; firing that burst when we already can't author anything
is both wasteful and impolite to sources we're trying to stay welcome at.

### If it says "not authenticated"

Run `claude` interactively and `/login`. Note what this is **not**: the keychain item is
readable non-interactively (verified — `security find-generic-password` exits 0), so this
is not a keychain-ACL or "background process can't unlock it" problem. The stored
credential itself went stale — its `mdat` is `20260726080036Z`, ~35 s into the failing
run, which is the CLI attempting a token refresh, failing, and writing itself out as
logged-out. A Claude Code session running inside the desktop app is unaffected, because
that uses host-provided auth rather than this keychain item — which is exactly why the
breakage was invisible from inside a working session.
