import AsyncStorage from '@react-native-async-storage/async-storage';

import { CatalogItem, GROCERY_CATALOG } from './catalog';
import { DEALS_CACHE_VERSION } from './format';
import { activeHidden, HiddenItem } from './hidden';
import { DEFAULT_RECIPE_PREFS } from './recipes';
import { BasketItem, CategoryCount, LikedItem, MyStore, Offer, PayloadMap, RecipePrefs } from './types';

const PLZ_KEY = 'plz';
const NONFOOD_KEY = 'showNonFood';
const MYSTORES_KEY = 'myStores';
const SORT_KEY = 'sortMode'; // the global sort (used in "All")
const SORT_BY_CATEGORY_KEY = 'sortByCategory'; // slug -> the user's explicit sort for it
const HIDDEN_STORES_KEY = 'hiddenStores';
const MYCATS_KEY = 'myCategories'; // ordered category slugs for the personalized "My Categories" home
const BASKET_KEY = 'basket';
const LIKES_KEY = 'likedItems';
const HIDDEN_KEY = 'hiddenItems'; // deals dismissed from the deal detail (one flyer week)
const DEALS_CACHE_KEY = 'dealsCache';
const PAYLOAD_CACHE_KEY = 'payloadCache';
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

// The categories chosen for the personalized "My Categories" home, in the user's order. Empty =
// no custom view yet, so the app falls back to "All" (a fresh install is never a blank screen).
// A hidden-set-style persisted PREFERENCE, like `hiddenStores`: cleared by "Reset all app data"
// only, not the Filters-sheet Reset. A slug that no longer has offers is simply skipped when the
// home is built, so a stale/renamed category is inert (never crashes, never shows an empty shelf).
export async function getStoredMyCategories(): Promise<string[]> {
  try {
    const raw = await AsyncStorage.getItem(MYCATS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Keep only non-empty strings — a corrupt entry must not reach the section builder as a
    // category slug (it would just never match, but drop it so the stored list stays clean).
    return parsed.filter((s): s is string => typeof s === 'string' && s.length > 0);
  } catch (e) {
    console.warn('storage: getStoredMyCategories failed', e);
    return [];
  }
}

export async function setStoredMyCategories(slugs: string[]): Promise<void> {
  try {
    await AsyncStorage.setItem(MYCATS_KEY, JSON.stringify(slugs));
  } catch (e) {
    console.warn('storage: setStoredMyCategories failed', e);
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

/** The user's explicit sort choice per category (slug -> mode). A category with no entry
 * falls back to `defaultSortForCategory` (see sort.ts) — so this only records overrides,
 * which keeps new/renamed categories on the sensible default instead of a stale pick. */
export async function getStoredSortByCategory(): Promise<Record<string, SortMode>> {
  try {
    const raw = await AsyncStorage.getItem(SORT_BY_CATEGORY_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    // Drop anything that isn't a known mode — a corrupt/legacy value must not sort by junk.
    return Object.fromEntries(
      Object.entries(parsed).filter(
        ([, v]) => v === 'discount' || v === 'price' || v === 'unit',
      ) as [string, SortMode][],
    );
  } catch (e) {
    console.warn('storage: getStoredSortByCategory failed', e);
    return {};
  }
}

export async function setStoredSortByCategory(map: Record<string, SortMode>): Promise<void> {
  try {
    await AsyncStorage.setItem(SORT_BY_CATEGORY_KEY, JSON.stringify(map));
  } catch (e) {
    console.warn('storage: setStoredSortByCategory failed', e);
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

/** Liked products (right-swipe). Per-element shape filter (not just a cast) because the
 * Likes page dereferences these on every render — a corrupt entry must be dropped, not
 * crash the page. Guard EVERY field the UI calls a method on: `chainLabel(item.chain)`
 * does `chain.charAt(0)`, so a missing `chain` is a TypeError, not a blank label. */
export async function getStoredLikes(): Promise<LikedItem[]> {
  try {
    const raw = await AsyncStorage.getItem(LIKES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (l): l is LikedItem =>
        !!l &&
        typeof l === 'object' &&
        typeof l.key === 'string' &&
        l.key.length > 0 &&
        typeof l.name === 'string' &&
        typeof l.chain === 'string' &&
        typeof l.likedPriceCents === 'number' &&
        typeof l.likedAt === 'number',
    );
  } catch (e) {
    console.warn('storage: getStoredLikes failed', e);
    return [];
  }
}

/** Hidden deals. Expired entries (from a previous flyer week) are dropped at read AND at write,
 * so a stale hide can never resurface and the list can't grow without bound. */
export async function getStoredHidden(): Promise<HiddenItem[]> {
  try {
    const raw = await AsyncStorage.getItem(HIDDEN_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const shaped = parsed.filter(
      (h): h is HiddenItem =>
        !!h &&
        typeof h === 'object' &&
        typeof h.key === 'string' &&
        h.key.length > 0 &&
        typeof h.name === 'string' &&
        typeof h.chain === 'string' &&
        typeof h.hiddenAt === 'number',
    );
    return activeHidden(shaped);
  } catch (e) {
    console.warn('storage: getStoredHidden failed', e);
    return [];
  }
}

export async function setStoredHidden(items: HiddenItem[]): Promise<void> {
  try {
    await AsyncStorage.setItem(HIDDEN_KEY, JSON.stringify(activeHidden(items)));
  } catch (e) {
    console.warn('storage: setStoredHidden failed', e);
    // best-effort
  }
}

export async function setStoredLikes(items: LikedItem[]): Promise<void> {
  try {
    await AsyncStorage.setItem(LIKES_KEY, JSON.stringify(items));
  } catch (e) {
    console.warn('storage: setStoredLikes failed', e);
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
  version?: number; // DEALS_CACHE_VERSION at write time; absent on pre-versioning caches
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
    // Stamped here rather than at every call site, so a cache written by this build is
    // always readable by it (an unstamped write would look stale forever).
    const stamped: CachedDeals = { ...data, version: DEALS_CACHE_VERSION };
    await AsyncStorage.setItem(DEALS_CACHE_KEY, JSON.stringify(stamped));
  } catch (e) {
    console.warn('storage: setDealsCache failed', e);
    // best-effort (e.g. storage quota) — the app still works without the cache
  }
}

// Drop the cached deals AND their prefetched payloads, so the next load refetches both from
// the server (used by the Options view to force an update when the weekly-authoritative cache
// is showing stale data). The two are coupled to the same PLZ/week, so they clear together.
export async function clearDealsCache(): Promise<void> {
  try {
    await AsyncStorage.multiRemove([DEALS_CACHE_KEY, PAYLOAD_CACHE_KEY]);
  } catch (e) {
    console.warn('storage: clearDealsCache failed', e);
    // best-effort
  }
}

// Raw payloads for the current PLZ's offers, prefetched in the background so the deal
// detail's "View payload" is instant + offline (no per-offer call to the sleepy backend).
// Single key = only the last PLZ, like the deals cache (~2 MB). `count` is the deal count
// at prefetch time, so a changed deal set (or a new flyer week) triggers a re-prefetch.
export type CachedPayloads = {
  plz: string;
  byId: PayloadMap;
  count: number;
  cachedAt: number; // ms epoch of the fetch
};

export async function getPayloadCache(): Promise<CachedPayloads | null> {
  try {
    const raw = await AsyncStorage.getItem(PAYLOAD_CACHE_KEY);
    return raw ? (JSON.parse(raw) as CachedPayloads) : null;
  } catch (e) {
    console.warn('storage: getPayloadCache failed', e);
    return null;
  }
}

export async function setPayloadCache(data: CachedPayloads): Promise<void> {
  try {
    await AsyncStorage.setItem(PAYLOAD_CACHE_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn('storage: setPayloadCache failed', e);
    // best-effort (e.g. storage quota) — "View payload" just falls back to a network fetch
  }
}

// Wipe the persisted prefs, saved stores, basket, and cache — a full app reset. The saved
// PLZ (location) is deliberately kept: a data reset shouldn't relocate the user to a default.
export async function clearAllData(): Promise<void> {
  try {
    await AsyncStorage.multiRemove([
      NONFOOD_KEY,
      HIDDEN_STORES_KEY,
      MYCATS_KEY,
      MYSTORES_KEY,
      SORT_KEY,
      SORT_BY_CATEGORY_KEY,
      BASKET_KEY,
      LIKES_KEY,
      HIDDEN_KEY,
      DEALS_CACHE_KEY,
      PAYLOAD_CACHE_KEY,
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
