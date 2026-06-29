Regenerate this week's bundled recipes for the Grocery Helper app. This is the offline
authoring step — no runtime API; you are Claude Code editing the repo directly.

Read first:
- `.recipe-candidates.json` (repo root) — this week's cheapest on-sale ingredients per
  cookable category: `{ category: [ { name, chain, price_cents, price_per_unit,
  discount_pct }, … ], … }`.
- `mobile/src/storage.ts` — the `STAPLE_KEYS` array (pantry items assumed on hand).
- `mobile/src/types.ts` — the `RecipesData` / `Recipe` / `RecipeIngredient` types.
- `docs/recipes.md` — the authoring conventions.
- `mobile/src/data/recipes.ts` — the current file, for the exact shape and header comment.

Then **rewrite `mobile/src/data/recipes.ts`** so it exports `RECIPES: RecipesData` with:
- `generatedFor: '10115'` and `generatedAt` = today's date (YYYY-MM-DD).
- ~10 varied recipes spanning diets (vegan / vegetarian / pescatarian / meat) and cuisines,
  across breakfast / lunch / dinner. `tags` = [diet, cuisine, meal].
- Each recipe built mainly around items present in `.recipe-candidates.json` so the app can
  price them. Do NOT invent ingredients that aren't broadly on sale or a common staple.
- Each ingredient: `label` (English), German `keywords` (lowercase stems that are substrings
  of the candidate offer names — derive them from the actual names), optional `qty`,
  `staple: true` for STAPLE_KEYS items (oil, salt, pepper, garlic, onion, flour, sugar, rice,
  pasta, eggs, milk, butter), and `exclude` guards where a keyword would mis-match (e.g.
  salmon vs "Lachs-Schinken-Art" → `exclude: ['vegan','schinken','aufschnitt']`).
- Keep the existing header comment block at the top of the file.

Before finishing, verify every non-staple ingredient's keywords match at least one name in
`.recipe-candidates.json`. Output ONLY by writing the file — do not run git or other shell
commands.
