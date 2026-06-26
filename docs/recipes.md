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
  only-on-sale, cheapest €/kg, servings, count) run client-side over the static set.

## Regenerating recipes (weekly, when the flyers refresh)

Recipes reference *this week's* deals, so refresh them on the weekly cadence (the flyers
expire each Sunday). This is a Claude Code task — no API key:

1. Make sure the dev DB has the current week's deals:
   `cd backend && source .venv/bin/activate && python -m app.scripts.recipe_seed --plz 10713`
   (or re-scrape first: `POST /api/scrape?plz=10713`). The script prints the cheapest on-sale
   candidates per cookable category as JSON.
2. Ask Claude Code to **rewrite `mobile/src/data/recipes.ts`** from that JSON + the always-have
   staples (`STAPLE_KEYS` in `mobile/src/storage.ts`), keeping ~10 recipes with a dietary/cuisine
   spread, German match `keywords` (+ `exclude` guards for traps like tomato→ketchup), and
   `generatedFor`/`generatedAt` updated. Prompt outline:

   > Author ~10 varied recipes (vegetarian/vegan/pescatarian/meat; italian/german/etc.) that
   > combine the on-sale items below with common always-have staples. Output the typed
   > `RecipesData` for `mobile/src/data/recipes.ts`. Each ingredient needs German `keywords`
   > that match the offer names (so the app can price it), `qty`, and `staple: true` for
   > pantry items (oil, salt, garlic…). Steps: 2–4 lines. <paste recipe_seed.py JSON>

3. `cd mobile && npx tsc --noEmit && npm run lint`, then commit `mobile/src/data/recipes.ts`.
   The push triggers **`eas-update.yml`** → the new recipes reach devices over-the-air. The
   backend is never touched.

> A CI-automated `claude -p` generator is possible later, but it would need Claude Code auth
> in CI — kept out for now so there's **no managed key anywhere**.
