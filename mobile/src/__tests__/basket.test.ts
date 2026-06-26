// Unit tests for the pure basket matcher + cross-store planner (src/basket.ts).

import {
  bestMatch,
  buildPlan,
  matchOffers,
  norm,
  offerMatchesItem,
} from '../basket';
import { BasketItem } from '../types';
import { makeOffer } from './fixtures';

const item = (partial: Partial<BasketItem> & { keywords: string[] }): BasketItem => ({
  key: partial.key ?? partial.label ?? partial.keywords[0],
  label: partial.label ?? partial.keywords[0],
  keywords: partial.keywords,
  exclude: partial.exclude,
});

describe('norm', () => {
  it('lowercases and folds German umlauts + ß', () => {
    expect(norm('MÖHRE')).toBe('mohre');
    expect(norm('Möhre')).toBe('mohre');
    expect(norm('Weißbier')).toBe('weissbier');
    expect(norm('Café Crème')).toBe('cafe creme');
  });

  it('is null-safe', () => {
    expect(norm('')).toBe('');
    // @ts-expect-error exercising the runtime guard for a null name
    expect(norm(null)).toBe('');
  });
});

describe('offerMatchesItem', () => {
  const milk = item({ label: 'Milk', keywords: ['milch'], exclude: ['buttermilch'] });

  it('matches a keyword as a substring, umlaut/case-insensitively', () => {
    expect(offerMatchesItem(makeOffer({ name: 'Frische MÖHREN 1kg' }), item({ keywords: ['möhre'] }))).toBe(true);
    expect(offerMatchesItem(makeOffer({ name: 'Bio Vollmilch' }), milk)).toBe(true);
  });

  it('honours the exclude trap-guards', () => {
    expect(offerMatchesItem(makeOffer({ name: 'Buttermilch 500g' }), milk)).toBe(false);
  });

  it('matches against the brand too', () => {
    const it_ = item({ keywords: ['milbona'] });
    expect(offerMatchesItem(makeOffer({ name: 'Joghurt', brand: 'Milbona' }), it_)).toBe(true);
  });

  it('returns false when nothing matches', () => {
    expect(offerMatchesItem(makeOffer({ name: 'Brot' }), milk)).toBe(false);
  });
});

describe('matchOffers / bestMatch', () => {
  const milk = item({ keywords: ['milch'] });
  const offers = [
    makeOffer({ name: 'Vollmilch', price_cents: 99 }),
    makeOffer({ name: 'Bio Milch', price_cents: 89 }),
    makeOffer({ name: 'Brot' }),
  ];

  it('matchOffers returns matches sorted by absolute price ascending', () => {
    const m = matchOffers(offers, milk);
    expect(m.map((o) => o.price_cents)).toEqual([89, 99]);
  });

  it('bestMatch returns the cheapest match, or null', () => {
    expect(bestMatch(offers, milk)?.price_cents).toBe(89);
    expect(bestMatch(offers, item({ keywords: ['kaviar'] }))).toBeNull();
  });
});

describe('buildPlan', () => {
  const milk = item({ key: 'milk', keywords: ['milch'] });
  const bread = item({ key: 'bread', keywords: ['brot'] });

  // milk: rewe 89 (cheapest) vs lidl 99; bread: lidl 149 only.
  const lidlMilk = makeOffer({ id: 101, name: 'Vollmilch', chain: 'lidl', price_cents: 99 });
  const reweMilk = makeOffer({ id: 102, name: 'Bio Milch', chain: 'rewe', price_cents: 89 });
  const lidlBread = makeOffer({ id: 103, name: 'Bauernbrot', chain: 'lidl', price_cents: 149 });
  const offers = [lidlMilk, reweMilk, lidlBread];

  it('cherry-picks the cheapest per item across stores', () => {
    const p = buildPlan([milk, bread], offers, {});
    expect(p.totalCents).toBe(89 + 149); // rewe milk + lidl bread
    expect(p.matchedCount).toBe(2);
    expect(p.missing).toEqual([]);
    // groups sorted by subtotal desc → lidl (149) before rewe (89)
    expect(p.byStore.map((g) => g.chain)).toEqual(['lidl', 'rewe']);
  });

  it('reports the best single store and the split savings', () => {
    const p = buildPlan([milk, bread], offers, {});
    // lidl covers both items (99 + 149 = 248); splitting saves 248 - 238 = 10
    expect(p.bestSingleChain).toBe('lidl');
    expect(p.savingsCents).toBe(10);
  });

  it('respects a user pick by offer id', () => {
    const p = buildPlan([milk, bread], offers, { milk: lidlMilk.id });
    expect(p.lines[0].offer?.id).toBe(lidlMilk.id); // forced lidl milk @ 99, not rewe @ 89
    expect(p.totalCents).toBe(99 + 149);
    expect(p.byStore).toHaveLength(1); // everything at lidl now
  });

  it('lists items with no deal as missing', () => {
    const caviar = item({ key: 'caviar', keywords: ['kaviar'] });
    const p = buildPlan([milk, caviar], offers, {});
    expect(p.missing.map((i) => i.key)).toEqual(['caviar']);
    expect(p.matchedCount).toBe(1);
  });
});
