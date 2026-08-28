import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { AppModal } from './AppModal';
import { FlyerPagesView } from './FlyerPagesView';

import { api } from '../api';
import { chainColors, chainLabel } from '../chains';
import { CHAIN_ORDER } from '../dealFilters';
import { dealsStale } from '../format';
import { getFlyerPagesCache, setFlyerPagesCache } from '../storage';
import { colors, radius } from '../theme';
import { FlyerPagesMap, MyStore, NearbyStore } from '../types';

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
  /** Chains whose deals are hidden. This — not `myStores` — is what the deals list,
   * Basket and Recipes actually filter on, so Add/Added reads and writes it. */
  hiddenStores: string[];
  onToggleStore: (chain: string) => void;
  /** Deals currently loaded per chain, so a row can show what adding it actually got you. */
  chainCounts: Record<string, number>;
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

export function StoresModal({
  visible,
  plz,
  myStores,
  onChangeMyStores,
  hiddenStores,
  onToggleStore,
  chainCounts,
  onClose,
}: Props) {
  const [stores, setStores] = useState<StoreRow[]>([]);
  const [selected, setSelected] = useState<Record<string, NearbyStore>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // "Change branch" picker (in-modal; not a nested Modal).
  const [picking, setPicking] = useState<{ chain: string; label: string } | null>(null);
  const [branches, setBranches] = useState<NearbyStore[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [branchesError, setBranchesError] = useState<string | null>(null);

  // This week's flyer scans, `{chain: [url, ...]}`. A chain the backend has no pages for is
  // ABSENT from the map, and that absence is the whole gate for the "View flyer" link —
  // no hardcoded list of which chains have a flyer, which would drift the moment one is
  // added (and would have to special-case dm, whose publisher serves an empty brochure).
  const [flyerPages, setFlyerPages] = useState<FlyerPagesMap>({});
  const [viewingFlyer, setViewingFlyer] = useState<{ chain: string; label: string } | null>(null);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    setPicking(null);
    setViewingFlyer(null);
    // Flyer pages load beside the stores, with their OWN try/catch: a backend that predates
    // /api/flyer-pages 404s, and that must cost the links, never the stores list.
    (async () => {
      try {
        const cached = await getFlyerPagesCache();
        if (cancelled) return;
        if (cached && cached.plz === plz && !dealsStale(cached.cachedAt)) {
          setFlyerPages(cached.byChain);
          return; // flyers are weekly, like the deals cache — a fresh one asks nothing
        }
        const byChain = await api.flyerPages(plz);
        if (cancelled) return;
        setFlyerPages(byChain);
        await setFlyerPagesCache({ plz, byChain, cachedAt: Date.now() });
      } catch {
        if (!cancelled) setFlyerPages({});
      }
    })();
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

  // One saved branch per chain — this is `myStores`' only remaining job: remembering WHICH
  // branch is yours (for display). Which chains' *deals* you see is `hiddenStores`.
  const saveBranch = (s: NearbyStore) =>
    onChangeMyStores([...myStores.filter((m) => m.chain !== s.chain), toMyStore(s)]);

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
    // ...and choosing your store implies wanting its deals, so un-hide it.
    if (hiddenStores.includes(s.chain)) onToggleStore(s.chain);
    setPicking(null);
  };

  return (
    <AppModal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
      testID="stores-modal"
    >
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Nearby stores</Text>
            {/* Named, because the flyer view nested below carries its own Back and this
                sheet is no longer the only thing with a dismiss control in it. */}
            <Pressable
              onPress={onClose}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel="Close stores"
            >
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>

          {viewingFlyer ? (
            <FlyerPagesView
              label={viewingFlyer.label}
              pages={flyerPages[viewingFlyer.chain] ?? []}
              onBack={() => setViewingFlyer(null)}
            />
          ) : picking ? (
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
                Added stores show their deals in your list — tap Added to hide one, Add to
                bring it back. Change picks the branch that&apos;s actually yours.
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
                    // "Added" == this chain's deals are shown. Default (untouched) is
                    // added, because `hiddenStores` is a hidden-set — so a chain we track
                    // reads as added without the user having to do anything, and a newly
                    // scraped chain (ALDI) arrives already on.
                    const isAdded = !hiddenStores.includes(chain);
                    const count = chainCounts[chain] ?? 0;
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
                          {/* What adding this store actually got you. 0 on an active chain
                              means the last scrape brought nothing back for it — say so
                              rather than leaving an "Added ✓" that shows no deals. */}
                          {s.active ? (
                            <Text style={styles.dealCount} numberOfLines={1}>
                              {count > 0
                                ? `${count} deal${count === 1 ? '' : 's'}`
                                : 'No deals loaded — pull to refresh'}
                            </Text>
                          ) : (
                            <Text style={styles.soon} numberOfLines={1}>
                              Deals coming soon
                            </Text>
                          )}
                          {/* Gated on the DATA, never on a list of "chains with a flyer":
                              the backend omits a chain it captured no pages for, which
                              covers dm (no brochure, ever) and a chain whose scrape failed
                              without either needing to be named here. */}
                          {(flyerPages[chain]?.length ?? 0) > 0 ? (
                            <Pressable
                              onPress={() => setViewingFlyer({ chain, label: s.label })}
                              accessibilityRole="button"
                              accessibilityLabel={`View ${s.label} flyer`}
                              hitSlop={6}
                              style={styles.flyerChip}
                            >
                              <Text style={styles.flyerChipText}>View flyer ›</Text>
                            </Pressable>
                          ) : null}
                        </View>

                        <View style={styles.actions}>
                          {/* Add/Added only for chains we scrape: it means "show this
                              store's deals", which is meaningless without any. */}
                          {s.active ? (
                            <Pressable
                              onPress={() => onToggleStore(chain)}
                              accessibilityRole="button"
                              accessibilityLabel={
                                isAdded ? `Hide ${s.label} deals` : `Show ${s.label} deals`
                              }
                              style={({ pressed }) => [
                                styles.action,
                                isAdded ? styles.savedTag : styles.addBtn,
                                pressed && styles.pressed,
                              ]}
                            >
                              <Text style={isAdded ? styles.savedText : styles.addText}>
                                {isAdded ? 'Added ✓' : '+ Add'}
                              </Text>
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
  dealCount: { color: colors.accent, fontSize: 12, fontWeight: '600', marginTop: 2 },
  soon: { color: colors.muted, fontSize: 12, fontStyle: 'italic', marginTop: 2 },
  // A bordered chip, NOT another line of accent text: `dealCount` directly above is already
  // accent 12/600, and an identical-looking line that happens to be tappable reads as more
  // of the same information. The border and the chevron are what say "this does something".
  flyerChip: {
    alignSelf: 'flex-start',
    marginTop: 6,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
  },
  flyerChipText: { color: colors.accent, fontSize: 12, fontWeight: '600' },
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
