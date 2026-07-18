Regenerate this week's bundled recipes for the Grocery Helper app. This is the offline
authoring step — no runtime API; you are Claude Code editing the repo directly.

Read first:
- `.recipe-candidates.json` (repo root) — this week's cheapest on-sale ingredients, **grouped by
  chain**: `{ "plz": "10115", "by_chain": { "<chain>": { "<category>": [ { name, chain,
  price_cents, price_per_unit, discount_pct }, … ], … }, … } }`.
- `mobile/src/storage.ts` — the `STAPLE_KEYS` array (pantry items assumed on hand).
- `mobile/src/types.ts` — the `RecipesData` / `Recipe` / `RecipeIngredient` types.
- `docs/recipes.md` — the authoring conventions.
- `mobile/src/data/recipes.ts` — the current file, for the exact shape and header comment.

## The rule that matters: author each recipe for ONE chain, or for exactly TWO

The app has a **"Shop at"** filter — a user can scope recipes to one store, or a mix of two. That
filter can only find recipes that were *built* that way. A recipe assembled from the cheapest item
in each category scatters its ingredients across four shops by construction and is unshoppable
under the filter; that is why the candidates are grouped by chain and why there is no flat
"cheapest anywhere" list to author from.

Write **~15 recipes**:
- **2 per chain** in `by_chain` — every **non-staple** ingredient's keywords must match at least one
  product name in **that chain's own lists**. Not "somewhere in the file": that chain.
- **5 two-store recipes**, each drawing from the union of exactly **two** chains' lists. Vary the
  pairs; don't use the same pair twice.
- If a PLZ yielded only one chain, write the per-chain recipes for it and skip the pairs.

**Do NOT add a store/chain field to a recipe.** The app re-matches every ingredient against the
user's live offers each session and derives the stores from that. An authored tag would be a claim
about *this* week's flyer that silently goes stale — the live match is the only truth.

## The rest of the shape

Rewrite `mobile/src/data/recipes.ts` so it exports `RECIPES: RecipesData` with:
- `generatedFor` = the `plz` value from `.recipe-candidates.json` (not a hardcoded one), and
  `generatedAt` = today's date (YYYY-MM-DD).
- Variety across the **whole set**, not within each recipe: diets (vegan / vegetarian /
  pescatarian / meat), cuisines, and breakfast / lunch / dinner should all be represented once the
  15 are taken together. `tags` = [diet, cuisine, meal].
- Each ingredient: `label` (English), German `keywords` (lowercase stems that are substrings of the
  candidate offer names — derive them from the actual names), optional `qty`, `staple: true` for
  STAPLE_KEYS items (oil, salt, pepper, garlic, onion, flour, sugar, rice, pasta, eggs, milk,
  butter), and `exclude` guards where a keyword would mis-match (e.g. salmon vs
  "Lachs-Schinken-Art" → `exclude: ['vegan','schinken','aufschnitt']`).
- Keep the existing header comment block at the top of the file.

A staple needs no chain: it is assumed on hand, so it never constrains where the recipe is
shoppable. Only non-staple ingredients have to come from the recipe's chain(s).

## Before finishing — verify per chain, not globally

For each single-store recipe, check every non-staple ingredient's keywords against **its own
chain's** lists and confirm a match; for each two-store recipe, against the union of its two. A
keyword that only matches under some *other* chain is a failure — fix the ingredient or pick a
different one. Output ONLY by writing the file — do not run git or other shell commands.
