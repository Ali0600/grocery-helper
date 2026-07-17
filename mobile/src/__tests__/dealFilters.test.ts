import {
  buildMineSections,
  buildSections,
  chainCounts,
  compareOffers,
  DealFilterOptions,
  dropEdekaCenterDuplicates,
  filterDeals,
  presentChains,
} from '../dealFilters';
import { SortMode } from '../storage';
import { hideKey } from '../hidden';
import { Offer } from '../types';
import { makeOffer } from './fixtures';

const OPTS: DealFilterOptions = {
  showNonFood: false,
  hiddenKeys: new Set<string>(),
  showHidden: false,
  hiddenStores: [],
  storeLens: null,
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

  it('places aldi last among the known chains, not alphabetically first', () => {
    const withAldi = [makeOffer({ chain: 'aldi' }), makeOffer({ chain: 'lidl' })];
    expect(presentChains(withAldi)).toEqual(['lidl', 'aldi']);
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

describe('filterDeals — "Only this store" lens', () => {
  const offers = [
    makeOffer({ chain: 'lidl', name: 'Lidl Milch' }),
    makeOffer({ chain: 'edeka', name: 'Edeka Milch' }),
    makeOffer({ chain: 'edeka', name: 'Edeka Brot' }),
    makeOffer({ chain: 'aldi', name: 'Aldi Käse' }),
  ];

  it('isolates one chain', () => {
    const out = filterDeals(offers, { ...OPTS, storeLens: 'edeka' });
    expect(out).toHaveLength(2);
    expect(out.every((o) => o.chain === 'edeka')).toBe(true);
  });

  it('is a no-op for a chain with no visible offers (the stale-lens guard)', () => {
    // e.g. the lensed store was removed from the store list, or the PLZ changed —
    // the list must never go empty because of a stale lens.
    const out = filterDeals(offers, { ...OPTS, storeLens: 'rewe' });
    expect(out).toHaveLength(offers.length);
  });

  it('composes AFTER the store list: a hidden chain cannot be lensed into view', () => {
    const out = filterDeals(offers, { ...OPTS, hiddenStores: ['edeka'], storeLens: 'edeka' });
    // edeka is hidden, so the lens finds nothing visible → no-op over the remaining set.
    expect(out.every((o) => o.chain !== 'edeka')).toBe(true);
    expect(out).toHaveLength(2);
  });

  it('composes with search and category', () => {
    const bySearch = filterDeals(offers, { ...OPTS, storeLens: 'edeka', query: 'milch' });
    expect(bySearch.map((o) => o.name)).toEqual(['Edeka Milch']);

    const withCat = [
      makeOffer({ chain: 'edeka', category: 'dairy' }),
      makeOffer({ chain: 'edeka', category: 'bakery' }),
      makeOffer({ chain: 'lidl', category: 'dairy' }),
    ];
    const byCat = filterDeals(withCat, { ...OPTS, storeLens: 'edeka', selected: 'dairy' });
    expect(byCat).toHaveLength(1);
    expect(byCat[0].chain).toBe('edeka');
  });

  it('composes with bio', () => {
    const mixed = [
      makeOffer({ chain: 'edeka', is_bio: true }),
      makeOffer({ chain: 'edeka', is_bio: false }),
      makeOffer({ chain: 'lidl', is_bio: true }),
    ];
    const out = filterDeals(mixed, { ...OPTS, storeLens: 'edeka', bioOnly: true });
    expect(out).toHaveLength(1);
    expect(out[0].chain).toBe('edeka');
  });
});

describe('dropEdekaCenterDuplicates', () => {
  // E center is EDEKA's hypermarket format, so their flyers overlap heavily: 103 of E center's
  // 272 products are also at EDEKA on a real Berlin PLZ, 98% of them at an identical price.
  // Only what E center actually ADDS should reach the list.
  const ed = (name: string, price: number) =>
    makeOffer({ chain: 'edeka', store_name: 'Edeka', name, price_cents: price });
  const ec = (name: string, price: number) =>
    makeOffer({ chain: 'edeka_center', store_name: 'E center', name, price_cents: price });
  const names = (out: Offer[]) => out.map((o) => `${o.chain}:${o.name}`);

  it('drops the E center copy when the price is identical (the 98% case)', () => {
    const out = dropEdekaCenterDuplicates([ed('Milka Tafel', 149), ec('Milka Tafel', 149)]);
    expect(names(out)).toEqual(['edeka:Milka Tafel']);
  });

  it('KEEPS the E center copy when it undercuts EDEKA — a cheaper price is not a duplicate', () => {
    // The real case this exception exists for: Axe Duschgel, EDEKA 2,79 vs E center 2,29.
    const out = dropEdekaCenterDuplicates([ed('Axe Duschgel', 279), ec('Axe Duschgel', 229)]);
    expect(names(out)).toEqual(['edeka:Axe Duschgel', 'edeka_center:Axe Duschgel']);
  });

  it('drops the E center copy when EDEKA is cheaper', () => {
    const out = dropEdekaCenterDuplicates([ed('Nutella', 199), ec('Nutella', 249)]);
    expect(names(out)).toEqual(['edeka:Nutella']);
  });

  it('keeps products only E center carries', () => {
    const out = dropEdekaCenterDuplicates([ed('Milka Tafel', 149), ec('Riesen Grillplatte', 999)]);
    expect(names(out)).toEqual(['edeka:Milka Tafel', 'edeka_center:Riesen Grillplatte']);
  });

  it('matches case- and punctuation-insensitively (normName), like the EDEKA-vs-E-center page', () => {
    const out = dropEdekaCenterDuplicates([ed('Milka Tafel', 149), ec('MILKA  Tafel!', 149)]);
    expect(names(out)).toEqual(['edeka:Milka Tafel']);
  });

  it('is a no-op when there is no EDEKA to compare against', () => {
    // A PLZ with no EDEKA: suppressing here would hide the product from every chain at once.
    const out = dropEdekaCenterDuplicates([ec('Milka Tafel', 149), makeOffer({ chain: 'lidl' })]);
    expect(out).toHaveLength(2);
  });

  it('never drops EDEKA rows or other chains', () => {
    const offers = [ed('Milka Tafel', 149), ec('Milka Tafel', 149), makeOffer({ chain: 'lidl', name: 'Milka Tafel', price_cents: 149 })];
    expect(names(dropEdekaCenterDuplicates(offers))).toEqual(['edeka:Milka Tafel', 'lidl:Milka Tafel']);
  });

  it('compares against the CHEAPEST EDEKA row when the name repeats', () => {
    // E center at 2,49 beats EDEKA's 2,79 but not its 1,99 → it is not a better deal.
    const out = dropEdekaCenterDuplicates([ed('Kaffee', 279), ed('Kaffee', 199), ec('Kaffee', 249)]);
    expect(names(out).filter((n) => n.startsWith('edeka_center'))).toEqual([]);
  });
});

describe('filterDeals — E center duplicates in the stack', () => {
  const ed = (name: string, price: number) =>
    makeOffer({ chain: 'edeka', name, price_cents: price });
  const ec = (name: string, price: number) =>
    makeOffer({ chain: 'edeka_center', name, price_cents: price });

  it('hides the duplicate in the normal list', () => {
    const offers = [ed('Milka Tafel', 149), ec('Milka Tafel', 149), ec('Nur E center', 199)];
    const out = filterDeals(offers, OPTS);
    expect(out.map((o) => o.name)).toEqual(['Milka Tafel', 'Nur E center']);
    expect(out.filter((o) => o.chain === 'edeka_center').map((o) => o.name)).toEqual(['Nur E center']);
  });

  it('suppression switches OFF when EDEKA is hidden — the product must not vanish entirely', () => {
    const offers = [ed('Milka Tafel', 149), ec('Milka Tafel', 149)];
    const out = filterDeals(offers, { ...OPTS, hiddenStores: ['edeka'] });
    expect(out.map((o) => o.chain)).toEqual(['edeka_center']); // E center's copy survives
  });

  it('runs BEFORE the store lens, so "Only E center" shows just its unique deals', () => {
    // Lensing strips EDEKA from the set; if the dedupe ran after, the guard would find no
    // EDEKA and every duplicate would reappear in exactly the view that should be cleanest.
    const offers = [ed('Milka Tafel', 149), ec('Milka Tafel', 149), ec('Nur E center', 199)];
    const out = filterDeals(offers, { ...OPTS, storeLens: 'edeka_center' });
    expect(out.map((o) => o.name)).toEqual(['Nur E center']);
  });

  it('a search cannot surface a suppressed duplicate', () => {
    const offers = [ed('Milka Tafel', 149), ec('Milka Tafel', 149)];
    const out = filterDeals(offers, { ...OPTS, query: 'milka' });
    expect(out.map((o) => o.chain)).toEqual(['edeka']);
  });
});

describe('filterDeals — hidden deals', () => {
  const edekaSchnaps = makeOffer({ id: 1, name: 'Schnaps', chain: 'edeka', price_cents: 99 });
  const lidlSchnaps = makeOffer({ id: 2, name: 'Schnaps', chain: 'lidl', price_cents: 149 });
  const butter = makeOffer({ id: 3, name: 'Butter', chain: 'lidl', category: 'butter' });
  const offers = [edekaSchnaps, lidlSchnaps, butter];
  const hide = (o: Offer) => new Set([hideKey(o)]);

  it('drops a hidden deal from the list, leaving the other chain’s copy', () => {
    const out = filterDeals(offers, { ...OPTS, hiddenKeys: hide(edekaSchnaps) });
    expect(out).toEqual([lidlSchnaps, butter]);
  });

  it('the lens shows ONLY hidden deals — the sole route back to a hidden deal’s detail', () => {
    const out = filterDeals(offers, {
      ...OPTS,
      hiddenKeys: hide(edekaSchnaps),
      showHidden: true,
    });
    expect(out).toEqual([edekaSchnaps]);
  });

  it('composes with search and category', () => {
    expect(
      filterDeals(offers, { ...OPTS, hiddenKeys: hide(lidlSchnaps), query: 'schnaps' }),
    ).toEqual([edekaSchnaps]);
    expect(
      filterDeals(offers, { ...OPTS, hiddenKeys: hide(butter), selected: 'butter' }),
    ).toEqual([]);
  });

  it('runs BEFORE the E-center dedupe: hiding EDEKA’s copy surfaces E center’s twin', () => {
    // The dedupe only suppresses an E center offer while an EDEKA twin is present. Hiding the
    // EDEKA copy must therefore let E center's re-appear, rather than losing the product from
    // both chains at once. This is exactly why the hide step precedes the dedupe.
    const edeka = makeOffer({ id: 10, name: 'Axe Duschgel', chain: 'edeka', price_cents: 279 });
    const ecenter = makeOffer({ id: 11, name: 'Axe Duschgel', chain: 'edeka_center', price_cents: 279 });
    const both = [edeka, ecenter];

    expect(filterDeals(both, OPTS)).toEqual([edeka]); // baseline: the E center dup is hidden
    expect(filterDeals(both, { ...OPTS, hiddenKeys: hide(edeka) })).toEqual([ecenter]);
  });
});

describe('buildMineSections — the "My Categories" home', () => {
  const labels: Record<string, string> = { fruits: 'Fruits', cheese: 'Cheese', pork: 'Pork' };
  // Sort every category by lowest price here, so the preview order is deterministic and readable.
  const byPrice: (slug: string) => SortMode = () => 'price';

  const fruit = (name: string, price: number) =>
    makeOffer({ name, category: 'fruits', category_label: 'Fruits', price_cents: price });
  const cheese = (name: string, price: number) =>
    makeOffer({ name, category: 'cheese', category_label: 'Cheese', price_cents: price });

  it('builds one shelf per chosen category, in myCategories order', () => {
    const base = [cheese('Gouda', 199), fruit('Äpfel', 149)];
    const out = buildMineSections(base, ['fruits', 'cheese'], labels, byPrice);
    expect(out.map((s) => s.slug)).toEqual(['fruits', 'cheese']); // user's order, not offer order
    expect(out.map((s) => s.label)).toEqual(['Fruits', 'Cheese']);
  });

  it('previews the top N by the category’s sort and reports the FULL total', () => {
    const base = [fruit('c', 300), fruit('a', 100), fruit('b', 200), fruit('d', 400)];
    const out = buildMineSections(base, ['fruits'], labels, byPrice, 2);
    expect(out[0].total).toBe(4); // "See all 4"
    expect(out[0].data.map((o) => o.name)).toEqual(['a', 'b']); // cheapest two, in price order
  });

  it('skips a chosen category that has no offers this week (no empty shelf)', () => {
    const out = buildMineSections([fruit('Äpfel', 149)], ['fruits', 'pork'], labels, byPrice);
    expect(out.map((s) => s.slug)).toEqual(['fruits']); // pork is absent, so it’s dropped
  });

  it('returns nothing when the base is empty or no categories are chosen', () => {
    expect(buildMineSections([], ['fruits'], labels, byPrice)).toEqual([]);
    expect(buildMineSections([fruit('Äpfel', 149)], [], labels, byPrice)).toEqual([]);
  });

  it('honours the per-category sort function (each shelf can order differently)', () => {
    const disc = (name: string, pct: number) =>
      makeOffer({ name, category: 'fruits', category_label: 'Fruits', discount_pct: pct, price_cents: 500 });
    const base = [disc('small', 10), disc('big', 40)];
    const out = buildMineSections(base, ['fruits'], labels, () => 'discount', 2);
    expect(out[0].data.map((o) => o.name)).toEqual(['big', 'small']); // biggest discount first
  });

  it('falls back to the offer label when the served labels map is missing the slug', () => {
    const out = buildMineSections([fruit('Äpfel', 149)], ['fruits'], {}, byPrice);
    expect(out[0].label).toBe('Fruits'); // from offer.category_label, not a blank header
  });
});
