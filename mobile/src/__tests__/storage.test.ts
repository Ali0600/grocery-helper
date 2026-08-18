import AsyncStorage from '@react-native-async-storage/async-storage';

import {
  clearAllData,
  clearDealsCache,
  getDealsCache,
  getStoredHistory,
  getStoredMyCategories,
  getStoredSortByCategory,
  getStoredStoreLens,
  setStoredHistory,
  setStoredMyCategories,
  setStoredSortByCategory,
  setDealsCache,
  setStoredStoreLens,
} from '../storage';
import { HistoryItem } from '../types';
import { makeOffer } from './fixtures';
import { VERTICALS } from '../verticals';

describe('myCategories persistence', () => {
  it('returns [] when nothing is stored (so the home falls back to All)', async () => {
    expect(await getStoredMyCategories()).toEqual([]);
  });

  it('round-trips the chosen categories in order', async () => {
    await setStoredMyCategories(['fruits', 'cheese', 'pork']);
    expect(await getStoredMyCategories()).toEqual(['fruits', 'cheese', 'pork']);
  });

  it('drops non-string / empty entries and a non-array payload', async () => {
    await AsyncStorage.setItem('myCategories', JSON.stringify(['fruits', 42, '', null, 'cheese']));
    expect(await getStoredMyCategories()).toEqual(['fruits', 'cheese']);
    await AsyncStorage.setItem('myCategories', JSON.stringify({ fruits: true }));
    expect(await getStoredMyCategories()).toEqual([]);
  });

  it('returns [] for unparseable JSON instead of throwing', async () => {
    await AsyncStorage.setItem('myCategories', 'not json');
    expect(await getStoredMyCategories()).toEqual([]);
  });

  it('is cleared by "Reset all app data"', async () => {
    await setStoredMyCategories(['fruits']);
    await clearAllData();
    expect(await getStoredMyCategories()).toEqual([]);
  });
});

describe('storeLens persistence', () => {
  it('returns [] when nothing is stored (so a fresh install shows every store)', async () => {
    expect(await getStoredStoreLens()).toEqual([]);
  });

  it('round-trips the chosen stores — the user asked for this to survive a restart', async () => {
    await setStoredStoreLens(['lidl', 'edeka']);
    expect(await getStoredStoreLens()).toEqual(['lidl', 'edeka']);
  });

  it('drops junk entries and a non-array payload rather than feeding them to the filter', async () => {
    await AsyncStorage.setItem('storeLens', JSON.stringify(['lidl', 7, null, 'edeka']));
    expect(await getStoredStoreLens()).toEqual(['lidl', 'edeka']);
    await AsyncStorage.setItem('storeLens', JSON.stringify({ lidl: true }));
    expect(await getStoredStoreLens()).toEqual([]);
  });

  it('returns [] for unparseable JSON instead of throwing', async () => {
    await AsyncStorage.setItem('storeLens', 'not json');
    expect(await getStoredStoreLens()).toEqual([]);
  });

  it('is cleared by "Reset all app data"', async () => {
    await setStoredStoreLens(['lidl']);
    await clearAllData();
    expect(await getStoredStoreLens()).toEqual([]);
  });
});

describe('sortByCategory persistence', () => {
  it('returns {} when nothing is stored (so every category uses its default)', async () => {
    expect(await getStoredSortByCategory()).toEqual({});
  });

  it('round-trips a map of overrides', async () => {
    await setStoredSortByCategory({ fruits: 'unit', household: 'discount' });
    expect(await getStoredSortByCategory()).toEqual({ fruits: 'unit', household: 'discount' });
  });

  it('drops entries that are not a known sort mode', async () => {
    // A corrupt/legacy value must not end up sorting the list by junk — the category
    // should fall back to its default instead.
    await AsyncStorage.setItem(
      'sortByCategory',
      JSON.stringify({ fruits: 'unit', cheese: 'bogus', pork: 42 }),
    );
    expect(await getStoredSortByCategory()).toEqual({ fruits: 'unit' });
  });

  it('returns {} for a non-object payload', async () => {
    await AsyncStorage.setItem('sortByCategory', JSON.stringify(['fruits']));
    expect(await getStoredSortByCategory()).toEqual({});
  });

  it('returns {} for unparseable JSON instead of throwing', async () => {
    await AsyncStorage.setItem('sortByCategory', 'not json');
    expect(await getStoredSortByCategory()).toEqual({});
  });
});

describe('history persistence', () => {
  const entry: HistoryItem = {
    key: 'mccain golden longs',
    name: 'McCain Golden Longs',
    brand: 'McCain',
    group: null,
    groupLabel: null,
    chain: 'lidl',
    addedPriceCents: 299,
    addedAt: 1,
  };

  it('returns [] when nothing is stored', async () => {
    expect(await getStoredHistory()).toEqual([]);
  });

  it('round-trips history entries', async () => {
    await setStoredHistory([entry]);
    expect(await getStoredHistory()).toEqual([entry]);
  });

  it('drops corrupt elements the History page would crash on', async () => {
    // Every guarded field is one the UI calls a method on or formats — notably `chain`:
    // chainLabel() does chain.charAt(0), so a missing chain is a TypeError, not a blank.
    await AsyncStorage.setItem(
      'likedItems',
      JSON.stringify([
        entry,
        { name: 'no key' },
        { key: '' },
        { ...entry, chain: undefined },
        { ...entry, addedPriceCents: 'free' },
        { ...entry, addedAt: null },
        'junk',
        null,
        42,
      ]),
    );
    expect(await getStoredHistory()).toEqual([entry]);
  });

  it('returns [] for a non-array payload or unparseable JSON', async () => {
    await AsyncStorage.setItem('likedItems', JSON.stringify({ key: 'x' }));
    expect(await getStoredHistory()).toEqual([]);
    await AsyncStorage.setItem('likedItems', 'not json');
    expect(await getStoredHistory()).toEqual([]);
  });
});


