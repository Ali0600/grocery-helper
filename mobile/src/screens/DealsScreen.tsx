import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  SectionList,
  SectionListData,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { api } from '../api';
import { chainLabel } from '../chains';
import { BasketModal } from '../components/BasketModal';
import { CategoryChips } from '../components/CategoryChips';
import { FlyerModal } from '../components/FlyerModal';
import { GroupHeader } from '../components/GroupHeader';
import { Icon } from '../components/Icon';
import { IconButton } from '../components/IconButton';
import { OfferCard } from '../components/OfferCard';
import { OptionsModal } from '../components/OptionsModal';
import { PlzModal } from '../components/PlzModal';
import { RecipesModal } from '../components/RecipesModal';
import { FilterBar } from '../components/FilterBar';
import { FilterSheet } from '../components/FilterSheet';
import { SearchBar } from '../components/SearchBar';
import { StoresModal } from '../components/StoresModal';
import { UpdateStatus } from '../components/UpdateStatus';
import { dealsStale } from '../format';
import { sortLabel } from '../sort';
import { filterByVisibleStores, hasHiddenPresent, toggleHiddenStore, visibleStoreChains } from '../stores';
import { DEFAULT_RECIPE_PREFS } from '../recipes';
import {
  clearAllData,
  clearDealsCache,
  getDealsCache,
  getStoredAlwaysHave,
  getStoredBasket,
  getStoredHiddenStores,
  getStoredMyStores,
  getStoredPlz,
  getStoredRecipePrefs,
  getStoredShowNonFood,
  getStoredSortMode,
  setDealsCache,
  setStoredAlwaysHave,
  setStoredBasket,
  setStoredHiddenStores,
  setStoredMyStores,
  setStoredPlz,
  setStoredRecipePrefs,
  setStoredShowNonFood,
  setStoredSortMode,
  SortMode,
} from '../storage';
import { colors, space } from '../theme';
import { BasketItem, CategoryCount, MyStore, Offer, RecipePrefs } from '../types';

// Override via mobile/.env (EXPO_PUBLIC_DEFAULT_PLZ) so a personal postal code isn't
// committed; falls back to a neutral central-Berlin default for the public bundle.
const DEFAULT_PLZ = process.env.EXPO_PUBLIC_DEFAULT_PLZ ?? '10115';
// Preferred order for the store filter; any other chains follow, alphabetically.
const CHAIN_ORDER = ['lidl', 'rewe', 'edeka'];

// Compare two values, sending nulls to the end regardless of direction.
function byNullsLast(a: number | null, b: number | null, dir: 'asc' | 'desc'): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  return dir === 'asc' ? a - b : b - a;
}

// The single source of truth for how offers are ordered, by the active sort mode. Used by
// the flat list, the within-group order, and the "More" bucket so they're always consistent.
function compareOffers(a: Offer, b: Offer, mode: SortMode): number {
  if (mode === 'unit') return byNullsLast(a.unit_price_cents, b.unit_price_cents, 'asc');
  if (mode === 'price') return a.price_cents - b.price_cents; // cheapest absolute price
  return byNullsLast(a.discount_pct, b.discount_pct, 'desc'); // 'discount': biggest % off
}

// Per-section metadata for the grouped (category) view. `label === null` renders no
// header; `muted` is the small "More" header above the trailing single-offer bucket.
type SectionMeta = {
  label: string | null;
  count: number;
  fromCents: number | null;
  muted: boolean;
};
type DealSection = SectionListData<Offer, SectionMeta>;

// Within a comparison group, order by the active sort metric (cheapest €/kg, biggest
// discount, or lowest price) — same comparator as the flat list, so they stay consistent.
function withinGroup(items: Offer[], mode: SortMode): Offer[] {
  return [...items].sort((a, b) => compareOffers(a, b, mode));
}

