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
import { CategoryChips } from '../components/CategoryChips';
import { FlyerModal } from '../components/FlyerModal';
import { GroupHeader } from '../components/GroupHeader';
import { OfferCard } from '../components/OfferCard';
import { PlzModal } from '../components/PlzModal';
import { SearchBar } from '../components/SearchBar';
import { SortToggle } from '../components/SortToggle';
import { StoreFilter } from '../components/StoreFilter';
import { StoresModal } from '../components/StoresModal';
import {
  getStoredMyStores,
  getStoredPlz,
  getStoredShowNonFood,
  getStoredSortMode,
  setStoredMyStores,
  setStoredPlz,
  setStoredShowNonFood,
  setStoredSortMode,
  SortMode,
} from '../storage';
import { colors } from '../theme';
import { CategoryCount, MyStore, Offer } from '../types';

const DEFAULT_PLZ = '10115';
// Preferred order for the store filter; any other chains follow, alphabetically.
const CHAIN_ORDER = ['lidl', 'rewe', 'edeka'];

// Compare two values, sending nulls to the end regardless of direction.
function byNullsLast(a: number | null, b: number | null, dir: 'asc' | 'desc'): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  return dir === 'asc' ? a - b : b - a;
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

// Within a comparison group, order by what's being compared: cheapest €/kg in 'unit'
// mode (no-€/kg items sink), else cheapest absolute price.
function withinGroup(items: Offer[], mode: SortMode): Offer[] {
  return [...items].sort((a, b) =>
    mode === 'unit'
      ? byNullsLast(a.unit_price_cents, b.unit_price_cents, 'asc')
      : a.price_cents - b.price_cents,
  );
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

  const tailSorted = [...tail].sort((a, b) =>
    mode === 'unit'
      ? byNullsLast(a.unit_price_cents, b.unit_price_cents, 'asc')
      : byNullsLast(a.discount_pct, b.discount_pct, 'desc'),
  );
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
  const [storeFilter, setStoreFilter] = useState<string | null>(null); // session lens; resets each launch

  // Hydrate saved prefs once on mount, then let `load` run.
  useEffect(() => {
    (async () => {
      const stored = await getStoredPlz();
      if (stored) setPlz(stored);
      setShowNonFood(await getStoredShowNonFood());
      setMyStores(await getStoredMyStores());
      setSortMode(await getStoredSortMode());
      setReady(true);
    })();
  }, []);

  const load = useCallback(async () => {
    if (!ready) return;
    setError(null);
    try {
      const [o, c, stores] = await Promise.all([
        api.offers({ plz }),
        api.categories(plz),
        api.stores(),
      ]);
      setOffers(o);
      setCats(c);
      setStoreName(stores.find((s) => s.plz === plz)?.name ?? null);
    } catch {
      setError(`Couldn't reach the API at ${api.base}.\nIs the backend running?`);
    } finally {
      setLoading(false);
    }
  }, [plz, ready]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const onApplied = useCallback(async (newPlz: string, name: string | null) => {
    await setStoredPlz(newPlz);
    setStoreName(name);
    setSelected(null);
    setQuery('');
    setStoreFilter(null);
    setPlz(newPlz);
    setPlzModal(false);
  }, []);

  const onChangeMyStores = useCallback((next: MyStore[]) => {
    setMyStores(next);
    setStoredMyStores(next);
  }, []);

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
  // Ignore a stale pick (e.g. the chain vanished after a PLZ change) -> show All.
  const effectiveStore = storeFilter && presentChains.includes(storeFilter) ? storeFilter : null;

  // Everything is filtered client-side from the full PLZ set. The store filter is a
  // global lens (applies to both category and search); non-food is hidden unless
  // toggled on; a search matches name/brand across all categories (it ignores the
  // selected chip), otherwise the selected category filters.
  const q = query.trim().toLowerCase();
  const foodBase = showNonFood ? offers : offers.filter((o) => o.category !== 'household');
  const base = effectiveStore ? foodBase.filter((o) => o.chain === effectiveStore) : foodBase;
  const visibleOffers = q
    ? base.filter(
        (o) =>
          o.name.toLowerCase().includes(q) ||
          (o.brand ?? '').toLowerCase().includes(q),
      )
    : selected
      ? base.filter((o) => o.category === selected)
      : base;

  // Re-sort the filtered view by the active mode (data arrives discount-sorted).
  // "Cheapest €/kg" ranks by normalized per-unit price; items without one sink.
  const sorted = [...visibleOffers].sort((a, b) =>
    sortMode === 'unit'
      ? byNullsLast(a.unit_price_cents, b.unit_price_cents, 'asc')
      : byNullsLast(a.discount_pct, b.discount_pct, 'desc'),
  );

  // Inside a selected category (and not searching), cluster offers by product so
  // competing prices sit together; the flat list stays for "All" and search.
  const grouped = !!selected && !q;
  const sections = grouped ? buildSections(sorted, sortMode) : [];

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.header}>
          <View style={styles.titleRow}>
            <Text style={styles.title}>Grocery deals</Text>
            <Pressable
              onPress={() => setStoresModal(true)}
              style={({ pressed }) => [styles.storesBtn, pressed && styles.storesBtnPressed]}
              hitSlop={6}
            >
              <Text style={styles.storesBtnText}>Stores</Text>
            </Pressable>
          </View>
          <Pressable onPress={() => setPlzModal(true)} hitSlop={6}>
            <Text style={styles.subtitle} numberOfLines={1}>
              PLZ {plz}
              {storeName ? ` · ${storeName}` : ''} <Text style={styles.change}>Change</Text>
            </Text>
          </Pressable>
        </View>

        <CategoryChips
          categories={cats}
          selected={selected}
          onSelect={setSelected}
          showNonFood={showNonFood}
          onToggleNonFood={onToggleNonFood}
        />

        {presentChains.length >= 2 && (
          <StoreFilter chains={presentChains} value={effectiveStore} onChange={setStoreFilter} />
        )}

        <SortToggle mode={sortMode} onChange={onChangeSort} />

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

        <SearchBar value={query} onChange={setQuery} />
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
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  header: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4 },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { color: colors.text, fontSize: 24, fontWeight: '700' },
  storesBtn: {
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  storesBtnPressed: { opacity: 0.7 },
  storesBtnText: { color: colors.accent, fontSize: 13, fontWeight: '700' },
  subtitle: { color: colors.muted, fontSize: 13, marginTop: 2 },
  change: { color: colors.accent, fontWeight: '600' },
  listFill: { flex: 1 },
  list: { paddingVertical: 6, paddingBottom: 24 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  error: { color: colors.badge, fontSize: 14, textAlign: 'center', lineHeight: 20 },
  muted: { color: colors.muted, fontSize: 14, textAlign: 'center' },
});
