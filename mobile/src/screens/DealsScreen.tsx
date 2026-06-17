import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { api } from '../api';
import { CategoryChips } from '../components/CategoryChips';
import { FlyerModal } from '../components/FlyerModal';
import { OfferCard } from '../components/OfferCard';
import { PlzModal } from '../components/PlzModal';
import { SearchBar } from '../components/SearchBar';
import { StoresModal } from '../components/StoresModal';
import {
  getStoredMyStores,
  getStoredPlz,
  getStoredShowNonFood,
  setStoredMyStores,
  setStoredPlz,
  setStoredShowNonFood,
} from '../storage';
import { colors } from '../theme';
import { CategoryCount, MyStore, Offer } from '../types';

const DEFAULT_PLZ = '10115';

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

  // Hydrate saved prefs once on mount, then let `load` run.
  useEffect(() => {
    (async () => {
      const stored = await getStoredPlz();
      if (stored) setPlz(stored);
      setShowNonFood(await getStoredShowNonFood());
      setMyStores(await getStoredMyStores());
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
    setPlz(newPlz);
    setPlzModal(false);
  }, []);

  const onChangeMyStores = useCallback((next: MyStore[]) => {
    setMyStores(next);
    setStoredMyStores(next);
  }, []);

  const onToggleNonFood = useCallback(() => {
    setShowNonFood((prev) => {
      const next = !prev;
      setStoredShowNonFood(next);
      if (!next && selected === 'household') setSelected(null);
      return next;
    });
  }, [selected]);

  // Everything is filtered client-side from the full PLZ set. Non-food is hidden
  // unless toggled on; a search matches name/brand across all categories (it
  // ignores the selected chip), otherwise the selected category filters.
  const q = query.trim().toLowerCase();
  const base = showNonFood ? offers : offers.filter((o) => o.category !== 'household');
  const visibleOffers = q
    ? base.filter(
        (o) =>
          o.name.toLowerCase().includes(q) ||
          (o.brand ?? '').toLowerCase().includes(q),
      )
    : selected
      ? base.filter((o) => o.category === selected)
      : base;

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

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.accent} />
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Text style={styles.error}>{error}</Text>
          </View>
        ) : (
          <FlatList
            style={styles.listFill}
            data={visibleOffers}
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
