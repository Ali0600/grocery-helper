// Tests for the curated catalog (src/catalog.ts): structural invariants + the
// documented substring-trap `exclude` guards, exercised through the real matcher.

import { offerMatchesItem } from '../basket';
import { CatalogItem, GROCERY_CATALOG, POPULAR_KEYS } from '../catalog';
import { BasketItem } from '../types';
import { makeOffer } from './fixtures';

const adapt = (c: CatalogItem): BasketItem => ({ key: c.key, label: c.en, keywords: c.keywords, exclude: c.exclude });
const byKey = (key: string): BasketItem => {
  const c = GROCERY_CATALOG.find((i) => i.key === key);
  if (!c) throw new Error(`no catalog item "${key}"`);
  return adapt(c);
};
const matches = (name: string, key: string): boolean => offerMatchesItem(makeOffer({ name }), byKey(key));

describe('catalog structure', () => {
  it('has unique keys', () => {
    const keys = GROCERY_CATALOG.map((c) => c.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it('every item has English + German labels and at least one keyword', () => {
    for (const c of GROCERY_CATALOG) {
      expect(c.en.length).toBeGreaterThan(0);
      expect(c.de.length).toBeGreaterThan(0);
      expect(c.keywords.length).toBeGreaterThan(0);
    }
  });

  it('every POPULAR_KEYS entry resolves to a catalog item', () => {
    const keys = new Set(GROCERY_CATALOG.map((c) => c.key));
    for (const k of POPULAR_KEYS) expect(keys.has(k)).toBe(true);
  });
});

describe('substring-trap exclude guards', () => {
  it('milk does not match buttermilk', () => {
    expect(matches('Frische Vollmilch', 'milk')).toBe(true);
    expect(matches('Buttermilch 500g', 'milk')).toBe(false);
  });

  it('leek vs garlic ("lauch" is a substring of "Knoblauch")', () => {
    expect(matches('Knoblauch', 'garlic')).toBe(true);
    expect(matches('Knoblauch', 'leek')).toBe(false);
    expect(matches('Lauch / Porree', 'leek')).toBe(true);
  });

  it('salmon vs pollock ("lachs" is a substring of "Seelachs")', () => {
    expect(matches('Seelachsfilet', 'pollock')).toBe(true);
    expect(matches('Seelachsfilet', 'salmon')).toBe(false);
    expect(matches('Räucherlachs', 'salmon')).toBe(true);
  });

  it('apple does not match apple juice', () => {
    expect(matches('Bio Äpfel 1kg', 'apple')).toBe(true);
    expect(matches('Apfelsaft naturtrüb', 'apple')).toBe(false);
  });

  it('rice does not match "Preis" promos ("reis" is a substring of "Preis")', () => {
    expect(matches('Basmati Reis', 'rice')).toBe(true);
    expect(matches('Tiefpreis Aktion', 'rice')).toBe(false);
  });
});
