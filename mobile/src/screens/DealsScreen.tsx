import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
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
import { colors } from '../theme';
import { CategoryCount, Offer } from '../types';

export default function DealsScreen() {
  const [cats, setCats] = useState<CategoryCount[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<Offer | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [o, c] = await Promise.all([
        api.offers({ category: selected ?? undefined }),
        api.categories(),
      ]);
      setOffers(o);
      setCats(c);
    } catch {
      setError(`Couldn't reach the API at ${api.base}.\nIs the backend running?`);
    } finally {
      setLoading(false);
    }
  }, [selected]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.title}>Berlin grocery deals</Text>
        <Text style={styles.subtitle}>PLZ 10115 · sorted by % off</Text>
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
              <Text style={styles.muted}>No deals in this category.</Text>
            </View>
          }
        />
      )}

      <FlyerModal offer={active} onClose={() => setActive(null)} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4 },
  title: { color: colors.text, fontSize: 24, fontWeight: '700' },
  subtitle: { color: colors.muted, fontSize: 13, marginTop: 2 },
  listFill: { flex: 1 },
  list: { paddingVertical: 6, paddingBottom: 24 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  error: { color: colors.badge, fontSize: 14, textAlign: 'center', lineHeight: 20 },
  muted: { color: colors.muted, fontSize: 14 },
});
