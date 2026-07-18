// Pure recipe helpers — no React/React-Native imports. Resolves each recipe ingredient
// against the user's currently-loaded offers (reusing the Basket matcher) so the Recipes
// screen can show live on-sale prices, and filters/ranks the bundled recipes by the user's
// prefs. There is no network/LLM here — the recipes were authored offline (see data/recipes.ts).

import { bestMatch, norm } from './basket';
import { BasketItem, Offer, Recipe, RecipeIngredient, RecipePrefs } from './types';

export const DIET_OPTIONS = ['vegetarian', 'vegan', 'gluten-free', 'no-pork'] as const;
export const CUISINE_OPTIONS = ['italian', 'german', 'pescatarian'] as const;

/** How many stores the "Shop at" scope may span — one shop, or a two-store run. Picking a third
 * replaces the oldest, so the tap is never a dead no-op. */
export const MAX_RECIPE_STORES = 2;

export const DEFAULT_RECIPE_PREFS: RecipePrefs = {
  servings: 2,
  count: 6,
  diet: null,
  cuisine: null,
  stores: [], // any store — never scope by default, or a fresh install looks empty
  onlyOnSale: false,
  cheapestKg: false,
};

// A recipe ingredient behaves like a one-off basket item for matching.
function asItem(ing: RecipeIngredient): BasketItem {
  return { key: ing.label, label: ing.label, keywords: ing.keywords, exclude: ing.exclude };
}

// Is this ingredient covered by the user's always-have list? (keyword overlap, both ways)
function inAlwaysHave(ing: RecipeIngredient, alwaysHave: BasketItem[]): boolean {
  return alwaysHave.some((ah) =>
    ah.keywords.some((k) =>
      ing.keywords.some((ik) => norm(ik).includes(norm(k)) || norm(k).includes(norm(ik))),
    ),
  );
}

export type IngredientRole = 'on_sale' | 'have' | 'buy';

export type ResolvedIngredient = {
  ing: RecipeIngredient;
  role: IngredientRole;
  offer: Offer | null; // the cheapest matching on-sale offer (when role === 'on_sale')
};

export type ResolvedRecipe = {
  recipe: Recipe;
  ingredients: ResolvedIngredient[];
  onSaleCount: number;
  buyCount: number; // ingredients you'd need to buy (not on sale, not a staple/always-have)
  estCostCents: number | null; // sum of the on-sale ingredients' prices (rough, 1 unit each)
  unitPriceSumCents: number | null; // Σ €/kg of matched on-sale ingredients (for the €/kg rank)
};

export function resolveRecipe(recipe: Recipe, offers: Offer[], alwaysHave: BasketItem[]): ResolvedRecipe {
  const ingredients: ResolvedIngredient[] = recipe.ingredients.map((ing) => {
    const offer = bestMatch(offers, asItem(ing));
    const role: IngredientRole = offer
      ? 'on_sale'
      : ing.staple || inAlwaysHave(ing, alwaysHave)
        ? 'have'
        : 'buy';
    return { ing, role, offer: role === 'on_sale' ? offer : null };
  });

  const onSale = ingredients.filter((r) => r.role === 'on_sale');
  const estCostCents = onSale.length ? onSale.reduce((s, r) => s + (r.offer?.price_cents ?? 0), 0) : null;
  const unitPrices = onSale.map((r) => r.offer?.unit_price_cents).filter((v): v is number => v != null);
  return {
    recipe,
    ingredients,
    onSaleCount: onSale.length,
    buyCount: ingredients.filter((r) => r.role === 'buy').length,
    estCostCents,
    unitPriceSumCents: unitPrices.length ? unitPrices.reduce((s, v) => s + v, 0) : null,
  };
}

/**
 * The chains a resolved recipe's on-sale ingredients actually come from — i.e. how many shops it
 * takes. Computed from the live match, never from an authored tag: a stored "this is a Lidl
 * recipe" would be a claim about the week it was written and would quietly go stale.
 */
