import { buildComparison } from '../compare';
import { makeOffer } from './fixtures';

const chains = ['edeka', 'edeka_center'];
const avo = (chain: string, price: number) =>
  makeOffer({ chain, category: 'fruits', group: 'avocado', group_label: 'Avocado', price_cents: price });

describe('buildComparison', () => {
  it('lines up a sub-group across stores and flags the cheapest', () => {
    const rows = buildComparison([avo('edeka', 199), avo('edeka_center', 149)], chains, 'fruits');
    expect(rows).toHaveLength(1);
    expect(rows[0].label).toBe('Avocado');
    expect(rows[0].spreadCents).toBe(50);
    expect(rows[0].cells.map((c) => c.chain)).toEqual(['edeka', 'edeka_center']);
    expect(rows[0].cells[1].isCheapest).toBe(true); // E center 149
    expect(rows[0].cells[0].isCheapest).toBe(false);
  });

  it('keeps the cheapest offer per store', () => {
    const rows = buildComparison([avo('edeka', 199), avo('edeka', 179), avo('edeka_center', 189)], chains, 'fruits');
    expect(rows[0].cells[0].offer?.price_cents).toBe(179); // edeka's cheaper of two
    expect(rows[0].cells[0].isCheapest).toBe(true); // 179 < 189
  });

  it('excludes sub-groups present at only one store', () => {
    const one = makeOffer({ chain: 'edeka', category: 'fruits', group: 'banana', group_label: 'Banane', price_cents: 111 });
    expect(buildComparison([one], chains, 'fruits')).toHaveLength(0);
  });

  it('filters by category and by selected chains', () => {
    const offers = [
      avo('edeka', 199),
      avo('edeka_center', 149),
      avo('lidl', 99), // lidl not in the selected chains
      makeOffer({ chain: 'edeka', category: 'vegetables', group: 'tomato', group_label: 'Tomate', price_cents: 99 }),
      makeOffer({ chain: 'edeka_center', category: 'vegetables', group: 'tomato', group_label: 'Tomate', price_cents: 89 }),
    ];
    const rows = buildComparison(offers, chains, 'fruits');
    expect(rows).toHaveLength(1); // only fruits/avocado; tomato is a different category
    expect(rows[0].cells.some((c) => c.chain === 'lidl')).toBe(false);
    expect(rows[0].cells[1].offer?.price_cents).toBe(149); // not lidl's 99
  });

  it('sorts rows by biggest price spread first', () => {
    const offers = [
      avo('edeka', 150),
      avo('edeka_center', 140), // spread 10
      makeOffer({ chain: 'edeka', category: 'fruits', group: 'mango', group_label: 'Mango', price_cents: 299 }),
      makeOffer({ chain: 'edeka_center', category: 'fruits', group: 'mango', group_label: 'Mango', price_cents: 199 }), // spread 100
    ];
    expect(buildComparison(offers, chains, 'fruits').map((r) => r.label)).toEqual(['Mango', 'Avocado']);
  });

  it('on a price tie flags only the first store (chain order)', () => {
    const kiwi = (chain: string) =>
      makeOffer({ chain, category: 'fruits', group: 'kiwi', group_label: 'Kiwi', price_cents: 99 });
    const rows = buildComparison([kiwi('edeka'), kiwi('edeka_center')], chains, 'fruits');
    expect(rows[0].spreadCents).toBe(0);
    expect(rows[0].cells[0].isCheapest).toBe(true);
    expect(rows[0].cells[1].isCheapest).toBe(false);
  });

  it('ignores offers without a sub-group', () => {
    const offers = [
      makeOffer({ chain: 'edeka', category: 'fruits', group: null, price_cents: 199 }),
      makeOffer({ chain: 'edeka_center', category: 'fruits', group: null, price_cents: 149 }),
    ];
    expect(buildComparison(offers, chains, 'fruits')).toHaveLength(0);
  });
});
