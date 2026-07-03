import {
  buildSections,
  chainCounts,
  compareOffers,
  DealFilterOptions,
  filterDeals,
  presentChains,
} from '../dealFilters';
import { Offer } from '../types';
import { makeOffer } from './fixtures';

const OPTS: DealFilterOptions = {
  showNonFood: false,
  hiddenStores: [],
  specialDays: false,
  bioOnly: false,
  query: '',
  selected: null,
};

describe('presentChains / chainCounts', () => {
  const offers = [
    makeOffer({ chain: 'edeka' }),
    makeOffer({ chain: 'lidl' }),
    makeOffer({ chain: 'lidl' }),
    makeOffer({ chain: 'zzz-neu' }),
  ];

  it('orders known chains by CHAIN_ORDER, unknown appended alphabetically', () => {
    expect(presentChains(offers)).toEqual(['lidl', 'edeka', 'zzz-neu']);
  });

  it('tallies offers per chain', () => {
    expect(chainCounts(offers)).toEqual({ lidl: 2, edeka: 1, 'zzz-neu': 1 });
  });
});

describe('compareOffers', () => {
  const cheap = makeOffer({ price_cents: 100, discount_pct: 10, unit_price_cents: 500 });
  const dear = makeOffer({ price_cents: 300, discount_pct: 50, unit_price_cents: 200 });
  const bare = makeOffer({ price_cents: 200, discount_pct: null, unit_price_cents: null });

  it('discount: biggest first, nulls sink', () => {
    expect([cheap, dear, bare].sort((a, b) => compareOffers(a, b, 'discount'))).toEqual([dear, cheap, bare]);
  });

  it('price: cheapest first', () => {
    expect([dear, bare, cheap].sort((a, b) => compareOffers(a, b, 'price'))).toEqual([cheap, bare, dear]);
  });

  it('unit: cheapest €/kg first, nulls sink', () => {
    expect([cheap, bare, dear].sort((a, b) => compareOffers(a, b, 'unit'))).toEqual([dear, cheap, bare]);
  });
});

describe('filterDeals', () => {
  const offers: Offer[] = [
    makeOffer({ name: 'Apfel', category: 'fruits', chain: 'lidl' }),
    makeOffer({ name: 'Spülmittel', category: 'household', chain: 'lidl' }),
    makeOffer({ name: 'Bio Milch', brand: 'Alnatura', category: 'dairy', chain: 'edeka', is_bio: true }),
    makeOffer({ name: 'Wochenend-Steak', category: 'beef', chain: 'edeka', day_limited: true }),
  ];

  it('hides household unless toggled on', () => {
    expect(filterDeals(offers, OPTS).map((o) => o.name)).not.toContain('Spülmittel');
    expect(filterDeals(offers, { ...OPTS, showNonFood: true }).map((o) => o.name)).toContain('Spülmittel');
  });

  it('drops hidden stores', () => {
    const names = filterDeals(offers, { ...OPTS, hiddenStores: ['edeka'] }).map((o) => o.name);
    expect(names).toEqual(['Apfel']);
  });

  it('special-days lens keeps only day-limited offers — but only when some exist', () => {
    expect(filterDeals(offers, { ...OPTS, specialDays: true }).map((o) => o.name)).toEqual(['Wochenend-Steak']);
    const none = offers.filter((o) => !o.day_limited);
    // Guard: with no day-limited offers loaded, a stale toggle must not empty the list.
    expect(filterDeals(none, { ...OPTS, specialDays: true })).toHaveLength(2);
  });

  it('bio lens keeps only organic offers — but only when some exist', () => {
    expect(filterDeals(offers, { ...OPTS, bioOnly: true }).map((o) => o.name)).toEqual(['Bio Milch']);
    const none = offers.filter((o) => !o.is_bio);
    expect(filterDeals(none, { ...OPTS, bioOnly: true })).toHaveLength(2);
  });

  it('search matches name or brand, case-insensitive, and overrides the category chip', () => {
    const byName = filterDeals(offers, { ...OPTS, query: 'apfel', selected: 'dairy' });
    expect(byName.map((o) => o.name)).toEqual(['Apfel']); // selected ignored while searching
    const byBrand = filterDeals(offers, { ...OPTS, query: 'ALNATURA' });
    expect(byBrand.map((o) => o.name)).toEqual(['Bio Milch']);
  });

  it('category chip filters when not searching', () => {
    expect(filterDeals(offers, { ...OPTS, selected: 'dairy' }).map((o) => o.name)).toEqual(['Bio Milch']);
  });

  it('lenses compose (hidden store + bio)', () => {
    const out = filterDeals(offers, { ...OPTS, hiddenStores: ['lidl'], bioOnly: true });
    expect(out.map((o) => o.name)).toEqual(['Bio Milch']);
  });
});

describe('buildSections', () => {
  const avo = (price: number) =>
    makeOffer({ group: 'avocado', group_label: 'Avocado', price_cents: price, category: 'fruits' });
  const solo = makeOffer({ group: 'kiwi', group_label: 'Kiwi', price_cents: 79 });
  const loose = makeOffer({ group: null, price_cents: 111 });

  it('returns [] for no offers', () => {
    expect(buildSections([], 'price')).toEqual([]);
  });

  it('groups products with 2+ offers, sends singletons and ungrouped to a "More" bucket', () => {
    const sections = buildSections([avo(199), avo(149), solo, loose], 'price');
    expect(sections).toHaveLength(2);
    expect(sections[0].label).toBe('Avocado');
    expect(sections[0].count).toBe(2);
    expect(sections[0].fromCents).toBe(149); // cheapest in the group
    expect(sections[0].data.map((o) => o.price_cents)).toEqual([149, 199]); // sorted within
    expect(sections[1].label).toBe('More');
    expect(sections[1].muted).toBe(true);
    expect(sections[1].data).toHaveLength(2);
  });

  it('a lone ungrouped list renders one unlabeled bucket', () => {
    const sections = buildSections([loose], 'price');
    expect(sections).toHaveLength(1);
    expect(sections[0].label).toBeNull(); // no "More" header when nothing sits above
  });

  it('orders groups by size, then label', () => {
    const tom = (p: number) =>
      makeOffer({ group: 'tomate', group_label: 'Tomate', price_cents: p });
    const sections = buildSections([avo(1), avo(2), tom(1), tom(2), tom(3)], 'price');
    expect(sections.map((s) => s.label)).toEqual(['Tomate', 'Avocado']); // 3 > 2
  });
});