// Turn the already-filtered + sorted category view into sections: each product with
// 2+ offers becomes a headed comparison group (biggest first, then A–Z); single-offer
// and ungrouped items collect into one trailing bucket sorted by the active toggle.
function buildSections(sorted: Offer[], mode: SortMode): DealSection[] {
  const byGroup = new Map<string, Offer[]>();
  const tail: Offer[] = [];
  for (const o of sorted) {
    if (o.group) {
      const arr = byGroup.get(o.group);
      if (arr) arr.push(o);
      else byGroup.set(o.group, [o]);
    } else {
      tail.push(o);
    }
  }

  const groups: DealSection[] = [];
  byGroup.forEach((items, key) => {
    if (items.length >= 2) {
      groups.push({
        key,
        data: withinGroup(items, mode),
        label: items[0].group_label ?? key,
        count: items.length,
        fromCents: Math.min(...items.map((o) => o.price_cents)),
        muted: false,
      });
    } else {
      tail.push(items[0]); // a lone product has nothing to compare — send it down
    }
  });
  groups.sort((x, y) => y.count - x.count || (x.label ?? '').localeCompare(y.label ?? ''));

  const tailSorted = [...tail].sort((a, b) => compareOffers(a, b, mode));
  if (tailSorted.length) {
    groups.push({
      key: '__rest__',
      data: tailSorted,
      label: groups.length ? 'More' : null, // only label the bucket when groups sit above
      count: tailSorted.length,
      fromCents: null,
      muted: true,
    });
  }
  return groups;
}

