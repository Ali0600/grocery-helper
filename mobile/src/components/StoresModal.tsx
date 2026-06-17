import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { api } from '../api';
import { colors } from '../theme';
import { MyStore, NearbyStore } from '../types';

type Props = {
  visible: boolean;
  plz: string;
  myStores: MyStore[];
  onChangeMyStores: (next: MyStore[]) => void;
  onClose: () => void;
};

function fmtDist(m: number): string {
  return m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1)} km`;
}

function badgeColors(chain: string): { bg: string; fg: string } {
  if (chain === 'lidl') return { bg: 'rgba(0,90,200,0.18)', fg: '#6ea8ff' };
  if (chain === 'rewe') return { bg: 'rgba(204,12,45,0.18)', fg: '#ff8597' };
  return { bg: colors.card2, fg: colors.muted };
}

const keyOf = (s: { chain: string; name: string }) => `${s.chain}:${s.name}`;

export function StoresModal({ visible, plz, myStores, onChangeMyStores, onClose }: Props) {
  const [stores, setStores] = useState<NearbyStore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.nearbyStores(plz);
        if (cancelled) return;
        setStores(res);
        if (res.length === 0) {
          setError("Couldn't find nearby stores right now. Pull up again in a moment.");
        }
      } catch {
        if (!cancelled) setError(`Couldn't reach the API at ${api.base}.`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [visible, plz]);

  const saved = new Set(myStores.map(keyOf));

  const add = (s: NearbyStore) =>
    onChangeMyStores([
      ...myStores,
      { chain: s.chain, label: s.label, name: s.name, address: s.address },
    ]);
  const remove = (s: NearbyStore) =>
    onChangeMyStores(myStores.filter((m) => keyOf(m) !== keyOf(s)));

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Nearby stores</Text>
            <Pressable onPress={onClose} hitSlop={10}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>

          <Text style={styles.intro}>
            Lidl &amp; REWE deals are live. Add other stores to save them — their deals are
            coming soon.
          </Text>

          {loading ? (
            <View style={styles.center}>
              <ActivityIndicator color={colors.accent} />
            </View>
          ) : error ? (
            <View style={styles.center}>
              <Text style={styles.error}>{error}</Text>
            </View>
          ) : (
            <ScrollView contentContainerStyle={styles.list}>
              {stores.map((s) => {
                const b = badgeColors(s.chain);
                const isSaved = saved.has(keyOf(s));
                return (
                  <View key={keyOf(s)} style={styles.row}>
                    <View style={styles.rowMain}>
                      <View style={styles.titleLine}>
                        <View style={[styles.badge, { backgroundColor: b.bg }]}>
                          <Text style={[styles.badgeText, { color: b.fg }]}>{s.label}</Text>
                        </View>
                        <Text style={styles.name} numberOfLines={1}>
                          {s.name}
                        </Text>
                      </View>
                      <Text style={styles.meta} numberOfLines={1}>
                        {(s.address ?? 'Address unavailable') + ' · ' + fmtDist(s.distance_m)}
                      </Text>
                    </View>

                    {s.active ? (
                      <View style={[styles.action, styles.activeTag]}>
                        <Text style={styles.activeText}>Active</Text>
                      </View>
                    ) : isSaved ? (
                      <Pressable
                        onPress={() => remove(s)}
                        style={({ pressed }) => [
                          styles.action,
                          styles.savedTag,
                          pressed && styles.pressed,
                        ]}
                      >
                        <Text style={styles.savedText}>Added ✓</Text>
                      </Pressable>
                    ) : (
                      <Pressable
                        onPress={() => add(s)}
                        style={({ pressed }) => [
                          styles.action,
                          styles.addBtn,
                          pressed && styles.pressed,
                        ]}
                      >
                        <Text style={styles.addText}>+ Add</Text>
                      </Pressable>
                    )}
                  </View>
                );
              })}
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingBottom: 24,
    borderWidth: 1,
    borderColor: colors.border,
    maxHeight: '82%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: { color: colors.text, fontSize: 17, fontWeight: '700' },
  close: { color: colors.accent, fontSize: 15, fontWeight: '600' },
  intro: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 18,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  center: { padding: 40, alignItems: 'center', justifyContent: 'center' },
  error: { color: colors.muted, fontSize: 14, textAlign: 'center', lineHeight: 20 },
  list: { paddingVertical: 8 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowMain: { flex: 1, paddingRight: 12 },
  titleLine: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  badge: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  badgeText: { fontSize: 11, fontWeight: '800', letterSpacing: 0.3 },
  name: { color: colors.text, fontSize: 15, fontWeight: '600', flexShrink: 1 },
  meta: { color: colors.muted, fontSize: 12, marginTop: 4 },
  action: {
    minWidth: 68,
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
  },
  pressed: { opacity: 0.7 },
  activeTag: { backgroundColor: 'rgba(61,220,132,0.16)' },
  activeText: { color: colors.accent, fontSize: 13, fontWeight: '700' },
  savedTag: { backgroundColor: 'transparent', borderWidth: 1, borderColor: colors.accent },
  savedText: { color: colors.accent, fontSize: 13, fontWeight: '600' },
  addBtn: { backgroundColor: colors.accent },
  addText: { color: '#08130c', fontSize: 13, fontWeight: '700' },
});
