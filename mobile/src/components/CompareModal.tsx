import React, { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppModal } from './AppModal';

import { chainColors, chainLabel } from '../chains';
import { buildComparison } from '../compare';
import { euro } from '../format';
import { colors, font, radius, space } from '../theme';
import { CategoryCount, Offer } from '../types';
import { Icon } from './Icon';

// A product price face-off: pick a couple of stores + a category, and each product
// sub-group (Avocado, Butter…) shows every store's cheapest price side by side, the
// cheapest highlighted. Tap a price to open that deal. Reuses `offer.group`.
export function CompareModal({
  visible,
  offers,
  chains,
  categories,
  onOpenOffer,
  onClose,
  onOpenEdekaVs,
  onDismiss,
  detail,
}: {
  visible: boolean;
  offers: Offer[];
  chains: string[]; // chains present for this PLZ, in display order
  categories: CategoryCount[];
  onOpenOffer: (o: Offer) => void;
  onClose: () => void;
  onOpenEdekaVs?: () => void; // open the dedicated EDEKA-vs-E-center diff page
  /** iOS-only, fires once this sheet's view controller has actually gone. The EDEKA-vs-E-center
   * handoff REPLACES this sheet, and iOS refuses to present while the presenter is still
   * dismissing — so that swap has to wait for this. */
  onDismiss?: () => void;
  /** The deal detail — rendered inside this sheet's modal; see LikesModal for why. */
  detail?: React.ReactNode;
}) {
  const [selectedChains, setSelectedChains] = useState<string[]>(chains);
  const [category, setCategory] = useState<string | null>(null);

  // The stores actually being compared: the user's picks (in present order), or all
  // present chains until they've narrowed to a valid ≥2 selection.
  const compareChains = useMemo(() => {
    const sel = new Set(selectedChains.filter((c) => chains.includes(c)));
    const ordered = chains.filter((c) => sel.has(c));
    return ordered.length >= 2 ? ordered : chains;
  }, [selectedChains, chains]);

  const foodCats = useMemo(() => categories.filter((c) => c.category !== 'household'), [categories]);
  // Only offer categories that actually have a head-to-head (≥2 stores share a sub-group).
  const comparableCats = useMemo(
    () => foodCats.filter((c) => buildComparison(offers, compareChains, c.category).length > 0),
    [foodCats, offers, compareChains],
  );
  const activeCat =
    category && comparableCats.some((c) => c.category === category)
      ? category
      : comparableCats[0]?.category ?? null;
  const rows = useMemo(
    () => buildComparison(offers, compareChains, activeCat),
    [offers, compareChains, activeCat],
  );

  const toggleChain = (c: string) =>
    setSelectedChains(() => {
      const has = compareChains.includes(c);
      if (has && compareChains.length <= 2) return compareChains; // keep at least two
      return has ? compareChains.filter((x) => x !== c) : [...compareChains, c];
    });

  return (
    <AppModal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
      onDismiss={onDismiss}
      testID="compare-modal"
    >
      <View style={styles.root}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>Compare stores</Text>
              <Text style={styles.sub}>Cheapest price per product, side by side</Text>
            </View>
            <Pressable onPress={onClose} hitSlop={10} accessibilityLabel="Close">
              <Icon name="close" size={24} color={colors.muted} />
            </Pressable>
          </View>

          {onOpenEdekaVs && chains.includes('edeka') && chains.includes('edeka_center') && (
            <Pressable
              onPress={onOpenEdekaVs}
              style={styles.evsBtn}
              accessibilityLabel="EDEKA vs E center"
            >
              <Icon name="git-compare-outline" size={15} color={colors.accent} />
              <Text style={styles.evsBtnText}>EDEKA vs E center — exclusives + price gaps</Text>
              <Icon name="chevron-forward" size={15} color={colors.accent} />
            </Pressable>
          )}

          {/* Store multi-select */}
          <View style={styles.pillRow}>
            {chains.map((c) => {
              const on = compareChains.includes(c);
              return (
                <Pressable
                  key={c}
                  onPress={() => toggleChain(c)}
                  style={[styles.pill, on && styles.pillOn]}
                >
                  <Text style={[styles.pillText, on && styles.pillTextOn]}>{chainLabel(c)}</Text>
                </Pressable>
              );
            })}
          </View>

          {/* Category picker */}
          {comparableCats.length > 0 && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.catRow}
              contentContainerStyle={styles.catRowContent}
            >
              {comparableCats.map((c) => {
                const on = c.category === activeCat;
                return (
                  <Pressable
                    key={c.category}
                    onPress={() => setCategory(c.category)}
                    style={[styles.chip, on && styles.chipOn]}
                  >
                    <Text style={[styles.chipText, on && styles.chipTextOn]}>{c.label}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          )}

          {/* Column header (store names) */}
          {rows.length > 0 && (
            <View style={[styles.tr, styles.thead]}>
              <Text style={[styles.product, styles.muted]} numberOfLines={1}>
                Product
              </Text>
              {compareChains.map((c) => {
                const col = chainColors(c);
                return (
                  <View key={c} style={styles.cell}>
                    <Text style={[styles.colHead, { color: col.fg }]} numberOfLines={1}>
                      {chainLabel(c)}
                    </Text>
                  </View>
                );
              })}
            </View>
          )}

          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            {rows.length === 0 ? (
              <Text style={styles.empty}>
                No head-to-head products for these stores. Try more stores or another category.
              </Text>
            ) : (
              rows.map((row) => (
                <View key={row.key} style={styles.tr}>
                  <Text style={styles.product} numberOfLines={2}>
                    {row.label}
                  </Text>
                  {row.cells.map((cell) => (
                    <Pressable
                      key={cell.chain}
                      style={styles.cell}
                      disabled={!cell.offer}
                      onPress={() => cell.offer && onOpenOffer(cell.offer)}
                    >
                      {cell.offer ? (
                        <View style={[styles.priceBox, cell.isCheapest && styles.cheapest]}>
                          <Text style={[styles.price, cell.isCheapest && styles.priceCheapest]}>
                            {euro(cell.offer.price_cents)}
                          </Text>
                        </View>
                      ) : (
                        <Text style={styles.dash}>—</Text>
                      )}
                    </Pressable>
                  ))}
                </View>
              ))
            )}
          </ScrollView>
        </View>
      </View>
      {/* Inside this sheet's modal, never a sibling of it — see LikesModal for the full why. */}
      {detail}
    </AppModal>
  );
}

const CELL_W = 62;

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  sheet: {
    flex: 1,
    marginTop: 44,
    backgroundColor: colors.bg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: space.lg,
    paddingTop: space.md,
  },
  header: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' },
  title: { ...font.h2, color: colors.text },
  sub: { color: colors.muted, fontSize: 12, marginTop: 2 },
  evsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: space.md,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.accent,
    backgroundColor: colors.card2,
  },
  evsBtnText: { flex: 1, color: colors.accent, fontSize: 13, fontWeight: '700' },
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm, marginTop: space.md },
  pill: {
    paddingHorizontal: 14,
    height: 32,
    borderRadius: radius.pill,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillOn: { backgroundColor: colors.accent, borderColor: colors.accent },
  pillText: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  pillTextOn: { color: colors.onAccent },
  catRow: { marginTop: space.md, flexGrow: 0 },
  catRowContent: { gap: space.sm, paddingRight: space.lg },
  chip: {
    paddingHorizontal: 12,
    height: 30,
    borderRadius: radius.pill,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipOn: { backgroundColor: colors.card2, borderColor: colors.accent },
  chipText: { color: colors.muted, fontSize: 12, fontWeight: '600' },
  chipTextOn: { color: colors.text },
  thead: { borderBottomWidth: 1, borderBottomColor: colors.border, paddingBottom: 6, marginTop: space.md },
  tr: { flexDirection: 'row', alignItems: 'center', paddingVertical: 7 },
  product: { flex: 1, minWidth: 0, color: colors.text, fontSize: 13, fontWeight: '600', paddingRight: space.sm },
  muted: { color: colors.muted, fontWeight: '600' },
  cell: { width: CELL_W, alignItems: 'center' },
  colHead: { fontSize: 11, fontWeight: '800', letterSpacing: 0.2 },
  priceBox: { paddingHorizontal: 6, paddingVertical: 3, borderRadius: radius.sm },
  cheapest: { backgroundColor: colors.accent },
  price: { color: colors.text, fontSize: 13, fontWeight: '700' },
  priceCheapest: { color: colors.onAccent },
  dash: { color: colors.muted, fontSize: 13 },
  body: { paddingBottom: space.xl },
  empty: { color: colors.muted, fontSize: 14, textAlign: 'center', paddingVertical: 40, lineHeight: 20 },
});
