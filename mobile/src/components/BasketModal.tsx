import React, { useEffect, useMemo, useState } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { buildPlan, matchOffers, norm, Plan, PlanLine } from '../basket';
import { CatalogItem, GROCERY_CATALOG, POPULAR_KEYS } from '../catalog';
import { chainColors, chainLabel } from '../chains';
import { euro, fmtPricePerUnit } from '../format';
import { colors } from '../theme';
import { BasketItem, Offer } from '../types';
import { OfferCard } from './OfferCard';

type Props = {
  visible: boolean;
  offers: Offer[];
  basket: BasketItem[];
  onChangeBasket: (next: BasketItem[]) => void;
  onClose: () => void;
};

function Pill({ chain }: { chain: string }) {
  const c = chainColors(chain);
  return (
    <View style={[styles.pill, { backgroundColor: c.bg }]}>
      <Text style={[styles.pillText, { color: c.fg }]}>{chainLabel(chain)}</Text>
    </View>
  );
}

// One wishlist item + its cheapest current deal (or "No deal this week").
function BasketRow({ line, onOpen, onRemove }: { line: PlanLine; onOpen: () => void; onRemove: () => void }) {
  const { item, offer, matchCount } = line;
  const ppu = offer ? fmtPricePerUnit(offer.price_per_unit) : null;
  return (
    <View style={styles.row}>
      <Pressable
        style={styles.rowMain}
        onPress={matchCount > 0 ? onOpen : undefined}
        disabled={matchCount === 0}
      >
        <Text style={styles.itemName} numberOfLines={1}>
          {item.label}
        </Text>
        {offer ? (
          <>
            <View style={styles.matchLine}>
              <Pill chain={offer.chain} />
              <Text style={styles.price}>{euro(offer.price_cents)}</Text>
              {ppu ? <Text style={styles.ppu}>· {ppu}</Text> : null}
            </View>
            <Text style={styles.matchName} numberOfLines={1}>
              {offer.name}
              {matchCount > 1 ? ` · ${matchCount} deals ›` : ''}
            </Text>
          </>
        ) : (
          <Text style={styles.noDeal}>No deal this week</Text>
        )}
      </Pressable>
      <Pressable onPress={onRemove} hitSlop={8} style={({ pressed }) => [styles.removeBtn, pressed && styles.pressed]}>
        <Text style={styles.remove}>✕</Text>
      </Pressable>
    </View>
  );
}

// The cross-store shopping plan: picks grouped by store, totals, and the savings line.
function PlanCard({ plan }: { plan: Plan }) {
  return (
    <View style={styles.planCard}>
      <Text style={styles.planTitle}>Shopping plan</Text>
      {plan.byStore.map((g) => (
        <View key={g.chain} style={styles.planRow}>
          <View style={styles.planLeft}>
            <Pill chain={g.chain} />
            <Text style={styles.planItems}>
              {g.lines.length} item{g.lines.length > 1 ? 's' : ''}
            </Text>
          </View>
          <Text style={styles.planSub}>{euro(g.subtotalCents)}</Text>
        </View>
      ))}
      <View style={[styles.planRow, styles.planTotalRow]}>
        <Text style={styles.planTotalLabel}>
          Total{plan.byStore.length > 1 ? ` · ${plan.byStore.length} stores` : ''}
        </Text>
        <Text style={styles.planTotal}>{euro(plan.totalCents)}</Text>
      </View>
      {plan.savingsCents != null && plan.savingsCents > 0 && plan.byStore.length > 1 ? (
        <Text style={styles.savings}>
          Splitting across {plan.byStore.length} stores saves {euro(plan.savingsCents)} vs{' '}
          {chainLabel(plan.bestSingleChain ?? '')} alone.
        </Text>
      ) : null}
      {plan.missing.length ? (
        <Text style={styles.missing}>No deal this week: {plan.missing.map((m) => m.label).join(', ')}</Text>
      ) : null}
    </View>
  );
}

