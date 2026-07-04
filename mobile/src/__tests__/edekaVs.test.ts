import { buildEdekaVs, normName } from '../edekaVs';
import { Offer } from '../types';
import { makeOffer } from './fixtures';

const ed = (p: Partial<Offer>) => makeOffer({ chain: 'edeka', ...p });
const ec = (p: Partial<Offer>) => makeOffer({ chain: 'edeka_center', ...p });

describe('normName', () => {
  it('lowercases, maps punctuation to spaces, and collapses whitespace', () => {
    expect(normName('Coca-Cola')).toBe('coca cola');
    expect(normName('  GUT&GÜNSTIG   Weizenmehl  Type 405 ')).toBe(
      'gut günstig weizenmehl type 405',
    );
  });
});

describe('buildEdekaVs', () => {
  it('finds E-center-only items and price differences, ignoring other chains', () => {
    const offers = [
      makeOffer({ chain: 'lidl', name: 'Coca Cola', price_cents: 100 }), // ignored
      ed({ name: 'Coca Cola', price_cents: 149 }),
      ec({ name: 'Coca-Cola', price_cents: 399 }), // same normalised name, price differs
      ed({ name: 'Butter', price_cents: 189 }),
      ec({ name: 'Butter', price_cents: 189 }), // shared + same price → neither list
      ec({ name: 'Aperol Spritz', price_cents: 699 }), // only E center
    ];
    const { priceDiffs, ecenterOnly, hasBoth } = buildEdekaVs(offers);
    expect(hasBoth).toBe(true);
    expect(ecenterOnly.map((o) => o.name)).toEqual(['Aperol Spritz']);
    expect(priceDiffs).toHaveLength(1);
    expect(priceDiffs[0].label).toBe('Coca-Cola'); // the E center offer's display name
    expect(priceDiffs[0].cheaper).toBe('edeka'); // 149 < 399
    expect(priceDiffs[0].gapCents).toBe(250);
  });

  it('compares the cheapest offer per chain for a shared name', () => {
    const offers = [
      ed({ name: 'Kaffee', price_cents: 1099 }),
      ed({ name: 'Kaffee', price_cents: 999 }), // cheaper EDEKA copy
      ec({ name: 'Kaffee', price_cents: 999 }), // equal to the cheapest EDEKA → not a diff
    ];
    expect(buildEdekaVs(offers).priceDiffs).toHaveLength(0);
    expect(buildEdekaVs(offers).ecenterOnly).toHaveLength(0);
  });

  it('orders price gaps biggest-first and exclusives A–Z', () => {
    const offers = [
      ed({ name: 'A', price_cents: 100 }),
      ec({ name: 'A', price_cents: 150 }), // gap 50
      ed({ name: 'B', price_cents: 100 }),
      ec({ name: 'B', price_cents: 400 }), // gap 300
      ec({ name: 'Zebra', price_cents: 100 }),
      ec({ name: 'Apfel', price_cents: 100 }),
    ];
    const { priceDiffs, ecenterOnly } = buildEdekaVs(offers);
    expect(priceDiffs.map((r) => r.label)).toEqual(['B', 'A']);
    expect(ecenterOnly.map((o) => o.name)).toEqual(['Apfel', 'Zebra']);
  });

  it('reports hasBoth=false when one chain is absent', () => {
    expect(buildEdekaVs([ec({ name: 'X' })]).hasBoth).toBe(false);
    expect(buildEdekaVs([ed({ name: 'X' })]).hasBoth).toBe(false);
  });
});
