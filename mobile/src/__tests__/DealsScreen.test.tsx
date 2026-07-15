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
import { render, screen, waitFor } from '@testing-library/react-native';
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