export function BasketModal({ visible, offers, basket, onChangeBasket, onClose }: Props) {
  const [text, setText] = useState('');
  const [picks, setPicks] = useState<Record<string, number>>({}); // item.key -> offer.id (session)
  const [viewing, setViewing] = useState<BasketItem | null>(null); // per-item "pick a deal" sub-view

  // Reset the transient UI whenever the sheet closes.
  useEffect(() => {
    if (!visible) {
      setViewing(null);
      setText('');
    }
  }, [visible]);

  // The basket is a grocery list — match against food only (drop household/non-food,
  // which the deals screen also hides by default). Kills traps like Birne→Glühbirne.
  const foodOffers = useMemo(() => offers.filter((o) => o.category !== 'household'), [offers]);
  const plan = useMemo(() => buildPlan(basket, foodOffers, picks), [basket, foodOffers, picks]);

  // Quick-add suggestions: filter the catalog by the typed text (English or German);
  // when empty, show the popular staples. Items already in the basket drop out.
  const suggestions = useMemo(() => {
    const inBasket = new Set(basket.map((b) => b.key));
    const pool = GROCERY_CATALOG.filter((c) => !inBasket.has(c.key));
    const t = norm(text.trim());
    if (!t) {
      return POPULAR_KEYS.map((k) => pool.find((c) => c.key === k))
        .filter((c): c is CatalogItem => !!c)
        .slice(0, 12);
    }
    return pool
      .filter(
        (c) =>
          norm(c.en).includes(t) ||
          norm(c.de).includes(t) ||
          c.key.includes(t) ||
          c.keywords.some((kw) => norm(kw).includes(t)),
      )
      .slice(0, 12);
  }, [text, basket]);

  const hasItem = (key: string) => basket.some((b) => b.key === key);

  const addCatalog = (c: CatalogItem) => {
    if (!hasItem(c.key)) {
      onChangeBasket([...basket, { key: c.key, label: c.en, keywords: c.keywords, exclude: c.exclude }]);
    }
    setText('');
  };

  // Enter / "done": add the best catalog match if the text matches one (curated
  // keywords), else add the raw text as a free-text item (matched literally).
  const addFromText = () => {
    const t = text.trim();
    if (!t) return;
    if (suggestions.length) {
      addCatalog(suggestions[0]);
      return;
    }
    const key = `free:${norm(t)}`;
    if (!hasItem(key)) onChangeBasket([...basket, { key, label: t, keywords: [norm(t)] }]);
    setText('');
  };

  const removeItem = (key: string) => onChangeBasket(basket.filter((b) => b.key !== key));
  const pickOffer = (item: BasketItem, offer: Offer) => {
    setPicks((prev) => ({ ...prev, [item.key]: offer.id }));
    setViewing(null);
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Basket</Text>
            <Pressable onPress={onClose} hitSlop={10}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>

          {viewing ? (
            <>
              <View style={styles.pickerBar}>
                <Pressable onPress={() => setViewing(null)} hitSlop={10}>
                  <Text style={styles.back}>‹ Back</Text>
                </Pressable>
                <Text style={styles.pickerTitle} numberOfLines={1}>
                  Deals for {viewing.label}
                </Text>
              </View>
              <ScrollView contentContainerStyle={styles.list} keyboardShouldPersistTaps="handled">
                <Text style={styles.pickHint}>Tap a deal to use it in your plan.</Text>
                {matchOffers(foodOffers, viewing).map((o) => (
                  <OfferCard key={o.id} offer={o} onPress={() => pickOffer(viewing, o)} />
                ))}
              </ScrollView>
            </>
          ) : (
            <>
              <View style={styles.addArea}>
                <View style={styles.inputBar}>
                  <TextInput
                    style={styles.input}
                    value={text}
                    onChangeText={setText}
                    placeholder="Add an item — e.g. Strawberry"
                    placeholderTextColor={colors.muted}
                    autoCorrect={false}
                    autoCapitalize="none"
                    returnKeyType="done"
                    submitBehavior="submit"
                    onSubmitEditing={addFromText}
                  />
                  {text.length > 0 ? (
                    <Pressable onPress={() => setText('')} hitSlop={10}>
                      <Text style={styles.clear}>✕</Text>
                    </Pressable>
                  ) : null}
                </View>
                {suggestions.length ? (
                  <View style={styles.chips}>
                    {suggestions.map((c) => (
                      <Pressable
                        key={c.key}
                        onPress={() => addCatalog(c)}
                        style={({ pressed }) => [styles.chip, pressed && styles.pressed]}
                      >
                        <Text style={styles.chipText}>+ {c.en}</Text>
                      </Pressable>
                    ))}
                  </View>
                ) : null}
              </View>

              <ScrollView contentContainerStyle={styles.list} keyboardShouldPersistTaps="handled">
                {basket.length === 0 ? (
                  <Text style={styles.empty}>
                    Add the groceries you want and we&apos;ll find the cheapest deals across stores. Tap a
                    suggestion above to start.
                  </Text>
                ) : (
                  <>
                    {plan.lines.map((line) => (
                      <BasketRow
                        key={line.item.key}
                        line={line}
                        onOpen={() => setViewing(line.item)}
                        onRemove={() => removeItem(line.item.key)}
                      />
                    ))}
                    <PlanCard plan={plan} />
                    <Pressable onPress={() => onChangeBasket([])} hitSlop={6} style={styles.clearAllBtn}>
                      <Text style={styles.clearAll}>Clear list</Text>
                    </Pressable>
                  </>
                )}
              </ScrollView>
            </>
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
    maxHeight: '88%',
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

  // Add area (input + suggestion chips)
  addArea: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4 },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card2,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 14,
  },
  input: { flex: 1, color: colors.text, fontSize: 16, paddingVertical: 11 },
  clear: { color: colors.muted, fontSize: 15, fontWeight: '600', paddingLeft: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 },
  chip: {
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  chipText: { color: colors.accent, fontSize: 13, fontWeight: '600' },

  list: { paddingVertical: 8, paddingBottom: 16 },
  empty: { color: colors.muted, fontSize: 14, lineHeight: 20, textAlign: 'center', padding: 28 },

  // Basket row
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowMain: { flex: 1, paddingRight: 12 },
  itemName: { color: colors.text, fontSize: 15, fontWeight: '700' },
  matchLine: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 5 },
  price: { color: colors.text, fontSize: 15, fontWeight: '700' },
  ppu: { color: colors.muted, fontSize: 12 },
  matchName: { color: colors.muted, fontSize: 12, marginTop: 3 },
  noDeal: { color: colors.muted, fontSize: 13, marginTop: 5, fontStyle: 'italic' },
  removeBtn: { paddingHorizontal: 8, paddingVertical: 6 },
  remove: { color: colors.muted, fontSize: 16, fontWeight: '700' },
  pressed: { opacity: 0.6 },

  pill: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  pillText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },

  // Plan card
  planCard: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    marginHorizontal: 12,
    marginTop: 12,
    padding: 14,
  },
  planTitle: { color: colors.text, fontSize: 15, fontWeight: '700', marginBottom: 10 },
  planRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 5 },
  planLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  planItems: { color: colors.muted, fontSize: 13 },
  planSub: { color: colors.text, fontSize: 14, fontWeight: '600' },
  planTotalRow: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    marginTop: 6,
    paddingTop: 10,
  },
  planTotalLabel: { color: colors.text, fontSize: 15, fontWeight: '700' },
  planTotal: { color: colors.accent, fontSize: 17, fontWeight: '800' },
  savings: { color: colors.accent, fontSize: 13, marginTop: 10, lineHeight: 18 },
  missing: { color: colors.muted, fontSize: 12, marginTop: 8, lineHeight: 17 },

  clearAllBtn: { alignSelf: 'center', marginTop: 16, paddingHorizontal: 16, paddingVertical: 8 },
  clearAll: { color: colors.muted, fontSize: 13, fontWeight: '600' },

  // Per-item picker sub-view
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
  pickHint: { color: colors.muted, fontSize: 13, paddingHorizontal: 16, paddingTop: 6, paddingBottom: 4 },
});
