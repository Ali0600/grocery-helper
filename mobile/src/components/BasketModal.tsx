import React, { useEffect, useMemo, useState } from 'react';
import {
  KeyboardAvoidingView,  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { AppModal } from './AppModal';

import { buildPlan, matchOffers, norm, Plan, PlanLine } from '../basket';
import { subGroupItem, toItem } from '../basketResolve';
import { CatalogItem, GROCERY_CATALOG, POPULAR_KEYS } from '../catalog';
import { chainColors, chainLabel } from '../chains';
import { euro, fmtPricePerUnit } from '../format';
import { filterByStoreLens, storeLensLabel } from '../stores';
import { colors, space, tint } from '../theme';
import { BasketItem, Offer } from '../types';
import { Icon } from './Icon';
import { OfferCard } from './OfferCard';

type Props = {
  visible: boolean;
  offers: Offer[];
  basket: BasketItem[];
  onChangeBasket: (next: BasketItem[]) => void;
  onClose: () => void;
  /** The deals screen's "Only show" lens, already narrowed by `activeStoreLens` (so empty,
   * stale and full-coverage selections all arrive as `[]`). It scopes what the plan and the
   * per-item picker MATCH against — not what you can add. See `lensedFood` below. */
  storeLens?: string[];
  /** Open a deal's flyer from the picker. Tapping a picker card opens the deal — the same thing a
   * card press does everywhere else in the app — so picking gets its own ✓ button beside it. */
  onOpenOffer?: (o: Offer) => void;
  /** The deal detail, rendered INSIDE this sheet's AppModal so it presents from THIS sheet's view
   * controller, not the shared root VC (a sibling modal is refused by iOS and the refusal latches
   * for the session). See LikesModal for the full explanation. */
  detail?: React.ReactNode;
};

// Runaway guard on the "in this week's flyers" chips, NOT a display budget. ~100 sub-groups
// are typically on offer and all of them are shown: the section is grouped by category at the
// bottom of the scroll view, so it costs nothing above it.
//
// It was 30, and that was a bug: the list is ordered by category name, so 30 slots were spent
// on Bakery→Fish and Fruits/Vegetables — the whole point of the feature — fell off the end.
// Any cap small enough to bite truncates alphabetically, which is never what you want.
const MAX_LIVE_CHIPS = 400;

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
        // The row is a button that opens this item's deals, but it announced only its
        // concatenated text — a screen reader got the price with no hint anything opens.
        accessibilityRole={matchCount > 0 ? 'button' : undefined}
        accessibilityLabel={matchCount > 0 ? `Choose a deal for ${item.label}` : undefined}
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
// Each store lists the actual items under it — what you'd read off in the aisle — with the
// matched product under each one, so the card stands alone as a shopping list.
function PlanCard({ plan, storeLens }: { plan: Plan; storeLens: string[] }) {
  return (
    <View style={styles.planCard} testID="plan-card">
      <View style={styles.planHead}>
        <Text style={styles.planTitle}>Shopping plan</Text>
        {/* Say so when the plan is narrowed, or a lens that hides a cheaper store elsewhere
            reads as us simply missing the deal. */}
        {storeLens.length ? (
          <Text style={styles.planLensNote}>{storeLensLabel(storeLens)}</Text>
        ) : null}
      </View>
      {plan.byStore.map((g) => (
        <View key={g.chain}>
          <View style={styles.planRow}>
            <View style={styles.planLeft}>
              <Pill chain={g.chain} />
            </View>
            <Text style={styles.planSub}>{euro(g.subtotalCents)}</Text>
          </View>
          {g.lines.map((l) => (
            <View key={l.item.key} style={styles.planLine}>
              <View style={styles.planLineTop}>
                <Text style={styles.planLineName} numberOfLines={1}>
                  {l.item.label}
                </Text>
                <Text style={styles.planLinePrice}>{euro(l.offer?.price_cents ?? 0)}</Text>
              </View>
              {l.offer ? (
                <Text style={styles.planLineProduct} numberOfLines={1}>
                  {l.offer.name}
                </Text>
              ) : null}
            </View>
          ))}
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

export function BasketModal({
  visible,
  offers,
  basket,
  onChangeBasket,
  onClose,
  storeLens = [],
  onOpenOffer,
  detail,
}: Props) {
  const [text, setText] = useState('');
  const [picks, setPicks] = useState<Record<string, number>>({}); // item.key -> offer.id (session)
  const [viewing, setViewing] = useState<BasketItem | null>(null); // per-item "pick a deal" sub-view
  const [bioOnly, setBioOnly] = useState(false); // per-visit lens on the picker's deals

  // Entering the picker always starts unfiltered — no stale Bio lens from a previous item.
  const openPicker = (item: BasketItem) => {
    setBioOnly(false);
    setViewing(item);
  };

  // Reset the transient UI whenever the sheet closes.
  useEffect(() => {
    if (!visible) {
      setViewing(null);
      setBioOnly(false);
      setText('');
    }
  }, [visible]);

  // Drop picks for items that have left the basket. This sheet stays mounted for the screen's
  // lifetime (it's gated by `visible`, not by mounting), so without this a pick outlives its
  // item — and now that the deal detail and the swipe can both undo an add, taking something
  // out and putting it back is one tap, which would silently resurrect the old pick.
  useEffect(() => {
    setPicks((prev) => {
      const live = new Set(basket.map((b) => b.key));
      const kept = Object.keys(prev).filter((k) => live.has(k));
      if (kept.length === Object.keys(prev).length) return prev; // no orphans: keep identity
      return Object.fromEntries(kept.map((k) => [k, prev[k]]));
    });
  }, [basket]);

  // The basket is a grocery list — match against food only (drop household/non-food,
  // which the deals screen also hides by default). Kills traps like Birne→Glühbirne.
  const foodOffers = useMemo(() => offers.filter((o) => o.category !== 'household'), [offers]);

  // The store lens scopes MATCHING, not the add vocabulary. `lensedFood` feeds the plan and
  // the per-item picker — the two surfaces that answer "where do I buy this?" — while the
  // chips and typed adds below stay on the full `foodOffers`. A basket item is store-agnostic
  // ("I want kohlrabi"); the lens only says where you're shopping, so an item with no in-lens
  // deal honestly reads "No deal this week" rather than becoming unaddable. It also protects
  // an invariant: `addFromText` falls through `liveShown` before minting a `free:` key, so
  // lensing that path would make a typed add and a swipe-add of the same product mint
  // DIFFERENT keys and sit in the basket twice.
  const lensedFood = useMemo(
    () => filterByStoreLens(foodOffers, storeLens),
    [foodOffers, storeLens],
  );
  // buildPlan derives its single-store comparison from the array it's handed, so lensing the
  // input also scopes "vs Lidl alone" to the lens — which is what you want when you've said
  // those are the stores you're visiting. A pick made before the lens narrowed is silently
  // ignored (its offer id isn't in the pool) and falls back to the cheapest in-lens match;
  // it returns as soon as the lens clears. That's the honest behaviour, not a bug to fix.
  const plan = useMemo(() => buildPlan(basket, lensedFood, picks), [basket, lensedFood, picks]);

  // Every product sub-group actually in this week's flyers ("Kohlrabi", "Pfifferling"),
  // so the add list is not limited to the ~80 hand-curated catalog items. Resolved
  // through the SAME `subGroupItem` the swipe uses, so a chip-add and a swipe-add of one
  // product de-dupe to a single basket row. Memoized on `foodOffers` alone — this walks
  // ~1600 offers, so it must NOT depend on `text` or it would re-run per keystroke.
  const liveGroups = useMemo(() => {
    const seen = new Map<string, { item: BasketItem; label: string; categoryLabel: string }>();
    for (const o of foodOffers) {
      if (!o.group || seen.has(o.group)) continue;
      seen.set(o.group, {
        item: subGroupItem(o.group, o.group_label),
        label: o.group_label ?? o.group,
        categoryLabel: o.category_label ?? o.category,
      });
    }
    return [...seen.values()].sort(
      (a, b) => a.categoryLabel.localeCompare(b.categoryLabel) || a.label.localeCompare(b.label),
    );
  }, [foodOffers]);

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

  // What to render in the flyer section: drop anything already in the basket OR already
  // shown as a catalog chip above — a live "Pilz" resolves to the catalog `mushroom` key,
  // so without this it would appear twice. Then apply the typed filter, accepting BOTH the
  // German sub-group label and the resolved English catalog label, so either language finds
  // it with no translation table. Filtering runs over ~100 derived entries, not the offers.
  const liveShown = useMemo(() => {
    const shown = new Set([...basket.map((b) => b.key), ...suggestions.map((c) => c.key)]);
    const t = norm(text.trim());
    return liveGroups
      .filter((g) => !shown.has(g.item.key))
      .filter(
        (g) =>
          !t ||
          norm(g.label).includes(t) ||
          norm(g.item.label).includes(t) ||
          g.item.keywords.some((kw) => norm(kw).includes(t)),
      )
      .slice(0, MAX_LIVE_CHIPS);
  }, [liveGroups, suggestions, basket, text]);

  // Grouped by category so "which fruits are actually on offer?" is answerable at a
  // glance. `liveShown` is already sorted by category, so this is a single pass.
  const liveSections = useMemo(() => {
    const out: { categoryLabel: string; items: typeof liveShown }[] = [];
    for (const g of liveShown) {
      const last = out[out.length - 1];
      if (last && last.categoryLabel === g.categoryLabel) last.items.push(g);
      else out.push({ categoryLabel: g.categoryLabel, items: [g] });
    }
    return out;
  }, [liveShown]);

  const hasItem = (key: string) => basket.some((b) => b.key === key);

  const addItem = (item: BasketItem) => {
    if (!hasItem(item.key)) onChangeBasket([...basket, item]);
    setText('');
  };
  const addCatalog = (c: CatalogItem) => addItem(toItem(c));

  // Enter / "done": the best catalog match if the text matches one (curated keywords),
  // else a sub-group from this week's flyers, else the raw text as a free-text item.
  // The flyer step is not just convenience: typing "Kohlrabi" used to mint `free:kohlrabi`
  // while a swipe on the same deal mints `grp:kohlrabi` — two basket rows for one product.
  const addFromText = () => {
    const t = text.trim();
    if (!t) return;
    if (suggestions.length) {
      addCatalog(suggestions[0]);
      return;
    }
    if (liveShown.length) {
      addItem(liveShown[0].item);
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

  // The viewed item's matched deals (cheapest first), with an optional Bio-only lens.
  // The toggle only renders when the item has organic matches, so it can't empty the list.
  // Scoped by the store lens along with the plan: picking a deal from a lensed-out store
  // would record a pick the plan then ignores, silently reverting to the cheapest in-lens
  // match — an offer you can't act on is worse than not offering it.
  const pickerMatches = useMemo(
    () => (viewing ? matchOffers(lensedFood, viewing) : []),
    [lensedFood, viewing],
  );
  const pickerBioCount = useMemo(
    () => pickerMatches.filter((o) => o.is_bio).length,
    [pickerMatches],
  );
  const pickerOffers =
    bioOnly && pickerBioCount > 0 ? pickerMatches.filter((o) => o.is_bio) : pickerMatches;

  return (
    <AppModal
      visible={visible}
      transparent
      // Stays "fade": this sheet now HOSTS a nested modal, and a nested slide never resolves its
      // transform on react-native-web — the child parks fully off-screen (PR #89).
      animationType="fade"
      onRequestClose={onClose}
      // On the AppModal, not an inner View, so it contains the nested `detail` (PR #89).
      testID="basket-modal"
    >
      <KeyboardAvoidingView
        style={styles.backdrop}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Basket</Text>
            {/* Labelled: the nested deal detail carries its own "Close", so an unlabelled one here
                is ambiguous for a screen reader and for any label-based query. */}
            <Pressable onPress={onClose} hitSlop={10} accessibilityLabel="Close basket">
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
                {pickerBioCount > 0 ? (
                  <Pressable
                    onPress={() => setBioOnly((v) => !v)}
                    hitSlop={8}
                    accessibilityRole="button"
                    accessibilityLabel="Bio only"
                    style={[styles.bioPill, bioOnly && styles.bioPillOn]}
                  >
                    <Icon name="leaf" size={11} color={bioOnly ? tint.bio.fg : colors.muted} />
                    <Text style={[styles.bioPillText, bioOnly && styles.bioPillTextOn]}>
                      Bio ({pickerBioCount})
                    </Text>
                  </Pressable>
                ) : null}
              </View>
              <ScrollView contentContainerStyle={styles.list} keyboardShouldPersistTaps="handled">
                <Text style={styles.pickHint}>
                  {pickerOffers.length}
                  {bioOnly ? ' Bio' : ''} deal{pickerOffers.length === 1 ? '' : 's'} — tap one to
                  see it, or ✓ to use it in your plan.
                </Text>
                {pickerOffers.map((o) => (
                  <View key={o.id} style={styles.pickRow}>
                    <View style={styles.pickCard}>
                      {/* The card opens the deal, exactly as a card press does on every other
                          surface — so it keeps OfferCard's default "Open deal for …" label.
                          Without onOpenOffer there is nothing to open, and OfferCard drops its
                          button role rather than announcing an action it can't perform. */}
                      <OfferCard offer={o} onPress={onOpenOffer ? () => onOpenOffer(o) : undefined} />
                    </View>
                    {/* Picking gets its own target since tap now opens. A ✓ (not a chevron —
                        a forward-chevron reads as "go there", not "choose this"). */}
                    <Pressable
                      onPress={() => pickOffer(viewing, o)}
                      hitSlop={10}
                      style={({ pressed }) => [styles.pickBtn, pressed && styles.pressedDim]}
                      accessibilityRole="button"
                      accessibilityLabel={`Use ${o.name} in your plan`}
                    >
                      <Icon name="checkmark-circle-outline" size={22} color={colors.accent} />
                    </Pressable>
                  </View>
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
                        accessibilityRole="button"
                        accessibilityLabel={`Add ${c.en} to basket`}
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
                        onOpen={() => openPicker(line.item)}
                        onRemove={() => removeItem(line.item.key)}
                      />
                    ))}
                    <PlanCard plan={plan} storeLens={storeLens} />
                    <Pressable onPress={() => onChangeBasket([])} hitSlop={6} style={styles.clearAllBtn}>
                      <Text style={styles.clearAll}>Clear list</Text>
                    </Pressable>
                  </>
                )}

                {/* Every sub-category actually on offer this week — the curated catalog is
                    ~80 items and the flyers carry ~100 sub-groups, so products like Kohlrabi
                    or Pfifferling were unreachable from here. Below the plan so it never
                    pushes the basket down, and inside the ScrollView so it costs no height. */}
                {liveSections.length ? (
                  <View style={styles.liveSection}>
                    <Text style={styles.liveTitle}>In this week&apos;s flyers</Text>
                    {liveSections.map((sec) => (
                      <View key={sec.categoryLabel}>
                        <Text style={styles.liveCat}>{sec.categoryLabel}</Text>
                        <View style={styles.chips}>
                          {sec.items.map((g) => (
                            <Pressable
                              key={g.item.key}
                              onPress={() => addItem(g.item)}
                              accessibilityRole="button"
                              accessibilityLabel={`Add ${g.item.label} to basket`}
                              style={({ pressed }) => [styles.chip, pressed && styles.pressed]}
                            >
                              <Text style={styles.chipText}>+ {g.item.label}</Text>
                            </Pressable>
                          ))}
                        </View>
                      </View>
                    ))}
                  </View>
                ) : null}
              </ScrollView>
            </>
          )}
        </View>
      </KeyboardAvoidingView>
      {detail}
    </AppModal>
  );
}

const styles = StyleSheet.create({
  // Picker row: the card keeps its own margins and flexes; the ✓ sits beside it as a second,
  // independent tap target (tap the card = view the flyer, tap the ✓ = pick it for the plan).
  pickRow: { flexDirection: 'row', alignItems: 'center' },
  pickCard: { flex: 1 },
  pickBtn: {
    width: 32,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: space.md,
  },
  pressedDim: { opacity: 0.5 },
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
  liveSection: { marginTop: space.lg, paddingTop: space.md, borderTopWidth: 1, borderTopColor: colors.border },
  liveTitle: { color: colors.text, fontSize: 14, fontWeight: '700' },
  liveCat: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: space.md,
  },

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
  planHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  planTitle: { color: colors.text, fontSize: 15, fontWeight: '700' },
  planLensNote: { color: colors.muted, fontSize: 12 },
  planRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 5 },
  planLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  planSub: { color: colors.text, fontSize: 14, fontWeight: '600' },
  // Item lines sit indented under their store's pill, so the card reads as a shopping list.
  planLine: { paddingLeft: 8, paddingBottom: 4 },
  planLineTop: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 },
  planLineName: { color: colors.text, fontSize: 13, flexShrink: 1 },
  planLinePrice: { color: colors.muted, fontSize: 13 },
  planLineProduct: { color: colors.muted, fontSize: 11, marginTop: 1 },
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
  bioPill: {
    marginLeft: 'auto',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card2,
  },
  bioPillOn: { backgroundColor: tint.bio.bg, borderColor: tint.bio.fg },
  bioPillText: { color: colors.muted, fontSize: 12, fontWeight: '700' },
  bioPillTextOn: { color: tint.bio.fg },
});
