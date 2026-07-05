import AsyncStorage from '@react-native-async-storage/async-storage';

import { CatalogItem, GROCERY_CATALOG } from './catalog';
import { DEFAULT_RECIPE_PREFS } from './recipes';
import { BasketItem, CategoryCount, MyStore, Offer, RecipePrefs } from './types';

const PLZ_KEY = 'plz';
const NONFOOD_KEY = 'showNonFood';
const MYSTORES_KEY = 'myStores';
const SORT_KEY = 'sortMode';
const HIDDEN_STORES_KEY = 'hiddenStores';
const BASKET_KEY = 'basket';
const DEALS_CACHE_KEY = 'dealsCache';
const RECIPE_PREFS_KEY = 'recipePrefs';
const ALWAYS_HAVE_KEY = 'alwaysHave';

export type SortMode = 'discount' | 'price' | 'unit';

export async function getStoredPlz(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(PLZ_KEY);
  } catch (e) {
    console.warn('storage: getStoredPlz failed', e);
    return null;
  }
}

export async function setStoredPlz(plz: string): Promise<void> {
  try {
    await AsyncStorage.setItem(PLZ_KEY, plz);
  } catch (e) {
    console.warn('storage: setStoredPlz failed', e);
    // Persistence is best-effort; the PLZ still applies for this session.
  }
}

export async function getStoredShowNonFood(): Promise<boolean> {
  try {
    return (await AsyncStorage.getItem(NONFOOD_KEY)) === '1';
  } catch (e) {
    console.warn('storage: getStoredShowNonFood failed', e);
    return false;
  }
}

export async function setStoredShowNonFood(value: boolean): Promise<void> {
  try {
    await AsyncStorage.setItem(NONFOOD_KEY, value ? '1' : '0');
  } catch (e) {
    console.warn('storage: setStoredShowNonFood failed', e);
    // best-effort
  }
}