describe('history persistence — the Likes-era migration', () => {
  // Entries written by the Likes build carry `likedPriceCents`/`likedAt`. Two directions have
  // to work, and each fails SILENTLY rather than loudly if it doesn't:
  //   * forwards — an existing user's likes must survive the upgrade and become History;
  //   * backwards — the OLD build's shape filter REQUIRED `likedAt`, so writing only the new
  //     names would make an OTA rollback drop every entry, with no error anywhere.
  const legacy = {
    key: 'mccain golden longs',
    name: 'McCain Golden Longs',
    brand: 'McCain',
    group: null,
    groupLabel: null,
    chain: 'lidl',
    likedPriceCents: 299,
    likedAt: 1,
  };

  it('reads a Likes-era entry as History, so an upgrade keeps what you had', async () => {
    await AsyncStorage.setItem('likedItems', JSON.stringify([legacy]));
    expect(await getStoredHistory()).toEqual([
      {
        key: 'mccain golden longs',
        name: 'McCain Golden Longs',
        brand: 'McCain',
        group: null,
        groupLabel: null,
        chain: 'lidl',
        addedPriceCents: 299,
        addedAt: 1,
      },
    ]);
  });

  it('writes BOTH spellings, so an OTA rollback to the Likes build still reads them', async () => {
    await setStoredHistory([
      {
        key: 'k',
        name: 'N',
        brand: null,
        group: null,
        groupLabel: null,
        chain: 'lidl',
        addedPriceCents: 299,
        addedAt: 1,
      },
    ]);
    const wire = JSON.parse((await AsyncStorage.getItem('likedItems')) as string);
    expect(wire[0]).toMatchObject({
      addedPriceCents: 299,
      addedAt: 1,
      likedPriceCents: 299, // what the old build's filter requires
      likedAt: 1,
    });
  });

  it('prefers the new field when an entry carries both and they differ', async () => {
    await AsyncStorage.setItem(
      'likedItems',
      JSON.stringify([{ ...legacy, addedPriceCents: 199, addedAt: 42 }]),
    );
    const [got] = await getStoredHistory();
    expect([got.addedPriceCents, got.addedAt]).toEqual([199, 42]);
  });

  it('still drops a legacy entry that is corrupt in a guarded field', async () => {
    await AsyncStorage.setItem(
      'likedItems',
      JSON.stringify([{ ...legacy, likedAt: null }, { ...legacy, chain: undefined }]),
    );
    expect(await getStoredHistory()).toEqual([]);
  });
});

describe('per-vertical caches', () => {
  const cached = (name: string) => ({
    plz: '10115',
    offers: [makeOffer({ name })],
    cats: [],
    storeName: 'Test',
    cachedAt: Date.now(),
  });

  // Driven off VERTICALS rather than the two names that happened to exist when this block
  // was written: `allCacheKeys()` derives its list the same way, so a section added to the
  // registry must be covered here without anyone remembering to add a case.
  const seedAll = async () => {
    for (const v of VERTICALS) await setDealsCache(v, cached(`${v} product`));
  };

  it('keeps each vertical’s week separately, so switching costs no round trip', async () => {
    await seedAll();
    for (const v of VERTICALS) {
      expect((await getDealsCache(v))?.offers[0].name).toBe(`${v} product`);
    }
  });

  it('writes under a scoped key, never the bare one', async () => {
    await setDealsCache('drugstore', cached('Schauma Shampoo'));
    expect(await AsyncStorage.getItem('dealsCache:drugstore')).toBeTruthy();
    expect(await AsyncStorage.getItem('dealsCache')).toBeNull();
  });

  it('one vertical’s cache is invisible to the others', async () => {
    await setDealsCache('grocery', cached('Bergkäse'));
    for (const v of VERTICALS.filter((x) => x !== 'grocery')) {
      expect(await getDealsCache(v)).toBeNull();
    }
  });

  it('"Clear cached deals" clears EVERY vertical, not just the current one', async () => {
    // "deals won't update" is a whole-app complaint; leaving the other vertical's stale
    // week behind reproduces the very bug the button exists to fix, one tap later.
    await seedAll();
    await clearDealsCache();
    for (const v of VERTICALS) expect(await getDealsCache(v)).toBeNull();
  });

  it('"Reset all app data" clears every vertical too', async () => {
    await seedAll();
    await clearAllData();
    for (const v of VERTICALS) expect(await getDealsCache(v)).toBeNull();
  });
});
