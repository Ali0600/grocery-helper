// The Hide feature's pure core. Two properties carry the whole design and both were user
// choices, so both are pinned here: a hide is scoped to ONE CHAIN's copy, and it lasts exactly
// ONE FLYER WEEK.
import { dealsStale } from '../format';
import {
  activeHidden,
  filterHidden,
  hiddenKeySet,
  hideKey,
  isHidden,
  onlyHidden,
  resolveHidden,
  toggleHidden,
} from '../hidden';
import { makeOffer } from './fixtures';

const NOW = new Date('2026-07-15T12:00:00').getTime(); // a Wednesday, mid flyer week
const LAST_WEEK = new Date('2026-07-08T12:00:00').getTime(); // the Wednesday before

const edekaSchnaps = makeOffer({ id: 1, name: 'Schnaps', chain: 'edeka', price_cents: 99 });
const lidlSchnaps = makeOffer({ id: 2, name: 'Schnaps', chain: 'lidl', price_cents: 149 });
const edekaButter = makeOffer({ id: 3, name: 'Butter', chain: 'edeka', price_cents: 199 });

beforeEach(() => {
  jest.spyOn(Date, 'now').mockReturnValue(NOW);
});
afterEach(() => {
  (Date.now as jest.Mock).mockRestore?.();
});

describe('hideKey — a hide is scoped to ONE chain', () => {
  it('separates the same product at different chains', () => {
    // The user's literal choice: hiding Edeka's Schnaps must leave Lidl's Schnaps visible.
    expect(hideKey(edekaSchnaps)).not.toBe(hideKey(lidlSchnaps));
  });

  it('matches the same product at the same chain across name spelling variants', () => {
    // Reuses edekaVs' normName, the blessed cross-source product-name normalizer.
    expect(hideKey(makeOffer({ name: 'SCHNAPS!', chain: 'edeka' }))).toBe(hideKey(edekaSchnaps));
  });

  it('is NOT keyed on offer.id — ids churn on every re-scrape', () => {
    // /api/reset deletes every row and Render's DB is ephemeral, so SQLite reuses rowids:
    // the same id is a different product next week. Identity must ignore it.
    expect(hideKey(makeOffer({ id: 999, name: 'Schnaps', chain: 'edeka' }))).toBe(
      hideKey(edekaSchnaps),
    );
  });
});

describe('a hide lasts exactly one flyer week', () => {
  it('is active in the week it was made', () => {
    const items = [resolveHidden(edekaSchnaps)];
    expect(activeHidden(items)).toHaveLength(1);
    expect(isHidden(edekaSchnaps, items)).toBe(true);
  });

  it('expires once the flyer week is over, so the deal comes back', () => {
    const stale = [{ ...resolveHidden(edekaSchnaps), hiddenAt: LAST_WEEK }];
    expect(dealsStale(LAST_WEEK)).toBe(true); // guard: the fixture really is last week's
    expect(activeHidden(stale)).toHaveLength(0);
    expect(isHidden(edekaSchnaps, stale)).toBe(false);
    expect(filterHidden([edekaSchnaps], hiddenKeySet(stale))).toEqual([edekaSchnaps]);
  });
});

describe('filtering', () => {
  const offers = [edekaSchnaps, lidlSchnaps, edekaButter];

  it('drops only the hidden chain-copy, leaving the other chain and other products', () => {
    const keys = hiddenKeySet([resolveHidden(edekaSchnaps)]);
    expect(filterHidden(offers, keys)).toEqual([lidlSchnaps, edekaButter]);
  });

  it('onlyHidden is the exact inverse — the lens back to a hidden deal', () => {
    const keys = hiddenKeySet([resolveHidden(edekaSchnaps)]);
    expect(onlyHidden(offers, keys)).toEqual([edekaSchnaps]);
  });

  it('no hides → the set passes through untouched', () => {
    expect(filterHidden(offers, hiddenKeySet([]))).toBe(offers);
  });
});

describe('toggleHidden', () => {
  it('adds, then removes on a second toggle (Hide ⇄ Un-Hide)', () => {
    const once = toggleHidden([], edekaSchnaps);
    expect(once).toHaveLength(1);
    expect(toggleHidden(once, edekaSchnaps)).toHaveLength(0);
  });

  it('prunes expired entries on write, so the stored list cannot grow forever', () => {
    const stale = { ...resolveHidden(lidlSchnaps), hiddenAt: LAST_WEEK };
    const next = toggleHidden([stale], edekaSchnaps);
    expect(next.map((h) => h.key)).toEqual([hideKey(edekaSchnaps)]);
  });

  it('un-hiding one chain-copy leaves the other chain hidden', () => {
    const both = toggleHidden(toggleHidden([], edekaSchnaps), lidlSchnaps);
    const after = toggleHidden(both, edekaSchnaps);
    expect(isHidden(edekaSchnaps, after)).toBe(false);
    expect(isHidden(lidlSchnaps, after)).toBe(true);
  });
});
