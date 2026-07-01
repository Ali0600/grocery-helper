import {
  filterByVisibleStores,
  hasHiddenPresent,
  toggleHiddenStore,
  visibleStoreChains,
} from '../stores';
import { makeOffer } from './fixtures';

const present = ['lidl', 'rewe', 'edeka'];

describe('toggleHiddenStore', () => {
  it('hides a visible chain', () => {
    expect(toggleHiddenStore([], 'edeka', present)).toEqual(['edeka']);
  });

  it('shows a hidden chain again', () => {
    expect(toggleHiddenStore(['edeka'], 'edeka', present)).toEqual([]);
  });

  it('allows hiding down to a single visible chain', () => {
    expect(toggleHiddenStore(['lidl'], 'rewe', present)).toEqual(['lidl', 'rewe']);
  });

  it('refuses to hide the last visible present chain (no empty list)', () => {
    // lidl + rewe already hidden; hiding edeka would leave nothing visible -> blocked
    expect(toggleHiddenStore(['lidl', 'rewe'], 'edeka', present)).toEqual(['lidl', 'rewe']);
  });

  it('hides a chain that is not present without tripping the guard', () => {
    expect(toggleHiddenStore([], 'aldi', present)).toEqual(['aldi']);
  });
});

describe('filterByVisibleStores', () => {
  it('drops offers whose chain is hidden', () => {
    const offers = [makeOffer({ chain: 'lidl' }), makeOffer({ chain: 'edeka' })];
    expect(filterByVisibleStores(offers, ['edeka']).map((o) => o.chain)).toEqual(['lidl']);
  });

  it('returns every offer when nothing is hidden', () => {
    const offers = [makeOffer({ chain: 'lidl' }), makeOffer({ chain: 'rewe' })];
    expect(filterByVisibleStores(offers, [])).toHaveLength(2);
  });
});

describe('visibleStoreChains / hasHiddenPresent', () => {
  it('lists the still-visible present chains in present order', () => {
    expect(visibleStoreChains(present, ['rewe'])).toEqual(['lidl', 'edeka']);
  });

  it('flags an active filter only when a present chain is hidden', () => {
    expect(hasHiddenPresent(present, ['edeka'])).toBe(true);
    expect(hasHiddenPresent(present, [])).toBe(false);
    expect(hasHiddenPresent(present, ['aldi'])).toBe(false); // hidden but not present -> nothing filtered
  });
});
