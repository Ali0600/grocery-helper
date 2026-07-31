import {
  activeStoreLens,
  filterByStoreLens,
  filterByVisibleStores,
  hasHiddenPresent,
  storeLensLabel,
  toggleHiddenStore,
  toggleStoreLens,
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

describe('filterByStoreLens', () => {
  const offers = [
    makeOffer({ chain: 'lidl' }),
    makeOffer({ chain: 'rewe' }),
    makeOffer({ chain: 'edeka' }),
  ];

  it('keeps only the lensed chains', () => {
    expect(filterByStoreLens(offers, ['lidl', 'edeka']).map((o) => o.chain)).toEqual([
      'lidl',
      'edeka',
    ]);
  });

  // Empty means "no lens", not "no stores" — the whole reason it can be called unconditionally.
  it('returns every offer when the lens is empty', () => {
    expect(filterByStoreLens(offers, [])).toHaveLength(3);
  });

  // Deliberately dumb: the stale/partial/full-coverage guards live in activeStoreLens, so a
  // lens naming a chain with no offers really does yield nothing here.
  it('yields nothing for a chain with no offers — guarding is the caller’s job', () => {
    expect(filterByStoreLens(offers, ['aldi'])).toEqual([]);
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


// --- The "Only show" lens (multi-select, persisted) ----------------------------------

describe('toggleStoreLens', () => {
  it('adds a chain to an empty (= All) lens', () => {
    expect(toggleStoreLens([], 'edeka')).toEqual(['edeka']);
  });

  it('keeps a THIRD pick — the lens is uncapped, unlike the Recipes "Shop at" scope', () => {
    // A two-element case can't catch a replace-oldest cap; this one can.
    expect(toggleStoreLens(['lidl', 'rewe'], 'edeka')).toEqual(['lidl', 'rewe', 'edeka']);
  });

  it('removes a selected chain without touching the others', () => {
    expect(toggleStoreLens(['edeka', 'lidl'], 'edeka')).toEqual(['lidl']);
  });

  it('clearing the LAST pick returns to All — there is deliberately no never-empty guard', () => {
    // The mirror of toggleHiddenStore's guard: here empty MEANS all, so a guard would make
    // the lens inescapable from the sheet.
    expect(toggleStoreLens(['edeka'], 'edeka')).toEqual([]);
  });
});

describe('activeStoreLens', () => {
  const available = ['lidl', 'rewe', 'edeka'];

  it('is empty when nothing is selected', () => {
    expect(activeStoreLens([], available)).toEqual([]);
  });

  it('narrows PARTIALLY to the chains still available, rather than giving up', () => {
    // 'netto' isn't loaded here; the edeka half of the selection must still apply.
    expect(activeStoreLens(['edeka', 'netto'], available)).toEqual(['edeka']);
  });

  it('is a no-op when NONE of the selection is available (the stale-lens guard)', () => {
    // This is what makes persisting the selection safe: a stale pick can never empty the list.
    expect(activeStoreLens(['netto', 'penny'], available)).toEqual([]);
  });

  it('collapses to All when the selection covers every available chain', () => {
    // Filtering to everything filters nothing — so it IS All, and the chip must not show.
    expect(activeStoreLens(['edeka', 'lidl', 'rewe'], available)).toEqual([]);
  });

  it('collapses when a store is HIDDEN into full coverage, with no tap at all', () => {
    // The reason the collapse lives here and not in the toggle: `available` shrinks
    // underneath the selection when the user removes a store in the Stores modal.
    expect(activeStoreLens(['lidl', 'rewe'], ['lidl', 'rewe'])).toEqual([]);
  });

  it('orders by availability, so tap order cannot change the result', () => {
    // Canonical output => one chip label and one memo input per selection.
    expect(activeStoreLens(['edeka', 'lidl'], available)).toEqual(['lidl', 'edeka']);
    expect(activeStoreLens(['lidl', 'edeka'], available)).toEqual(['lidl', 'edeka']);
  });

  it('is empty when nothing is loaded yet', () => {
    expect(activeStoreLens(['lidl'], [])).toEqual([]);
  });
});

describe('storeLensLabel', () => {
  it('names one store, exactly as the single-select chip always did', () => {
    expect(storeLensLabel(['edeka'])).toBe('Only Edeka');
  });

  it('names two, reusing the store chip\'s " · " join', () => {
    expect(storeLensLabel(['lidl', 'edeka'])).toBe('Only Lidl · Edeka');
  });

  it('counts from THREE up — the threshold, so an off-by-one fails here', () => {
    expect(storeLensLabel(['lidl', 'rewe', 'edeka'])).toBe('Only 3 stores');
  });

  it('never joins five names — the chip row scrolls, so a long label shoves the sort button off', () => {
    expect(storeLensLabel(['lidl', 'rewe', 'edeka', 'edeka_center', 'aldi'])).toBe('Only 5 stores');
  });
});
