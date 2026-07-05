import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { AppModal } from './AppModal';

import { api } from '../api';
import { chainColors, chainLabel } from '../chains';
import { CHAIN_ORDER } from '../dealFilters';
import { colors } from '../theme';
import { MyStore, NearbyStore } from '../types';

// A row in the stores list. `placeholder` marks an ACTIVE chain the nearest-stores
// lookup (2.5 km) found no OSM branch for — rendered so the user can still tap
// Change (the picker searches a wider 6 km) and save their branch, e.g. an E center
// that sits just outside the nearest-list radius.
type StoreRow = NearbyStore & { placeholder?: boolean };

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

// A saved store reconstructed for display (no fresh distance until re-picked).
const toNearby = (m: MyStore): NearbyStore => ({
  chain: m.chain,
  label: m.label,
  name: m.name,
  address: m.address,
  lat: m.lat ?? 0,
  lng: m.lng ?? 0,
  distance_m: 0,
  active: false,
});
const toMyStore = (s: NearbyStore): MyStore => ({
  chain: s.chain,
  label: s.label,
  name: s.name,
  address: s.address,
  lat: s.lat,
  lng: s.lng,
});

// Two NearbyStores are the same branch if their address matches (or, lacking one,
// their coordinates are within ~11 m). Used to mark the current pick in the picker.
const sameBranch = (a: NearbyStore, b: NearbyStore): boolean =>
  a.chain === b.chain &&
  (a.address && b.address
    ? a.address === b.address
    : Math.abs(a.lat - b.lat) < 1e-4 && Math.abs(a.lng - b.lng) < 1e-4);

const branchKey = (s: NearbyStore): string =>
  `${s.chain}:${s.address ?? ''}:${s.lat.toFixed(5)},${s.lng.toFixed(5)}`;

