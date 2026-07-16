import AsyncStorage from '@react-native-async-storage/async-storage';

import { getStoredSortByCategory, setStoredSortByCategory } from '../storage';

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
