import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  SectionList,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { api } from '../api';
import { chainLabel } from '../chains';
import { BasketModal } from '../components/BasketModal';
import { CategoryChips } from '../components/CategoryChips';
import { CompareModal } from '../components/CompareModal';
import { EdekaVsModal } from '../components/EdekaVsModal';
import { FlyerModal } from '../components/FlyerModal';
import { GroupHeader } from '../components/GroupHeader';
import { Icon } from '../components/Icon';
import { IconButton } from '../components/IconButton';
import { SwipeableOfferCard } from '../components/SwipeableOfferCard';
import { OptionsModal } from '../components/OptionsModal';
import { PlzModal } from '../components/PlzModal';
import { RecipesModal } from '../components/RecipesModal';
import { FilterBar } from '../components/FilterBar';
import { FilterSheet } from '../components/FilterSheet';
import { SearchBar } from '../components/SearchBar';
import { StoresModal } from '../components/StoresModal';
import { UpdateStatus } from '../components/UpdateStatus';
import {
  buildSections,
  chainCounts as tallyChainCounts,
  compareOffers,
  DealSection,
  filterDeals,
  presentChains as derivePresentChains,
} from '../dealFilters';
import { dealsStale } from '../format';
import { sortLabel } from '../sort';
import { filterByVisibleStores, hasHiddenPresent, toggleHiddenStore, visibleStoreChains } from '../stores';
import { resolveBasketItem } from '../basketResolve';
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
import { colors, radius, space } from '../theme';
import { BasketItem, CategoryCount, MyStore, Offer, RecipePrefs } from '../types';