// Store chains the user has hidden from the deals list (multi-select visibility). Empty
// = all shown; a hidden-set so any new/unknown chain defaults to visible. Persisted, so
// it also sticks across PLZ changes (unlike the session-only special-days / bio lenses).
export async function getStoredHiddenStores(): Promise<string[]> {
  try {
    const raw = await AsyncStorage.getItem(HIDDEN_STORES_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch (e) {
    console.warn('storage: getStoredHiddenStores failed', e);
    return [];
  }
}

export async function setStoredHiddenStores(chains: string[]): Promise<void> {
  try {
    await AsyncStorage.setItem(HIDDEN_STORES_KEY, JSON.stringify(chains));
  } catch (e) {
    console.warn('storage: setStoredHiddenStores failed', e);
    // best-effort
  }
}

export async function getStoredMyStores(): Promise<MyStore[]> {
  try {
    const raw = await AsyncStorage.getItem(MYSTORES_KEY);
    return raw ? (JSON.parse(raw) as MyStore[]) : [];
  } catch (e) {
    console.warn('storage: getStoredMyStores failed', e);
    return [];
  }
}

export async function setStoredMyStores(stores: MyStore[]): Promise<void> {
  try {
    await AsyncStorage.setItem(MYSTORES_KEY, JSON.stringify(stores));
  } catch (e) {
    console.warn('storage: setStoredMyStores failed', e);
    // best-effort
  }
}

export async function getStoredSortMode(): Promise<SortMode> {
  try {
    const v = await AsyncStorage.getItem(SORT_KEY);
    return v === 'price' || v === 'unit' ? v : 'discount'; // legacy/unknown -> default
  } catch (e) {
    console.warn('storage: getStoredSortMode failed', e);
    return 'discount';
  }
}

export async function setStoredSortMode(mode: SortMode): Promise<void> {
  try {
    await AsyncStorage.setItem(SORT_KEY, mode);
  } catch (e) {
    console.warn('storage: setStoredSortMode failed', e);
    // best-effort
  }
}

export async function getStoredBasket(): Promise<BasketItem[]> {
  try {
    const raw = await AsyncStorage.getItem(BASKET_KEY);
    return raw ? (JSON.parse(raw) as BasketItem[]) : [];
  } catch (e) {
    console.warn('storage: getStoredBasket failed', e);
    return [];
  }
}

export async function setStoredBasket(items: BasketItem[]): Promise<void> {
  try {
    await AsyncStorage.setItem(BASKET_KEY, JSON.stringify(items));
  } catch (e) {
    console.warn('storage: setStoredBasket failed', e);
    // best-effort
  }
}

// The last good deals payload, cached so the app shows something instantly while the
// (free-tier, sleepy) backend cold-starts. One key = only the most recently loaded PLZ
// is cached, which bounds the size to ~1 MB (the app is overwhelmingly single-PLZ).
export type CachedDeals = {
  plz: string;
  offers: Offer[];
  cats: CategoryCount[];
  storeName: string | null;
  cachedAt: number; // ms epoch of the fetch
};

export async function getDealsCache(): Promise<CachedDeals | null> {
  try {
    const raw = await AsyncStorage.getItem(DEALS_CACHE_KEY);
    return raw ? (JSON.parse(raw) as CachedDeals) : null;
  } catch (e) {
    console.warn('storage: getDealsCache failed', e);
    return null;
  }
}

export async function setDealsCache(data: CachedDeals): Promise<void> {
  try {
    await AsyncStorage.setItem(DEALS_CACHE_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn('storage: setDealsCache failed', e);
    // best-effort (e.g. storage quota) — the app still works without the cache
  }
}

// Drop just the cached deals, so the next load refetches from the server (used by the
// Options view to force an update when the weekly-authoritative cache is showing stale data).
export async function clearDealsCache(): Promise<void> {
  try {
    await AsyncStorage.removeItem(DEALS_CACHE_KEY);
  } catch (e) {
    console.warn('storage: clearDealsCache failed', e);
    // best-effort
  }
}

// Wipe the persisted prefs, saved stores, basket, and cache — a full app reset. The saved
// PLZ (location) is deliberately kept: a data reset shouldn't relocate the user to a default.
export async function clearAllData(): Promise<void> {
  try {
    await AsyncStorage.multiRemove([
      NONFOOD_KEY,
      HIDDEN_STORES_KEY,
      MYSTORES_KEY,
      SORT_KEY,
      BASKET_KEY,
      DEALS_CACHE_KEY,
      RECIPE_PREFS_KEY,
      ALWAYS_HAVE_KEY,
    ]);
  } catch (e) {
    console.warn('storage: clearAllData failed', e);
    // best-effort
  }
}

// --- Recipes: persisted filters + the "always have" staples list ---

export async function getStoredRecipePrefs(): Promise<RecipePrefs> {
  try {
    const raw = await AsyncStorage.getItem(RECIPE_PREFS_KEY);
    // Merge over defaults so a new field added later still has a value.
    return raw ? { ...DEFAULT_RECIPE_PREFS, ...(JSON.parse(raw) as Partial<RecipePrefs>) } : DEFAULT_RECIPE_PREFS;
  } catch (e) {
    console.warn('storage: getStoredRecipePrefs failed', e);
    return DEFAULT_RECIPE_PREFS;
  }
}

export async function setStoredRecipePrefs(prefs: RecipePrefs): Promise<void> {
  try {
    await AsyncStorage.setItem(RECIPE_PREFS_KEY, JSON.stringify(prefs));
  } catch (e) {
    console.warn('storage: setStoredRecipePrefs failed', e);
    // best-effort
  }
}

// Common pantry staples that don't have to be on sale to appear in a recipe. Seeded from
// the catalog (so the German match keywords are reused), plus salt (not a catalog item).
const STAPLE_KEYS = [
  'garlic', 'onion', 'carrot', 'oil', 'butter', 'flour', 'rice', 'pasta', 'eggs', 'milk', 'sugar', 'pepper',
];

export function defaultAlwaysHave(): BasketItem[] {
  const items: BasketItem[] = STAPLE_KEYS.map((k) => GROCERY_CATALOG.find((c) => c.key === k))
    .filter((c): c is CatalogItem => !!c)
    .map((c) => ({ key: c.key, label: c.en, keywords: c.keywords, exclude: c.exclude }));
  items.push({ key: 'salt', label: 'Salt', keywords: ['salz'] });
  return items;
}

export async function getStoredAlwaysHave(): Promise<BasketItem[]> {
  try {
    const raw = await AsyncStorage.getItem(ALWAYS_HAVE_KEY);
    return raw ? (JSON.parse(raw) as BasketItem[]) : defaultAlwaysHave();
  } catch (e) {
    console.warn('storage: getStoredAlwaysHave failed', e);
    return defaultAlwaysHave();
  }
}

export async function setStoredAlwaysHave(items: BasketItem[]): Promise<void> {
  try {
    await AsyncStorage.setItem(ALWAYS_HAVE_KEY, JSON.stringify(items));
  } catch (e) {
    console.warn('storage: setStoredAlwaysHave failed', e);
    // best-effort
  }
}
