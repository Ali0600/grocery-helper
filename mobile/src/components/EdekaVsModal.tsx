import React, { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppModal } from './AppModal';

import { chainColors } from '../chains';
import { buildEdekaVs } from '../edekaVs';
import { cleanUnit, euro } from '../format';
import { colors, font, radius, space } from '../theme';
import { Offer } from '../types';
import { Icon } from './Icon';

// A focused EDEKA-vs-E-center diff. Two sections: same-named items whose price differs
// (cheapest per chain, biggest gap first, cheaper highlighted) and the products only
// E center carries. Reuses served offer fields (chain / name / price) — no backend. Tap
// a price or a row to open that deal (FlyerModal).
export function EdekaVsModal({
  visible,
  offers,
  onOpenOffer,
  onClose,
  detail,
}: {
  visible: boolean;
  offers: Offer[];
  onOpenOffer: (o: Offer) => void;
  onClose: () => void;
  /** The deal detail — rendered inside this sheet's modal; see LikesModal for why. */
  detail?: React.ReactNode;
}) {
  const { priceDiffs, ecenterOnly, hasBoth } = useMemo(() => buildEdekaVs(offers), [offers]);

  return (
    <AppModal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
      testID="edekavs-modal"
    >
      <View style={styles.root}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <View style={styles.headerText}>
              <Text style={styles.title}>EDEKA vs E center</Text>
              <Text style={styles.sub}>What differs between the two flyers</Text>
            </View>
            <Pressable onPress={onClose} hitSlop={10} accessibilityLabel="Close">
              <Icon name="close" size={24} color={colors.muted} />
            </Pressable>
          </View>

          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            {!hasBoth ? (
              <Text style={styles.empty}>
                Need both EDEKA and E center deals for this area. Add an E center in Stores, or
                refresh the deals.
              </Text>
            ) : (
              <>
                <View style={styles.sectionHead}>
                  <Icon name="git-compare-outline" size={16} color={colors.accent} />
                  <Text style={styles.sectionTitle}>Same item, different price</Text>
                  <Text style={styles.count}>{priceDiffs.length}</Text>
                </View>
                {priceDiffs.length === 0 ? (
                  <Text style={styles.note}>Shared items are all priced the same right now.</Text>
                ) : (
                  <>
                    <View style={[styles.tr, styles.thead]}>
                      <Text style={[styles.product, styles.mutedTxt]}>Product</Text>
                      <Text style={[styles.colHead, { color: chainColors('edeka').fg }]}>EDEKA</Text>
                      <Text style={[styles.colHead, { color: chainColors('edeka_center').fg }]}>
                        E center
                      </Text>
                    </View>
                    {priceDiffs.map((row) => (
                      <View key={row.key} style={[styles.tr, styles.rowSep]}>
                        <View style={styles.product}>
                          <Text style={styles.name} numberOfLines={2}>
                            {row.label}
                          </Text>
                          {cleanUnit(row.ecenter.unit ?? row.edeka.unit) ? (
                            <Text style={styles.unit}>
                              {cleanUnit(row.ecenter.unit ?? row.edeka.unit)}
                            </Text>
                          ) : null}
                        </View>
                        <Pressable style={styles.cell} onPress={() => onOpenOffer(row.edeka)}>
                          <View style={[styles.priceBox, row.cheaper === 'edeka' && styles.cheapest]}>
                            <Text
                              style={[styles.price, row.cheaper === 'edeka' && styles.priceCheapest]}
                            >
                              {euro(row.edeka.price_cents)}
                            </Text>
                          </View>
                        </Pressable>
                        <Pressable style={styles.cell} onPress={() => onOpenOffer(row.ecenter)}>
                          <View
                            style={[styles.priceBox, row.cheaper === 'ecenter' && styles.cheapest]}
                          >
                            <Text
                              style={[
                                styles.price,
                                row.cheaper === 'ecenter' && styles.priceCheapest,
                              ]}
                            >
                              {euro(row.ecenter.price_cents)}
                            </Text>
                          </View>
                        </Pressable>
                      </View>
                    ))}
                  </>
                )}

                <View style={[styles.sectionHead, styles.sectionGap]}>
                  <Icon name="storefront-outline" size={16} color={chainColors('edeka_center').fg} />
                  <Text style={styles.sectionTitle}>Only at E center</Text>
                  <Text style={styles.count}>{ecenterOnly.length}</Text>
                </View>
                {ecenterOnly.length === 0 ? (
                  <Text style={styles.note}>E center has nothing EDEKA doesn&apos;t right now.</Text>
                ) : (
                  ecenterOnly.map((o) => (
                    <Pressable key={o.id} style={styles.onlyRow} onPress={() => onOpenOffer(o)}>
                      <View style={styles.onlyLeft}>
                        <Text style={styles.name} numberOfLines={1}>
                          {o.name}
                        </Text>
                        <Text style={styles.unit} numberOfLines={1}>
                          {[o.category_label, cleanUnit(o.unit)].filter(Boolean).join(' · ')}
                        </Text>
                      </View>
                      <Text style={styles.onlyPrice}>{euro(o.price_cents)}</Text>
                    </Pressable>
                  ))
                )}
              </>
            )}
          </ScrollView>
        </View>
      </View>
      {/* Inside this sheet's modal, never a sibling of it — see LikesModal for the full why. */}
      {detail}
    </AppModal>
  );
}

const CELL_W = 64;

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
  headerText: { flex: 1, paddingRight: space.sm },
  title: { ...font.h2, color: colors.text },
  sub: { color: colors.muted, fontSize: 12, marginTop: 2 },
  body: { paddingTop: space.md, paddingBottom: space.xl },
  sectionHead: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: space.sm },
  sectionGap: { marginTop: space.xl },
  sectionTitle: { color: colors.text, fontSize: 14, fontWeight: '700' },
  count: { color: colors.muted, fontSize: 12, fontWeight: '700' },
  note: { color: colors.muted, fontSize: 13, paddingVertical: 6 },
  thead: { borderBottomWidth: 1, borderBottomColor: colors.border, paddingBottom: 6 },
  tr: { flexDirection: 'row', alignItems: 'center', paddingVertical: 7 },
  rowSep: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  product: { flex: 1, minWidth: 0, paddingRight: space.sm },
  name: { color: colors.text, fontSize: 13, fontWeight: '600' },
  unit: { color: colors.muted, fontSize: 11, marginTop: 1 },
  mutedTxt: { color: colors.muted, fontSize: 12, fontWeight: '600' },
  colHead: { width: CELL_W, textAlign: 'center', fontSize: 11, fontWeight: '800', letterSpacing: 0.2 },
  cell: { width: CELL_W, alignItems: 'center' },
  priceBox: { paddingHorizontal: 6, paddingVertical: 3, borderRadius: radius.sm },
  cheapest: { backgroundColor: colors.accent },
  price: { color: colors.text, fontSize: 13, fontWeight: '700' },
  priceCheapest: { color: colors.onAccent },
  onlyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  onlyLeft: { flex: 1, minWidth: 0, paddingRight: space.sm },
  onlyPrice: { color: colors.text, fontSize: 14, fontWeight: '700' },
  empty: { color: colors.muted, fontSize: 14, textAlign: 'center', paddingVertical: 40, lineHeight: 20 },
});