export default function DealsScreen() {
  const [plz, setPlz] = useState(DEFAULT_PLZ);
  const [storeName, setStoreName] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [plzModal, setPlzModal] = useState(false);

  const [cats, setCats] = useState<CategoryCount[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<Offer | null>(null);
  const [showNonFood, setShowNonFood] = useState(false);
  const [storesModal, setStoresModal] = useState(false);
  const [myStores, setMyStores] = useState<MyStore[]>([]);
  const [sortMode, setSortMode] = useState<SortMode>('discount');
  const [hiddenStores, setHiddenStores] = useState<string[]>([]); // persisted: chains hidden from the deals list
  const [specialDays, setSpecialDays] = useState(false); // session lens: only day-limited specials
  const [bioOnly, setBioOnly] = useState(false); // session lens: only organic ("Bio") offers
  const [basket, setBasket] = useState<BasketItem[]>([]);
  const [basketModal, setBasketModal] = useState(false);
  const [optionsModal, setOptionsModal] = useState(false);
  const [recipesModal, setRecipesModal] = useState(false);
  const [filterSheet, setFilterSheet] = useState(false);
  const [recipePrefs, setRecipePrefs] = useState<RecipePrefs>(DEFAULT_RECIPE_PREFS);
  const [alwaysHave, setAlwaysHave] = useState<BasketItem[]>([]);
  // Deals-cache / refresh status (stale-while-revalidate over the sleepy free backend).
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [updating, setUpdating] = useState(false);
  const [refreshFailed, setRefreshFailed] = useState(false);

  // Hydrate saved prefs once on mount, then let `load` run.
  useEffect(() => {
    (async () => {
      const stored = await getStoredPlz();
      if (stored) setPlz(stored);
      setShowNonFood(await getStoredShowNonFood());
      setMyStores(await getStoredMyStores());
      setSortMode(await getStoredSortMode());
      setHiddenStores(await getStoredHiddenStores());
      setBasket(await getStoredBasket());
      setRecipePrefs(await getStoredRecipePrefs());
      setAlwaysHave(await getStoredAlwaysHave());
      setReady(true);
    })();
  }, []);

  // Fetch fresh deals, update the view + re-cache. `hadData` = something is already on
  // screen (cache hit or a prior load), so a failure stays silent (no error screen).
  const revalidate = useCallback(
    async (hadData: boolean) => {
      setUpdating(true);
      setRefreshFailed(false);
      if (!hadData) setError(null);

      const fetchAll = () => Promise.all([api.offers({ plz }), api.categories(plz), api.stores()]);

      try {
        // Plain read first. On a sleepy free-tier cold start this can fail (timeout) or come
        // back empty — the ephemeral DB only boot-scrapes the default PLZ — so if there's
        // nothing, force an on-demand scrape for this PLZ (like the picker) and refetch.
        let result = await fetchAll().catch(() => null);
        if (!result || result[0].length === 0) {
          await api.scrape(plz);
          result = await fetchAll();
        }
        const [o, c, stores] = result;

        // Never clobber good cached deals with an empty result, and never cache empty —
        // otherwise a cold-backend refresh wipes the deals + poisons the cache.
        if (o.length === 0 && hadData) {
          setRefreshFailed(true);
          return;
        }

        const name = stores.find((s) => s.plz === plz)?.name ?? null;
        setOffers(o);
        setCats(c);
        setStoreName(name);
        const now = Date.now();
        setUpdatedAt(now);
        setError(null);
        if (o.length > 0) {
          setDealsCache({ plz, offers: o, cats: c, storeName: name, cachedAt: now });
        }
      } catch {
        setRefreshFailed(true);
        if (!hadData) setError(`Couldn't reach the API at ${api.base}.\nIs the backend running?`);
      } finally {
        setLoading(false);
        setUpdating(false);
      }
    },
    [plz],
  );

  // On launch / PLZ change: show the cached deals for this PLZ instantly (no spinner),
  // then refresh in the background. Only a true cold start (no cache) shows the spinner.
  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    (async () => {
      const cached = await getDealsCache();
      if (cancelled) return;
      const hit = !!cached && cached.plz === plz;
      // Flyers are weekly, so a cache from the current flyer week is still current: serve
      // it and skip the (sleepy) backend entirely. Only fetch when there's no cache or it's
      // past the cached week's Sunday. Pull-to-refresh always forces a fetch.
      const fresh = hit && cached != null && !dealsStale(cached.cachedAt);
      if (hit && cached) {
        setOffers(cached.offers);
        setCats(cached.cats);
        setStoreName(cached.storeName);
        setUpdatedAt(cached.cachedAt);
        setError(null);
        setLoading(false);
      } else {
        setOffers([]);
        setCats([]);
        setUpdatedAt(null);
        setLoading(true);
      }
      if (!fresh) revalidate(hit);
    })();
    return () => {
      cancelled = true;
    };
  }, [plz, ready, revalidate]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await revalidate(true);
    setRefreshing(false);
  }, [revalidate]);

  const onApplied = useCallback(async (newPlz: string, name: string | null) => {
    await setStoredPlz(newPlz);
    setStoreName(name);
    setSelected(null);
    setQuery('');
    setSpecialDays(false);
    setBioOnly(false);
    setPlz(newPlz);
    setPlzModal(false);
  }, []);

  const onChangeMyStores = useCallback((next: MyStore[]) => {
    setMyStores(next);
    setStoredMyStores(next);
  }, []);

  const onChangeBasket = useCallback((next: BasketItem[]) => {
    setBasket(next);
    setStoredBasket(next);
  }, []);

  const onChangeRecipePrefs = useCallback((next: RecipePrefs) => {
    setRecipePrefs(next);
    setStoredRecipePrefs(next);
  }, []);

  const onChangeAlwaysHave = useCallback((next: BasketItem[]) => {
    setAlwaysHave(next);
    setStoredAlwaysHave(next);
  }, []);

  // Options view actions. Each returns a short result string for the modal to show.
  const onClearCache = useCallback(async () => {
    await clearDealsCache();
    await revalidate(true); // force a fresh fetch, bypassing the weekly-authoritative cache
    return 'Cleared the cached deals and refreshed from the server.';
  }, [revalidate]);

  const onResetAll = useCallback(async () => {
    await clearAllData();
    setMyStores([]);
    setBasket([]);
    setShowNonFood(false);
    setSortMode('discount');
    setSelected(null);
    setQuery('');
    setHiddenStores([]);
    setSpecialDays(false);
    setBioOnly(false);
    if (plz !== DEFAULT_PLZ) {
      setPlz(DEFAULT_PLZ); // the [plz] effect reloads for the default PLZ (cache now empty)
    } else {
      await revalidate(true); // already on the default PLZ — just refresh
    }
    return 'Reset all app data to defaults.';
  }, [plz, revalidate]);

  const onRescrape = useCallback(async () => {
    const res = await api.scrape(plz);
    await revalidate(true);
    return `Re-scraped ${res.scraped} offers for ${plz}.`;
  }, [plz, revalidate]);

  const onWipeServer = useCallback(async () => {
    const res = await api.resetDb(plz);
    await clearDealsCache();
    await revalidate(true);
    return `Wiped the server DB (removed ${res.deleted}) and re-scraped ${res.scraped} offers.`;
  }, [plz, revalidate]);

  const onChangeSort = useCallback((mode: SortMode) => {
    setSortMode(mode);
    setStoredSortMode(mode);
  }, []);

  const onToggleNonFood = useCallback(() => {
    setShowNonFood((prev) => {
      const next = !prev;
      setStoredShowNonFood(next);
      if (!next && selected === 'household') setSelected(null);
      return next;
    });
  }, [selected]);

  // Chains present for this PLZ, in a preferred order, for the store filter.
  const presentChains = (() => {
    const set = new Set(offers.map((o) => o.chain));
    const ordered = CHAIN_ORDER.filter((c) => set.has(c));
    const extra = [...set].filter((c) => !CHAIN_ORDER.includes(c)).sort();
    return [...ordered, ...extra];
  })();
  // Per-chain offer total for the store-pill counts (static, whole-set, like the
  // category chip counts) — the loaded set is already server-deduped.
  const chainCounts = offers.reduce<Record<string, number>>((acc, o) => {
    acc[o.chain] = (acc[o.chain] ?? 0) + 1;
    return acc;
  }, {});
  // Active chains, for the header subline (e.g. "Lidl · REWE · Edeka").
  const chainsSub = presentChains.map(chainLabel).join(' · ');
  // Toggle a store's visibility (persisted); guarded so the last visible store can't be hidden.
  const onToggleStore = (chain: string) => {
    setHiddenStores((prev) => {
      const next = toggleHiddenStore(prev, chain, presentChains);
      setStoredHiddenStores(next);
      return next;
    });
  };
  const showAllStores = () => {
    setHiddenStores([]);
    setStoredHiddenStores([]);
  };

  // Everything is filtered client-side from the full PLZ set. The store filter is a
  // global lens (applies to both category and search); non-food is hidden unless
  // toggled on; a search matches name/brand across all categories (it ignores the
  // selected chip), otherwise the selected category filters.
  const q = query.trim().toLowerCase();
  const foodBase = showNonFood ? offers : offers.filter((o) => o.category !== 'household');
  const storeBase = filterByVisibleStores(foodBase, hiddenStores);
  // "Special days" is a global lens (like the store filter): keep only day-limited
  // specials (sale window shorter than the Mon–Sat week), regardless of today's date.
  const dayLimitedCount = offers.filter((o) => o.day_limited).length;
  const hasDayLimited = dayLimitedCount > 0;
  const base =
    specialDays && hasDayLimited ? storeBase.filter((o) => o.day_limited) : storeBase;
  // "Bio only" is another global lens: keep just organic offers (server-computed is_bio).
  const bioCount = offers.filter((o) => o.is_bio).length;
  const hasBio = bioCount > 0;
  const bioBase = bioOnly && hasBio ? base.filter((o) => o.is_bio) : base;
  const visibleOffers = q
    ? bioBase.filter(
        (o) =>
          o.name.toLowerCase().includes(q) ||
          (o.brand ?? '').toLowerCase().includes(q),
      )
    : selected
      ? bioBase.filter((o) => o.category === selected)
      : bioBase;

  // Re-sort the filtered view by the active mode (lowest price / biggest discount /
  // cheapest €/kg); offers missing the metric (no discount, no €/kg) sink to the bottom.
  const sorted = [...visibleOffers].sort((a, b) => compareOffers(a, b, sortMode));

  // Inside a selected category (and not searching), cluster offers by product so
  // competing prices sit together; the flat list stays for "All" and search.
  const grouped = !!selected && !q;
  const sections = grouped ? buildSections(sorted, sortMode) : [];

  // Household offer count for the Non-food control (deduped, from /api/categories).
  const nonFoodCount = cats.find((c) => c.category === 'household')?.count ?? null;
  // Active (non-default) filters → removable chips on the bar; their count badges "Filters".
  const filterChips = [
    hasHiddenPresent(presentChains, hiddenStores)
      ? {
          key: 'store',
          label: visibleStoreChains(presentChains, hiddenStores).map(chainLabel).join(' · '),
          onRemove: showAllStores,
        }
      : null,
    specialDays
      ? { key: 'days', label: 'Special days', onRemove: () => setSpecialDays(false) }
      : null,
    bioOnly ? { key: 'bio', label: 'Bio', onRemove: () => setBioOnly(false) } : null,
    showNonFood ? { key: 'nonfood', label: 'Non-food', onRemove: onToggleNonFood } : null,
  ].filter(Boolean) as { key: string; label: string; onRemove: () => void }[];
  const resetFilters = () => {
    showAllStores();
    setSpecialDays(false);
    setBioOnly(false);
    if (showNonFood) onToggleNonFood();
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.header}>
          <Pressable
            style={styles.location}
            onPress={() => setPlzModal(true)}
            hitSlop={6}
            accessibilityRole="button"
            accessibilityLabel="Change postal code"
          >
            <Icon name="location-outline" size={18} color={colors.accent} />
            <View style={styles.locationText}>
              <View style={styles.locationLine}>
                <Text style={styles.locName} numberOfLines={1}>
                  PLZ {plz}
                </Text>
                <Icon name="chevron-down" size={14} color={colors.muted} />
              </View>
              <Text style={styles.locSub} numberOfLines={1}>
                {chainsSub || storeName || 'Tap to set location'}
              </Text>
            </View>
          </Pressable>
          <View style={styles.headerActions}>
            <IconButton
              name="restaurant-outline"
              accessibilityLabel="Recipes"
              onPress={() => setRecipesModal(true)}
            />
            <IconButton
              name="cart-outline"
              accessibilityLabel="Basket"
              badge={basket.length}
              onPress={() => setBasketModal(true)}
            />
            <IconButton
              name="storefront-outline"
              accessibilityLabel="Stores"
              onPress={() => setStoresModal(true)}
            />
            <IconButton
              name="settings-outline"
              accessibilityLabel="Options"
              onPress={() => setOptionsModal(true)}
            />
          </View>
        </View>

        <UpdateStatus
          updatedAt={updatedAt}
          updating={updating}
          stale={dealsStale(updatedAt)}
          offline={refreshFailed}
        />

        <SearchBar value={query} onChange={setQuery} />

        <CategoryChips
          categories={cats}
          selected={selected}
          onSelect={setSelected}
          showNonFood={showNonFood}
        />

        <FilterBar
          sortLabel={sortLabel(sortMode)}
          chips={filterChips}
          onOpen={() => setFilterSheet(true)}
        />

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.accent} />
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Text style={styles.error}>{error}</Text>
          </View>
        ) : grouped ? (
          <SectionList
            style={styles.listFill}
            sections={sections}
            keyExtractor={(o) => String(o.id)}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="on-drag"
            stickySectionHeadersEnabled={false}
            renderItem={({ item }: { item: Offer }) => (
              <OfferCard offer={item} onPress={() => setActive(item)} />
            )}
            renderSectionHeader={({ section }: { section: DealSection }) =>
              section.label ? (
                <GroupHeader
                  label={section.label}
                  count={section.muted ? undefined : section.count}
                  fromCents={section.fromCents}
                  muted={section.muted}
                />
              ) : null
            }
            contentContainerStyle={styles.list}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={colors.muted}
              />
            }
            ListEmptyComponent={
              <View style={styles.center}>
                <Text style={styles.muted}>No deals for this PLZ / category yet.</Text>
              </View>
            }
          />
        ) : (
          <FlatList
            style={styles.listFill}
            data={sorted}
            keyExtractor={(o) => String(o.id)}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="on-drag"
            renderItem={({ item }) => (
              <OfferCard offer={item} onPress={() => setActive(item)} />
            )}
            contentContainerStyle={styles.list}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={colors.muted}
              />
            }
            ListEmptyComponent={
              <View style={styles.center}>
                <Text style={styles.muted}>
                  {q
                    ? `No deals match “${query.trim()}”.`
                    : 'No deals for this PLZ / category yet.'}
                </Text>
              </View>
            }
          />
        )}
      </KeyboardAvoidingView>

      <FlyerModal offer={active} onClose={() => setActive(null)} />
      <PlzModal
        visible={plzModal}
        initialPlz={plz}
        onClose={() => setPlzModal(false)}
        onApplied={onApplied}
      />
      <StoresModal
        visible={storesModal}
        plz={plz}
        myStores={myStores}
        onChangeMyStores={onChangeMyStores}
        onClose={() => setStoresModal(false)}
      />
      <BasketModal
        visible={basketModal}
        offers={offers}
        basket={basket}
        onChangeBasket={onChangeBasket}
        onClose={() => setBasketModal(false)}
      />
      <OptionsModal
        visible={optionsModal}
        plz={plz}
        updatedAt={updatedAt}
        apiBase={api.base}
        onClose={() => setOptionsModal(false)}
        onClearCache={onClearCache}
        onResetAll={onResetAll}
        onRescrape={onRescrape}
        onWipeServer={onWipeServer}
      />
      <RecipesModal
        visible={recipesModal}
        offers={offers}
        prefs={recipePrefs}
        onChangePrefs={onChangeRecipePrefs}
        alwaysHave={alwaysHave}
        onChangeAlwaysHave={onChangeAlwaysHave}
        onClose={() => setRecipesModal(false)}
      />
      <FilterSheet
        visible={filterSheet}
        onClose={() => setFilterSheet(false)}
        onReset={resetFilters}
        sortMode={sortMode}
        onChangeSort={onChangeSort}
        chains={presentChains}
        chainCounts={chainCounts}
        hiddenStores={hiddenStores}
        onToggleStore={onToggleStore}
        hasDayLimited={hasDayLimited}
        dayLimitedCount={dayLimitedCount}
        specialDays={specialDays}
        onChangeSpecialDays={setSpecialDays}
        hasBio={hasBio}
        bioCount={bioCount}
        bioOnly={bioOnly}
        onChangeBio={setBioOnly}
        showNonFood={showNonFood}
        nonFoodCount={nonFoodCount}
        onToggleNonFood={onToggleNonFood}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.md,
    paddingHorizontal: space.lg,
    paddingTop: space.md,
    paddingBottom: space.sm,
  },
  location: { flexDirection: 'row', alignItems: 'center', gap: space.sm, flexShrink: 1 },
  locationText: { flexShrink: 1 },
  locationLine: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  locName: { color: colors.text, fontSize: 17, fontWeight: '700', flexShrink: 1 },
  locSub: { color: colors.muted, fontSize: 12, marginTop: 1 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: space.sm, flexShrink: 0 },
  listFill: { flex: 1 },
  list: { paddingVertical: 6, paddingBottom: 24 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  error: { color: colors.badge, fontSize: 14, textAlign: 'center', lineHeight: 20 },
  muted: { color: colors.muted, fontSize: 14, textAlign: 'center' },
});
