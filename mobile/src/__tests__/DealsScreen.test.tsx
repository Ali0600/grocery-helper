// DealsScreen's cache/revalidate seam — the app's most valuable invariants, every one of
// which had a real bug at some point:
//   * the weekly-authoritative contract (a fresh cache makes ZERO backend calls),
//   * the cache version (a new chain was invisible until Sunday — the ALDI bug),
//   * never clobbering good data with an empty refresh (the poisoned-cache bug),
//   * the cold-PLZ on-demand scrape.
// The api module is mocked wholesale; storage runs against the official AsyncStorage
// in-memory mock (jest-setup.js). Time is pinned via a Date.now spy — no fake timers, so
// RNTL's async rendering behaves normally.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react-native';
import React from 'react';

import { DEALS_CACHE_VERSION } from '../format';
import DealsScreen from '../screens/DealsScreen';
import { makeOffer } from './fixtures';

jest.mock('../api', () => ({
  api: {
    base: 'http://test',
    offers: jest.fn(),
    categories: jest.fn(),
    stores: jest.fn(),
    scrape: jest.fn(),
    resetDb: jest.fn(),
    recategorize: jest.fn(),
    offerPayload: jest.fn(),
    offerPayloads: jest.fn(),
    nearbyStores: jest.fn(),
    chainBranches: jest.fn(),
  },
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { api } = require('../api');

const NOW = new Date('2026-06-24T12:00:00').getTime(); // a Wednesday, mid flyer week
const CACHED_OFFER = makeOffer({ name: 'Cached Bergkäse', price_cents: 299 });
const FRESH_OFFER = makeOffer({ name: 'Frisches ALDI Angebot', price_cents: 149 });

/** A promise the test resolves by hand, so "cached renders BEFORE the refresh lands" is
 * an ordered fact rather than a race. */
function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

async function seedCache(over: Partial<Record<string, unknown>> = {}) {
  await AsyncStorage.setItem('plz', '10115');
  await AsyncStorage.setItem(
    'dealsCache',
    JSON.stringify({
      plz: '10115',
      offers: [CACHED_OFFER],
      cats: [],
      storeName: 'Lidl Testkiez',
      cachedAt: NOW,
      version: DEALS_CACHE_VERSION,
      ...over,
    }),
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(Date, 'now').mockReturnValue(NOW);
  api.categories.mockResolvedValue([]);
  api.stores.mockResolvedValue([{ id: 1, chain: 'lidl', name: 'Lidl Testkiez', plz: '10115' }]);
  api.scrape.mockResolvedValue({ scraped: 1 });
  // Payload prefetch is fire-and-forget background work — resolve it quietly.
  api.offerPayloads.mockResolvedValue({});
});

afterEach(() => {
  (Date.now as jest.Mock).mockRestore?.();
});

describe('DealsScreen — the weekly-authoritative cache contract', () => {
  it('serves a fresh current-version cache with ZERO backend calls', async () => {
    await seedCache();
    await render(<DealsScreen />);

    expect(await screen.findByText('Cached Bergkäse')).toBeTruthy();
    // The whole point of the weekly cache: a mid-week open never touches the
    // (sleepy, free-tier) backend.
    expect(api.offers).not.toHaveBeenCalled();
    expect(api.scrape).not.toHaveBeenCalled();
  });

  it('treats an older cache VERSION as stale-not-absent: cached deals render instantly, a background refresh swaps in the new set', async () => {
    // The ALDI-invisibility bug as a regression test: a release that adds a chain bumps
    // DEALS_CACHE_VERSION; without this, the fresh-cache branch above skips the backend
    // and the new chain stays invisible until Sunday.
    await seedCache({ version: DEALS_CACHE_VERSION - 1 });
    const fetch = deferred<(typeof FRESH_OFFER)[]>();
    api.offers.mockReturnValue(fetch.promise);

    await render(<DealsScreen />);

    // Stale ≠ absent: the old deals must be on screen while the refresh is in flight
    // (no spinner, no cold-start block)...
    expect(await screen.findByText('Cached Bergkäse')).toBeTruthy();
    expect(api.offers).toHaveBeenCalled();

    // ...and the new set replaces them when it lands.
    fetch.resolve([FRESH_OFFER]);
    expect(await screen.findByText('Frisches ALDI Angebot')).toBeTruthy();
    await waitFor(() => expect(screen.queryByText('Cached Bergkäse')).toBeNull());
  });

  it('re-stamps the rewritten cache with the CURRENT version, so the refresh happens once, not forever', async () => {
    await seedCache({ version: DEALS_CACHE_VERSION - 1 });
    api.offers.mockResolvedValue([FRESH_OFFER]);

    await render(<DealsScreen />);
    await screen.findByText('Frisches ALDI Angebot');

    await waitFor(() => {
      const writes = (AsyncStorage.setItem as jest.Mock).mock.calls.filter(
        ([k]) => k === 'dealsCache',
      );
      expect(writes.length).toBeGreaterThan(0);
      const latest = JSON.parse(writes[writes.length - 1][1]);
      expect(latest.version).toBe(DEALS_CACHE_VERSION);
      expect(latest.offers).toHaveLength(1);
    });
  });
});

describe('DealsScreen — an empty refresh must never destroy good data', () => {
  it('keeps the deals on screen and never writes an empty cache', async () => {
    // The poisoned-cache bug: a cold Render backend returns [] (its ephemeral DB only
    // boot-scrapes the default PLZ); that emptiness must not wipe the view or the cache.
    await seedCache({ version: DEALS_CACHE_VERSION - 1 }); // force a refresh attempt
    api.offers.mockResolvedValue([]); // backend stays empty, even after the scrape
    await render(<DealsScreen />);

    expect(await screen.findByText('Cached Bergkäse')).toBeTruthy();
    // The empty read triggers the on-demand scrape, then a refetch — still empty.
    await waitFor(() => expect(api.scrape).toHaveBeenCalled());
    // The cached offer survives...
    expect(screen.getByText('Cached Bergkäse')).toBeTruthy();
    // ...and no empty offer list was ever persisted over the good cache.
    const writes = (AsyncStorage.setItem as jest.Mock).mock.calls.filter(
      ([k]) => k === 'dealsCache',
    );
    for (const [, payload] of writes) {
      expect(JSON.parse(payload).offers.length).toBeGreaterThan(0);
    }
  });
});

describe('DealsScreen — cold start on an unscraped PLZ', () => {
  it('scrapes on demand when the first read is empty, then renders the refetched deals', async () => {
    await AsyncStorage.setItem('plz', '10115'); // no deals cache at all
    api.offers.mockResolvedValueOnce([]).mockResolvedValue([FRESH_OFFER]);

    await render(<DealsScreen />);

    expect(await screen.findByText('Frisches ALDI Angebot')).toBeTruthy();
    expect(api.scrape).toHaveBeenCalledTimes(1);
    expect(api.offers.mock.calls.length).toBeGreaterThanOrEqual(2); // read → scrape → refetch
  });
});

describe('DealsScreen — the Likes heart badge', () => {
  // The badge counts liked products on sale NOW (exact name match), not the list size —
  // it's the "something you like is back on sale" signal.
  async function seedLike(over: Partial<Record<string, unknown>> = {}) {
    await AsyncStorage.setItem(
      'likedItems',
      JSON.stringify([
        {
          key: 'cached bergkäse',
          name: 'Cached Bergkäse',
          brand: null,
          group: null,
          groupLabel: null,
          chain: 'lidl',
          likedPriceCents: 299,
          likedAt: 1,
          ...over,
        },
      ]),
    );
  }

  it('shows the on-sale count when a liked product is in the current deals', async () => {
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);

    await screen.findByText('Cached Bergkäse');
    expect(within(screen.getByLabelText('Likes')).getByText('1')).toBeTruthy();
  });

  it('stays badge-less when no liked product is on sale', async () => {
    await seedCache();
    await seedLike({ key: 'nicht im angebot', name: 'Nicht im Angebot' });
    await render(<DealsScreen />);

    await screen.findByText('Cached Bergkäse');
    expect(within(screen.getByLabelText('Likes')).queryByText(/\d/)).toBeNull();
  });

  it('renders the deal detail INSIDE the Likes sheet, never as a sibling of it', async () => {
    // The iOS bug this pins (measured on a simulator, 2026-07-17): RN presents a Modal from
    // `[self reactViewController]` — the first view controller up the responder chain — so two
    // SIBLING modals resolve to the same root VC and iOS refuses the second:
    //   "Attempt to present <RCTFabricModalHostViewController> on <EXRootViewController>
    //    which is already presenting <RCTFabricModalHostViewController>".
    // The detail never appeared, and RN's `_isPresented = YES` latch (set before the failed
    // present, never rolled back) then killed EVERY later deal tap for the whole session.
    // Nested, the detail mounts into the sheet's own VC view and presents from it.
    // This constraint is invisible at the point that depends on it — moving the element one
    // level up in DealsScreen silently reintroduces the bug — so assert containment.
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');

    fireEvent.press(screen.getByLabelText('Likes'));
    fireEvent.press(await screen.findByLabelText('Open deal for Cached Bergkäse'));

    // "View payload" is unique to the deal detail; it must live INSIDE the Likes modal.
    const likesModal = await screen.findByTestId('likes-modal');
    await waitFor(() => expect(within(likesModal).getByText('View payload')).toBeTruthy());

    // ...and the Likes row still comes first in tree order, which is what makes the detail
    // paint on top on react-native-web (portals mount into document.body in JSX order under
    // one z-index, so DOM order — not visibility — decides). Both platforms, one layout.
    const marks = screen.getAllByText(/liked at|View payload/);
    expect(JSON.stringify(marks[0].props.children)).toContain('liked at');
    expect(JSON.stringify(marks[1].props.children)).toContain('View payload');
  });

  it('opens the deal when the liked product NAME is tapped, not just the price block', async () => {
    // The name is the obvious thing to tap and was dead: only the ~45pt price block had a
    // press handler, so "I tap it and nothing happens" had two independent causes.
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');
    fireEvent.press(screen.getByLabelText('Likes'));

    // The row's pressable wraps the whole main column, name included.
    const row = await screen.findByLabelText('Open deal for Cached Bergkäse');
    expect(within(row).getByText('Cached Bergkäse')).toBeTruthy();

    fireEvent.press(row);
    expect(await screen.findByText('View payload')).toBeTruthy();
  });

  it('drops the detail when the Likes sheet closes, so it cannot change host mid-flight', async () => {
    // If `active` outlived the sheet, the single detail element would move from inside the
    // sheet to the screen root — a remount that races a dismissal against a present.
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');

    fireEvent.press(screen.getByLabelText('Likes'));
    fireEvent.press(await screen.findByLabelText('Open deal for Cached Bergkäse'));
    await screen.findByText('View payload');

    // Both sheets carry a "Close" — the detail nests inside Likes — so target the labelled one.
    fireEvent.press(screen.getByLabelText('Close likes'));
    await waitFor(() => expect(screen.queryByText('View payload')).toBeNull());
  });
});

describe('DealsScreen — the header is pin-only', () => {
  it('drops the PLZ text but keeps it ANNOUNCED, so removing it visually is not an a11y regression', async () => {
    // Six icon actions + a text block don't fit a phone: the 6th icon squeezed "PLZ 10713"
    // to "P…" at 375/390pt. The pin stays; the code moves into the label.
    await seedCache();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');

    expect(screen.queryByText('PLZ 10715')).toBeNull();
    expect(screen.queryByText(/^PLZ /)).toBeNull(); // no visible postal-code text at all
    expect(screen.getByLabelText('Change postal code, currently 10115')).toBeTruthy();
  });
});

describe('DealsScreen — per-category sort', () => {
  // One global sort couldn't fit both: €/kg is the axis you shop Fruits on (and out-covers
  // "Biggest discount" there, 77% vs 47% measured), while household is only 25% €/kg-covered.
  // Asserts the RENDERED label, not the state — the sort must visibly say what it's doing.
  async function seedFruitCache() {
    await seedCache({
      offers: [
        makeOffer({ name: 'Bananen', category: 'fruits', category_label: 'Fruits' }),
        makeOffer({ name: 'Äpfel', category: 'fruits', category_label: 'Fruits' }),
      ],
      cats: [{ category: 'fruits', label: 'Fruits', count: 2 }],
    });
  }

  it('switches to €/kg when a food category is selected, and back to discount in All', async () => {
    await seedFruitCache();
    await render(<DealsScreen />);

    // "All" keeps the deal-hunting default — the app's headline.
    await waitFor(() => expect(screen.getByText('Biggest discount')).toBeTruthy());

    fireEvent.press(screen.getByText('Fruits (2)'));
    await waitFor(() => expect(screen.getByText('Cheapest €/kg')).toBeTruthy());

    fireEvent.press(screen.getByText('All'));
    await waitFor(() => expect(screen.getByText('Biggest discount')).toBeTruthy());
  });

  it('honours a stored per-category override instead of the default', async () => {
    await seedFruitCache();
    await AsyncStorage.setItem('sortByCategory', JSON.stringify({ fruits: 'price' }));

    await render(<DealsScreen />);
    fireEvent.press(screen.getByText('Fruits (2)'));

    // The user's pick for Fruits wins over the €/kg default.
    await waitFor(() => expect(screen.getByText('Lowest price')).toBeTruthy());
  });
});