export function StoresModal({ visible, plz, myStores, onChangeMyStores, onClose }: Props) {
  const [stores, setStores] = useState<StoreRow[]>([]);
  const [selected, setSelected] = useState<Record<string, NearbyStore>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // "Change branch" picker (in-modal; not a nested Modal).
  const [picking, setPicking] = useState<{ chain: string; label: string } | null>(null);
  const [branches, setBranches] = useState<NearbyStore[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [branchesError, setBranchesError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    setPicking(null);
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.nearbyStores(plz);
        if (cancelled) return;
        // Active chains we scrape deals for always get a row — if the 2.5 km nearest
        // lookup found no branch (e.g. the E center is a bit farther out), show a
        // placeholder whose Change button searches the picker's wider radius.
        const found = new Set(res.map((s) => s.chain));
        const placeholders: StoreRow[] = CHAIN_ORDER.filter((c) => !found.has(c)).map((c) => ({
          chain: c,
          label: chainLabel(c),
          name: chainLabel(c),
          address: null,
          lat: 0,
          lng: 0,
          distance_m: 0,
          active: true,
          placeholder: true,
        }));
        setStores([...res, ...placeholders]);
        // Seed the shown branch per chain from the nearest list, then overlay any
        // saved branch (the user's chosen store for that chain).
        const seed: Record<string, NearbyStore> = {};
        for (const s of res) seed[s.chain] = s;
        for (const m of myStores) seed[m.chain] = toNearby(m);
        setSelected(seed);
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
    // myStores intentionally omitted: add/change update `selected` directly below.
  }, [visible, plz]); // eslint-disable-line react-hooks/exhaustive-deps

  const savedFor = (chain: string) => myStores.find((m) => m.chain === chain);

  // One saved store per chain: Add/Change replaces, Remove drops it.
  const saveBranch = (s: NearbyStore) =>
    onChangeMyStores([...myStores.filter((m) => m.chain !== s.chain), toMyStore(s)]);
  const removeChain = (chain: string) =>
    onChangeMyStores(myStores.filter((m) => m.chain !== chain));

  const openPicker = async (chain: string, label: string) => {
    setPicking({ chain, label });
    setBranchesLoading(true);
    setBranchesError(null);
    setBranches([]);
    try {
      const res = await api.chainBranches(plz, chain);
      setBranches(res);
      if (res.length === 0) setBranchesError('No other branches found near this PLZ.');
    } catch {
      setBranchesError(`Couldn't reach the API at ${api.base}.`);
    } finally {
      setBranchesLoading(false);
    }
  };

  const pickBranch = (s: NearbyStore) => {
    setSelected((prev) => ({ ...prev, [s.chain]: s }));
    saveBranch(s); // picking a branch IS choosing your store — persist it
    setPicking(null);
  };

  return (
    <AppModal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Nearby stores</Text>
            <Pressable onPress={onClose} hitSlop={10}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>

          {picking ? (
            <>
              <View style={styles.pickerBar}>
                <Pressable onPress={() => setPicking(null)} hitSlop={10}>
                  <Text style={styles.back}>‹ Back</Text>
                </Pressable>
                <Text style={styles.pickerTitle} numberOfLines={1}>
                  {picking.label} near {plz}
                </Text>
              </View>
              {branchesLoading ? (
                <View style={styles.center}>
                  <ActivityIndicator color={colors.accent} />
                </View>
              ) : branchesError ? (
                <View style={styles.center}>
                  <Text style={styles.error}>{branchesError}</Text>
                </View>
              ) : (
                <ScrollView contentContainerStyle={styles.list}>
                  {branches.map((s) => {
                    const cur = selected[s.chain];
                    const isCurrent = cur && sameBranch(cur, s);
                    return (
                      <Pressable
                        key={branchKey(s)}
                        onPress={() => pickBranch(s)}
                        style={({ pressed }) => [styles.row, pressed && styles.pressed]}
                      >
                        <View style={styles.rowMain}>
                          <Text style={styles.name} numberOfLines={1}>
                            {s.name}
                          </Text>
                          <Text style={styles.meta} numberOfLines={1}>
                            {(s.address ?? 'Address unavailable') + ' · ' + fmtDist(s.distance_m)}
                          </Text>
                        </View>
                        <Text style={isCurrent ? styles.current : styles.choose}>
                          {isCurrent ? 'Selected' : 'Choose'}
                        </Text>
                      </Pressable>
                    );
                  })}
                </ScrollView>
              )}
            </>
          ) : (
            <>
              <Text style={styles.intro}>
                Deals are live for the chains marked Active. Tap Change on any store to
                pick the branch that&apos;s actually yours; Add saves it to your list.
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
                    const chain = s.chain;
                    const disp = selected[chain] ?? s;
                    const b = chainColors(chain);
                    const isSaved = !!savedFor(chain);
                    // A placeholder row displays its hint only while nothing better is
                    // known — a saved branch overlaid via `selected` replaces it.
                    const showingPlaceholder = disp === s && !!s.placeholder;
                    return (
                      <View key={chain} style={styles.row}>
                        <View style={styles.rowMain}>
                          <View style={styles.titleLine}>
                            <View style={[styles.badge, { backgroundColor: b.bg }]}>
                              <Text style={[styles.badgeText, { color: b.fg }]}>{s.label}</Text>
                            </View>
                            {!showingPlaceholder ? (
                              <Text style={styles.name} numberOfLines={1}>
                                {disp.name}
                              </Text>
                            ) : null}
                            {s.active ? (
                              <View style={styles.activeInline}>
                                <Text style={styles.activeInlineText}>Active</Text>
                              </View>
                            ) : null}
                          </View>
                          <Text style={styles.meta} numberOfLines={1}>
                            {showingPlaceholder
                              ? 'No branch found within 2.5 km — Change searches wider'
                              : (disp.address ?? 'Address unavailable') +
                                (disp.distance_m > 0 ? ' · ' + fmtDist(disp.distance_m) : '')}
                          </Text>
                        </View>

                        <View style={styles.actions}>
                          {isSaved ? (
                            <Pressable
                              onPress={() => removeChain(chain)}
                              style={({ pressed }) => [
                                styles.action,
                                styles.savedTag,
                                pressed && styles.pressed,
                              ]}
                            >
                              <Text style={styles.savedText}>Added ✓</Text>
                            </Pressable>
                          ) : !showingPlaceholder ? (
                            <Pressable
                              onPress={() => saveBranch(selected[chain] ?? s)}
                              style={({ pressed }) => [
                                styles.action,
                                styles.addBtn,
                                pressed && styles.pressed,
                              ]}
                            >
                              <Text style={styles.addText}>+ Add</Text>
                            </Pressable>
                          ) : null}
                          <Pressable
                            onPress={() => openPicker(chain, s.label)}
                            hitSlop={6}
                            style={({ pressed }) => [styles.changeBtn, pressed && styles.pressed]}
                          >
                            <Text style={styles.changeText}>Change</Text>
                          </Pressable>
                        </View>
                      </View>
                    );
                  })}
                </ScrollView>
              )}
            </>
          )}
        </View>
      </View>
    </AppModal>
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
  pickerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  back: { color: colors.accent, fontSize: 15, fontWeight: '600' },
  pickerTitle: { color: colors.text, fontSize: 15, fontWeight: '700', flexShrink: 1 },
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
  actions: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  action: {
    minWidth: 64,
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
  },
  pressed: { opacity: 0.6 },
  activeInline: {
    backgroundColor: 'rgba(61,220,132,0.16)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  activeInlineText: { color: colors.accent, fontSize: 10, fontWeight: '700' },
  savedTag: { backgroundColor: 'transparent', borderWidth: 1, borderColor: colors.accent },
  savedText: { color: colors.accent, fontSize: 13, fontWeight: '600' },
  addBtn: { backgroundColor: colors.accent },
  addText: { color: '#08130c', fontSize: 13, fontWeight: '700' },
  changeBtn: { paddingHorizontal: 8, paddingVertical: 8 },
  changeText: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  choose: { color: colors.accent, fontSize: 13, fontWeight: '700' },
  current: { color: colors.muted, fontSize: 13, fontWeight: '600' },
});
