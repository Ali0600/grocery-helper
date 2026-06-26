// Unit tests for the pure recipe resolver/filter/scaler (src/recipes.ts).

import { DEFAULT_RECIPE_PREFS, filterRecipes, resolveRecipe, scaleQty } from '../recipes';
import { BasketItem, Recipe, RecipeIngredient, RecipePrefs } from '../types';
import { makeOffer } from './fixtures';

const ing = (label: string, keywords: string[], extra: Partial<RecipeIngredient> = {}): RecipeIngredient => ({
  label,
  keywords,
  ...extra,
});

const recipe = (partial: Partial<Recipe> & { id: string; ingredients: RecipeIngredient[] }): Recipe => ({
  title: partial.title ?? partial.id,
  summary: '',
  servings: partial.servings ?? 2,
  timeMinutes: partial.timeMinutes ?? 20,
  tags: partial.tags ?? [],
  steps: partial.steps ?? [],
  ...partial,
});

const prefs = (over: Partial<RecipePrefs> = {}): RecipePrefs => ({ ...DEFAULT_RECIPE_PREFS, ...over });

describe('scaleQty', () => {
  it('scales a leading integer quantity', () => {
    expect(scaleQty('400 g', 2)).toBe('800 g');
    expect(scaleQty('2 cloves', 2)).toBe('4 cloves');
    expect(scaleQty('250 g', 3)).toBe('750 g');
  });

  it('scales unicode fractions and German decimals', () => {
    expect(scaleQty('½', 2)).toBe('1');
    expect(scaleQty('⅓', 3)).toBe('1');
    expect(scaleQty('1,5 kg', 2)).toBe('3 kg');
    expect(scaleQty('0,5 l', 3)).toBe('1.5 l'); // non-integer keeps a trimmed decimal
  });

  it('passes through what it cannot parse, and is a no-op at mult 1', () => {
    expect(scaleQty('to taste', 2)).toBe('to taste');
    expect(scaleQty(undefined, 2)).toBeUndefined();
    expect(scaleQty('400 g', 1)).toBe('400 g');
  });
});

describe('resolveRecipe', () => {
  const r = recipe({
    id: 'stirfry',
    ingredients: [
      ing('Chicken', ['hähnchen']),
      ing('Oil', ['öl'], { staple: true }),
      ing('Rice', ['reis']),
    ],
  });
  const offers = [makeOffer({ name: 'Hähnchenbrust', price_cents: 299, unit_price_cents: 599 })];

  it('tags ingredients on_sale / have / buy', () => {
    const res = resolveRecipe(r, offers, []);
    const byLabel = Object.fromEntries(res.ingredients.map((i) => [i.ing.label, i.role]));
    expect(byLabel).toEqual({ Chicken: 'on_sale', Oil: 'have', Rice: 'buy' });
    expect(res.onSaleCount).toBe(1);
    expect(res.buyCount).toBe(1); // rice (oil is a staple → "have", not "buy")
    expect(res.estCostCents).toBe(299);
    expect(res.unitPriceSumCents).toBe(599);
  });

  it('treats an always-have ingredient as "have", not "buy"', () => {
    const alwaysHave: BasketItem[] = [{ key: 'rice', label: 'Rice', keywords: ['reis'] }];
    const res = resolveRecipe(r, offers, alwaysHave);
    const rice = res.ingredients.find((i) => i.ing.label === 'Rice');
    expect(rice?.role).toBe('have');
    expect(res.buyCount).toBe(0);
  });
});

describe('filterRecipes', () => {
  const pasta = recipe({
    id: 'pasta',
    tags: ['vegetarian', 'italian', 'dinner'],
    ingredients: [ing('Pasta', ['nudel']), ing('Tomato', ['tomate'])],
  });
  const chickenRice = recipe({
    id: 'chicken-rice',
    tags: ['german', 'dinner'],
    ingredients: [ing('Chicken', ['hähnchen']), ing('Rice', ['reis'])],
  });
  const porkChop = recipe({
    id: 'pork-chop',
    tags: ['pork', 'german'],
    ingredients: [ing('Schnitzel', ['schnitzel'])],
  });
  const recipes = [pasta, chickenRice, porkChop];

  const offers = [
    makeOffer({ name: 'Nudeln 500g', price_cents: 99, unit_price_cents: 200 }),
    makeOffer({ name: 'Tomaten', price_cents: 149, unit_price_cents: 300 }),
    makeOffer({ name: 'Hähnchen', price_cents: 299, unit_price_cents: 100 }),
  ];

  it('filters by diet (vegan counts as vegetarian; no-pork excludes pork)', () => {
    expect(filterRecipes(recipes, prefs({ diet: 'vegetarian' }), offers, []).map((r) => r.recipe.id)).toEqual(['pasta']);
    expect(filterRecipes(recipes, prefs({ diet: 'no-pork' }), offers, []).map((r) => r.recipe.id).sort()).toEqual([
      'chicken-rice',
      'pasta',
    ]);
  });

  it('filters by cuisine', () => {
    expect(filterRecipes(recipes, prefs({ cuisine: 'italian' }), offers, []).map((r) => r.recipe.id)).toEqual(['pasta']);
  });

  it('only-on-sale keeps recipes with nothing left to buy', () => {
    // pasta: both ingredients on sale (buyCount 0); the others need rice/schnitzel.
    expect(filterRecipes(recipes, prefs({ onlyOnSale: true }), offers, []).map((r) => r.recipe.id)).toEqual(['pasta']);
  });

  it('default rank is most-on-sale first; cheapestKg ranks by Σ €/kg', () => {
    expect(filterRecipes(recipes, prefs(), offers, []).map((r) => r.recipe.id)).toEqual([
      'pasta', // 2 on sale
      'chicken-rice', // 1 on sale
      'pork-chop', // 0 on sale
    ]);
    // €/kg sums: chicken-rice = 100, pasta = 500, pork-chop = none (sinks last).
    expect(filterRecipes(recipes, prefs({ cheapestKg: true }), offers, []).map((r) => r.recipe.id)).toEqual([
      'chicken-rice',
      'pasta',
      'pork-chop',
    ]);
  });

  it('caps the result to prefs.count', () => {
    expect(filterRecipes(recipes, prefs({ count: 2 }), offers, [])).toHaveLength(2);
  });
});