// Override via mobile/.env (EXPO_PUBLIC_DEFAULT_PLZ) so a personal postal code isn't
// committed; falls back to a neutral central-Berlin default for the public bundle.
const DEFAULT_PLZ = process.env.EXPO_PUBLIC_DEFAULT_PLZ ?? '10115';

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
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [optionsModal, setOptionsModal] = useState(false);
  const [recipesModal, setRecipesModal] = useState(false);
  const [compareModal, setCompareModal] = useState(false);
  const [edekaVsModal, setEdekaVsModal] = useState(false);
  const [filterSheet, setFilterSheet] = useState(false);
  const [recipePrefs, setRecipePrefs] = useState<RecipePrefs>(DEFAULT_RECIPE_PREFS);
  const [alwaysHave, setAlwaysHave] = useState<BasketItem[]>([]);
  // Deals-cache / refresh status (stale-while-revalidate over the sleepy free backend).
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [updating, setUpdating] = useState(false);
  const [refreshFailed, setRefreshFailed] = useState(false);
  // Tracks the CURRENT plz so an in-flight revalidate for a previous PLZ can detect it's
  // stale and bail instead of clobbering the new PLZ's view + single-key cache.
  const plzRef = useRef(plz);
  useEffect(() => {
    plzRef.current = plz;
  }, [plz]);
  // Don't leave the toast timer running past unmount.
  useEffect(() => {
    return () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);

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
      const target = plz; // the PLZ this run fetches for; bail if the user switches away
      setUpdating(true);
      setRefreshFailed(false);
      if (!hadData) setError(null);

      const fetchAll = () =>
        Promise.all([api.offers({ plz: target }), api.categories(target), api.stores()]);

      try {
        // Plain read first. On a sleepy free-tier cold start this can fail (timeout) or come
        // back empty — the ephemeral DB only boot-scrapes the default PLZ — so if there's
        // nothing, force an on-demand scrape for this PLZ (like the picker) and refetch.
        let result = await fetchAll().catch(() => null);
        if (!result || result[0].length === 0) {
          await api.scrape(target);
          result = await fetchAll();
        }
        // A late response for a previous PLZ must not clobber the current one's view
        // (or overwrite the single-key deals cache); its own run owns nothing anymore.
        if (plzRef.current !== target) return;
        const [o, c, stores] = result;

        // Never clobber good cached deals with an empty result, and never cache empty —
        // otherwise a cold-backend refresh wipes the deals + poisons the cache.
        if (o.length === 0 && hadData) {
          setRefreshFailed(true);
          return;
        }

        const name = stores.find((s) => s.plz === target)?.name ?? null;
        setOffers(o);
        setCats(c);
        setStoreName(name);
        const now = Date.now();
        setUpdatedAt(now);
        setError(null);
        if (o.length > 0) {
          setDealsCache({ plz: target, offers: o, cats: c, storeName: name, cachedAt: now });
        }
      } catch {
        if (plzRef.current !== target) return;
        setRefreshFailed(true);
        if (!hadData) setError(`Couldn't reach the API at ${api.base}.\nIs the backend running?`);
      } finally {
        // A stale run must not flip the spinner/updating flags the current run owns.
        if (plzRef.current === target) {
          setLoading(false);
          setUpdating(false);
        }
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

  // Transient confirmation banner (used by swipe-to-add).
  const showToast = useCallback((msg: string) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 1900);
  }, []);

  // Swipe-left on a deal → add its sub-category (the same entry the "+" adds) to the
  // basket, de-duped by key so re-swiping the same product just re-confirms.
  // Reads the basket through a ref so this callback is STABLE — a `[basket]` dep would
  // give every add a new identity and re-render every swipeable row mid-gesture (the
  // suspected stuck-gesture / app-freeze trigger on the TestFlight build).
  const basketRef = useRef(basket);
  useEffect(() => {
    basketRef.current = basket;
  }, [basket]);
  const onAddToBasket = useCallback(
    (offer: Offer) => {
      const item = resolveBasketItem(offer);
      const current = basketRef.current;
      if (current.some((b) => b.key === item.key)) {
        showToast(`${item.label} is already in your basket`);
        return;
      }
      onChangeBasket([...current, item]);
      showToast(`Added ${item.label} to basket`);
    },
    [onChangeBasket, showToast],
  );

  // Stable per-row callbacks: rows are memoized, so nothing about an unrelated
  // re-render (toast in/out, filter tweaks) touches a row while a gesture is live.
  const openOffer = useCallback((o: Offer) => setActive(o), []);
  const renderOffer = useCallback(
    ({ item }: { item: Offer }) => (
      <SwipeableOfferCard offer={item} onPressOffer={openOffer} onAdd={onAddToBasket} />
    ),
    [openOffer, onAddToBasket],
  );

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

  // Derived data is memoized (the pipeline used to re-run 8+ passes over ~1400 offers
  // on every keystroke); the pure logic lives in dealFilters.ts where it's unit-tested.
  const presentChains = useMemo(() => derivePresentChains(offers), [offers]);
  const chainCounts = useMemo(() => tallyChainCounts(offers), [offers]);
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

  // Hidden stores apply EVERYWHERE the user shops from: the deals list (via filterDeals
  // below) and the Basket + Recipes matchers — hiding EDEKA means the basket must not
  // route you there as "cheapest". Compare keeps its own store picker (full set).
  const modalOffers = useMemo(
    () => filterByVisibleStores(offers, hiddenStores),
    [offers, hiddenStores],
  );

  const dayLimitedCount = useMemo(() => offers.filter((o) => o.day_limited).length, [offers]);
  const bioCount = useMemo(() => offers.filter((o) => o.is_bio).length, [offers]);
  const hasDayLimited = dayLimitedCount > 0;
  const hasBio = bioCount > 0;

  // Everything is filtered client-side from the full PLZ set. The store filter is a
  // global lens (applies to both category and search); non-food is hidden unless
  // toggled on; a search matches name/brand across all categories (it ignores the
  // selected chip), otherwise the selected category filters.
  const q = query.trim().toLowerCase();
  const visibleOffers = useMemo(
    () => filterDeals(offers, { showNonFood, hiddenStores, specialDays, bioOnly, query, selected }),
    [offers, showNonFood, hiddenStores, specialDays, bioOnly, query, selected],
  );

  // Re-sort the filtered view by the active mode (lowest price / biggest discount /
  // cheapest €/kg); offers missing the metric (no discount, no €/kg) sink to the bottom.
  const sorted = useMemo(
    () => [...visibleOffers].sort((a, b) => compareOffers(a, b, sortMode)),
    [visibleOffers, sortMode],
  );

  // Inside a selected category (and not searching), cluster offers by product so
  // competing prices sit together; the flat list stays for "All" and search.
  const grouped = !!selected && !q;
  const sections = useMemo(
    () => (grouped ? buildSections(sorted, sortMode) : []),
    [grouped, sorted, sortMode],
  );

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
              name="git-compare-outline"
              accessibilityLabel="Compare stores"
              onPress={() => setCompareModal(true)}
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
            initialNumToRender={10}
            maxToRenderPerBatch={10}
            windowSize={7}
            renderItem={renderOffer}
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
            initialNumToRender={10}
            maxToRenderPerBatch={10}
            windowSize={7}
            renderItem={renderOffer}
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

      {toast ? (
        <View style={styles.toast} pointerEvents="none">
          <Text style={styles.toastText}>{toast}</Text>
        </View>
      ) : null}

      <CompareModal
        visible={compareModal}
        offers={offers}
        chains={presentChains}
        categories={cats}
        onOpenOffer={setActive}
        onClose={() => setCompareModal(false)}
        onOpenEdekaVs={() => {
          setCompareModal(false);
          setEdekaVsModal(true);
        }}
      />
      <EdekaVsModal
        visible={edekaVsModal}
        offers={offers}
        onOpenOffer={setActive}
        onClose={() => setEdekaVsModal(false)}
      />
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
        offers={modalOffers}
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
        offers={modalOffers}
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
  toast: {
    position: 'absolute',
    bottom: 28,
    alignSelf: 'center',
    maxWidth: '90%',
    backgroundColor: colors.card2,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
  },
  toastText: { color: colors.text, fontSize: 13, fontWeight: '600', textAlign: 'center' },
});
