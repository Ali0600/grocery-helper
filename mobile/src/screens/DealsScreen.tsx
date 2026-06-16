import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
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
import { getStoredPlz, setStoredPlz } from '../storage';
import { colors } from '../theme';
import { CategoryCount, Offer } from '../types';

const DEFAULT_PLZ = '10115';

export default function DealsScreen() {
  const [plz, setPlz] = useState(DEFAULT_PLZ);
  const [storeName, setStoreName] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [plzModal, setPlzModal] = useState(false);

  const [cats, setCats] = useState<CategoryCount[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<Offer | null>(null);

  // Hydrate the saved PLZ once on mount, then let `load` run for it.
  useEffect(() => {
    (async () => {
      const stored = await getStoredPlz();
      if (stored) setPlz(stored);
      setReady(true);
    })();
  }, []);

  const load = useCallback(async () => {
    if (!ready) return;
    setError(null);
    try {
      const [o, c, stores] = await Promise.all([
        api.offers({ plz, category: selected ?? undefined }),
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
  }, [plz, selected, ready]);

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
    setPlz(newPlz);
    setPlzModal(false);
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.title}>Grocery deals</Text>
        <Pressable onPress={() => setPlzModal(true)} hitSlop={6}>
          <Text style={styles.subtitle} numberOfLines={1}>
            PLZ {plz}
            {storeName ? ` · ${storeName}` : ''} <Text style={styles.change}>Change</Text>
          </Text>
        </Pressable>
      </View>

      <CategoryChips categories={cats} selected={selected} onSelect={setSelected} />

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
          data={offers}
          keyExtractor={(o) => String(o.id)}
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
              <Text style={styles.muted}>No deals for this PLZ / category yet.</Text>
            </View>
          }
        />
      )}

      <FlyerModal offer={active} onClose={() => setActive(null)} />
      <PlzModal
        visible={plzModal}
        initialPlz={plz}
        onClose={() => setPlzModal(false)}
        onApplied={onApplied}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4 },
  title: { color: colors.text, fontSize: 24, fontWeight: '700' },
  subtitle: { color: colors.muted, fontSize: 13, marginTop: 2 },
  change: { color: colors.accent, fontWeight: '600' },
  listFill: { flex: 1 },
  list: { paddingVertical: 6, paddingBottom: 24 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  error: { color: colors.badge, fontSize: 14, textAlign: 'center', lineHeight: 20 },
  muted: { color: colors.muted, fontSize: 14 },
});