export function recipeChains(rr: ResolvedRecipe): string[] {
  const seen: string[] = [];
  for (const ri of rr.ingredients) {
    // Staples are excluded on purpose: you don't make a trip for salt you already own, so a
    // staple that happens to be on sale must not add a store. It also keeps the badge honest
    // when a staple's keywords over-match — "salz" hits salted peanuts, "butter" hits a
    // Schweinefleisch-Spieß *Butter*fly — which measured 6 of 15 recipes before this guard.
    if (ri.ing.staple) continue;
    const chain = ri.offer?.chain; // only on-sale ingredients carry an offer
    if (chain && !seen.includes(chain)) seen.push(chain);
  }
  return seen;
}

/**
 * The stores the user asked to shop at, minus any with no offers in this set. A chain they hid in
 * the Stores modal — or one that simply isn't in this PLZ — must be a no-op, not an empty screen;
 * same only-when-present guard the deals pipeline applies to its store lens.
 */
export function activeRecipeStores(stores: string[] | undefined, offers: Offer[]): string[] {
  if (!stores?.length) return [];
  const present = new Set(offers.map((o) => o.chain));
  return stores.filter((c) => present.has(c));
}

function matchesDiet(tags: string[], diet: string | null): boolean {
  if (!diet) return true;
  if (diet === 'vegetarian') return tags.includes('vegetarian') || tags.includes('vegan');
  if (diet === 'no-pork') return !tags.includes('pork');
  return tags.includes(diet); // vegan, gluten-free
}

// Resolve, filter by prefs, rank, and cap to `count`. Returns ready-to-render recipes.
export function filterRecipes(
  recipes: Recipe[],
  prefs: RecipePrefs,
  offers: Offer[],
  alwaysHave: BasketItem[],
): ResolvedRecipe[] {
  // "Shop at": resolve against one store's (or two stores') offers only, so an ingredient on sale
  // elsewhere reads as "buy" — what you'd actually do. Staples still fall to "have", so they never
  // constrain where a recipe is shoppable, and the existing `onlyOnSale` toggle becomes "only what
  // I can fully shop here" for free.
  const active = activeRecipeStores(prefs.stores, offers);
  const pool = active.length ? offers.filter((o) => active.includes(o.chain)) : offers;

  let out = recipes
    .filter((r) => matchesDiet(r.tags, prefs.diet))
    .filter((r) => !prefs.cuisine || r.tags.includes(prefs.cuisine))
    .map((r) => resolveRecipe(r, pool, alwaysHave));

  if (prefs.onlyOnSale) out = out.filter((r) => r.buyCount === 0);

  if (prefs.cheapestKg) {
    // Cheapest €/kg of the on-sale ingredients first; recipes with no €/kg data sink.
    out.sort((a, b) => (a.unitPriceSumCents ?? Infinity) - (b.unitPriceSumCents ?? Infinity));
  } else {
    // Default: the most on-sale ingredients first (best use of this week's deals).
    out.sort((a, b) => b.onSaleCount - a.onSaleCount);
  }

  return out.slice(0, prefs.count);
}

const FRACTIONS: Record<string, number> = { '¼': 0.25, '½': 0.5, '¾': 0.75, '⅓': 1 / 3, '⅔': 2 / 3 };

// Scale a leading quantity ("400 g" → "800 g", "½" → "1") by a multiplier; pass through
// anything we can't parse (e.g. "2 cloves" still scales the 2; "to taste" is left alone).
export function scaleQty(qty: string | undefined, mult: number): string | undefined {
  if (!qty || mult === 1) return qty;
  const m = qty.match(/^\s*([¼½¾⅓⅔]|\d+(?:[.,]\d+)?)\s*(.*)$/);
  if (!m) return qty;
  const base = FRACTIONS[m[1]] ?? parseFloat(m[1].replace(',', '.'));
  if (!isFinite(base)) return qty;
  const scaled = base * mult;
  const num = Number.isInteger(scaled) ? String(scaled) : scaled.toFixed(2).replace(/\.?0+$/, '');
  return m[2] ? `${num} ${m[2]}` : num;
}
