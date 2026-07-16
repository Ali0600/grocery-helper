import { defaultSortForCategory, resolveSortMode, sortLabel } from '../sort';

describe('defaultSortForCategory', () => {
  it('keeps "Biggest discount" for All — €/kg is only meaningful within a comparable set', () => {
    expect(defaultSortForCategory(null)).toBe('discount');
  });

  it('keeps "Biggest discount" for household (the only non-food category)', () => {
    // Measured: household is the one category where discount out-covers €/kg (36% vs 25%).
    expect(defaultSortForCategory('household')).toBe('discount');
  });

  it('defaults food categories to €/kg', () => {
    for (const cat of ['fruits', 'vegetables', 'pork', 'cheese', 'bakery', 'pantry', 'snacks']) {
      expect(defaultSortForCategory(cat)).toBe('unit');
    }
  });

  it('defaults an unlisted/future category to €/kg (only household is non-food)', () => {
    // `other`/`vegan` and anything the classifier gains later should land on the food default
    // rather than needing a code change to be sensible.
    expect(defaultSortForCategory('other')).toBe('unit');
    expect(defaultSortForCategory('vegan')).toBe('unit');
    expect(defaultSortForCategory('brand-new-category')).toBe('unit');
  });
});

describe('resolveSortMode', () => {
  it('uses the persisted global mode in All', () => {
    expect(resolveSortMode(null, 'price', {})).toBe('price');
    expect(resolveSortMode(null, 'discount', { fruits: 'unit' })).toBe('discount');
  });

  it('falls back to the category default when the user has no pick for it', () => {
    expect(resolveSortMode('fruits', 'discount', {})).toBe('unit');
    expect(resolveSortMode('household', 'unit', {})).toBe('discount');
  });

  it("lets the user's explicit pick win over the default", () => {
    expect(resolveSortMode('fruits', 'discount', { fruits: 'price' })).toBe('price');
    // …including putting a food category back on discount.
    expect(resolveSortMode('fruits', 'price', { fruits: 'discount' })).toBe('discount');
    // …and household onto €/kg.
    expect(resolveSortMode('household', 'discount', { household: 'unit' })).toBe('unit');
  });

  it('does not leak one category\'s pick to another', () => {
    const picks = { fruits: 'price' as const };
    expect(resolveSortMode('fruits', 'discount', picks)).toBe('price');
    expect(resolveSortMode('cheese', 'discount', picks)).toBe('unit'); // cheese keeps its default
    expect(resolveSortMode('household', 'discount', picks)).toBe('discount');
  });

  it('ignores the global mode inside a category (that is what the per-category pick is for)', () => {
    // The old behaviour — one global sort — is exactly what made €/kg leak into household.
    expect(resolveSortMode('household', 'unit', {})).toBe('discount');
  });
});

describe('sortLabel', () => {
  it('labels each mode', () => {
    expect(sortLabel('unit')).toBe('Cheapest €/kg');
    expect(sortLabel('discount')).toBe('Biggest discount');
    expect(sortLabel('price')).toBe('Lowest price');
  });
});
