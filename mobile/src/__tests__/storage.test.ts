import AsyncStorage from '@react-native-async-storage/async-storage';

import {
  getStoredLikes,
  getStoredSortByCategory,
  setStoredLikes,
  setStoredSortByCategory,
} from '../storage';
import { LikedItem } from '../types';

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

describe('likes persistence', () => {
  const liked: LikedItem = {
    key: 'mccain golden longs',
    name: 'McCain Golden Longs',
    brand: 'McCain',
    group: null,
    groupLabel: null,
    chain: 'lidl',
    likedPriceCents: 299,
    likedAt: 1,
  };

  it('returns [] when nothing is stored', async () => {
    expect(await getStoredLikes()).toEqual([]);
  });

  it('round-trips liked items', async () => {
    await setStoredLikes([liked]);
    expect(await getStoredLikes()).toEqual([liked]);
  });

  it('drops corrupt elements the Likes page would crash on', async () => {
    // Every guarded field is one the UI calls a method on or formats — notably `chain`:
    // chainLabel() does chain.charAt(0), so a missing chain is a TypeError, not a blank.
    await AsyncStorage.setItem(
      'likedItems',
      JSON.stringify([
        liked,
        { name: 'no key' },
        { key: '' },
        { ...liked, chain: undefined },
        { ...liked, likedPriceCents: 'free' },
        { ...liked, likedAt: null },
        'junk',
        null,
        42,
      ]),
    );
    expect(await getStoredLikes()).toEqual([liked]);
  });

  it('returns [] for a non-array payload or unparseable JSON', async () => {
    await AsyncStorage.setItem('likedItems', JSON.stringify({ key: 'x' }));
    expect(await getStoredLikes()).toEqual([]);
    await AsyncStorage.setItem('likedItems', 'not json');
    expect(await getStoredLikes()).toEqual([]);
  });
});
