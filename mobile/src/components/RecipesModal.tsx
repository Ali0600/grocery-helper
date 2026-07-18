import React, { useMemo, useState } from 'react';
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

import { GROCERY_CATALOG } from '../catalog';
import { chainColors, chainLabel } from '../chains';
import { RECIPES } from '../data/recipes';
import { CHAIN_ORDER } from '../dealFilters';
import { euro } from '../format';
import {
  activeRecipeStores,
  CUISINE_OPTIONS,
  DIET_OPTIONS,
  filterRecipes,
  MAX_RECIPE_STORES,
  recipeChains,
  ResolvedRecipe,
  scaleQty,
} from '../recipes';
import { defaultAlwaysHave } from '../storage';
import { colors } from '../theme';
import { BasketItem, Offer, RecipePrefs } from '../types';

type Props = {
  visible: boolean;
  offers: Offer[];
  prefs: RecipePrefs;
  onChangePrefs: (p: RecipePrefs) => void;
  alwaysHave: BasketItem[];
  onChangeAlwaysHave: (items: BasketItem[]) => void;
  onClose: () => void;
  /** Open an on-sale ingredient's deal detail. Only rows with a matched offer can call this. */
  onOpenOffer?: (o: Offer) => void;
  /** The deal detail, rendered INSIDE this sheet's AppModal so it presents from THIS sheet's view
   * controller rather than the shared root VC — a sibling modal is refused by iOS and the refusal
   * latches for the session. See LikesModal for the full explanation. */
  detail?: React.ReactNode;
};

const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' ');

export function RecipesModal({
  visible,
  offers,
  prefs,
  onChangePrefs,
  alwaysHave,
  onChangeAlwaysHave,
  onClose,
  onOpenOffer,
  detail,
}: Props) {
  const [editing, setEditing] = useState(false); // always-have editor sub-view
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({}); // recipe id -> steps shown

  const resolved = useMemo(
    () => filterRecipes(RECIPES.recipes, prefs, offers, alwaysHave),
    [prefs, offers, alwaysHave],
  );

  // Chains actually in this set (`offers` is already hidden-stores-filtered), in the app's usual
  // order — so a chain the user removed in the Stores modal simply has no chip here.
  const presentChains = useMemo(() => {
    const present = new Set(offers.map((o) => o.chain));
    return CHAIN_ORDER.filter((c) => present.has(c));
  }, [offers]);
  // Render the *active* selection, so a stale pick (chain hidden, PLZ switched) can't show as
  // selected while doing nothing.
  const activeStores = useMemo(() => activeRecipeStores(prefs.stores, offers), [prefs.stores, offers]);

  const set = (patch: Partial<RecipePrefs>) => onChangePrefs({ ...prefs, ...patch });

  const toggleStore = (chain: string) => {
    const cur = prefs.stores ?? [];
    const next = cur.includes(chain)
      ? cur.filter((c) => c !== chain)
      : // A third pick drops the oldest rather than being ignored — a tap that does nothing reads
        // as a broken chip.
        [...cur, chain].slice(-MAX_RECIPE_STORES);
    set({ stores: next });
  };

  // --- prefs controls ---
  const choiceRow = (label: string, options: readonly string[], value: string | null, onPick: (v: string | null) => void) => (
    <View style={styles.choiceRow}>
      <Text style={styles.choiceLabel}>{label}</Text>
      <View style={styles.chips}>
        {chip('Any', value == null, () => onPick(null))}
        {options.map((o) => chip(titleCase(o), value === o, () => onPick(o), o))}
      </View>
    </View>
  );

  // `a11y` overrides the announced name where the visible label is ambiguous on its own — a store
  // chip reading just "Lidl" is indistinguishable from the chain pill on every card below it.
  const chip = (label: string, active: boolean, onPress: () => void, key?: string, a11y?: string) => (
    <Pressable
      key={key ?? label}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={a11y ?? label}
      style={({ pressed }) => [styles.chip, active && styles.chipActive, pressed && styles.pressed]}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );

  const stepper = (label: string, value: number, min: number, max: number, onChange: (v: number) => void) => (
    <View style={styles.stepper}>
      <Text style={styles.choiceLabel}>{label}</Text>
      <Pressable
        onPress={() => onChange(Math.max(min, value - 1))}
        style={({ pressed }) => [styles.stepBtn, pressed && styles.pressed]}
        hitSlop={6}
      >
        <Text style={styles.stepBtnText}>−</Text>
      </Pressable>
      <Text style={styles.stepValue}>{value}</Text>
      <Pressable
        onPress={() => onChange(Math.min(max, value + 1))}
        style={({ pressed }) => [styles.stepBtn, pressed && styles.pressed]}
        hitSlop={6}
      >
        <Text style={styles.stepBtnText}>+</Text>
      </Pressable>
    </View>
  );

  // --- one recipe card ---
  const renderRecipe = (rr: ResolvedRecipe) => {
    const r = rr.recipe;
    const mult = prefs.servings / r.servings;
    const showSteps = expanded[r.id];
    const chains = recipeChains(rr); // how many shops this actually takes, from the live match
    return (
      <View key={r.id} style={styles.card}>
        <Text style={styles.recipeTitle}>{r.title}</Text>
        <Text style={styles.recipeMeta}>
          Serves {prefs.servings} · {r.timeMinutes} min · {r.tags.map(titleCase).join(' · ')}
        </Text>
        <Text style={styles.recipeSummary}>{r.summary}</Text>

        <View style={styles.costRow}>
          {rr.estCostCents != null ? (
            <Text style={styles.costPill}>≈ {euro(rr.estCostCents)} on sale</Text>
          ) : null}
          <Text style={styles.costMeta}>
            {rr.onSaleCount} on sale{rr.buyCount > 0 ? ` · ${rr.buyCount} to buy` : ''}
          </Text>
        </View>

        {/* Shown in every mode, not just when scoped: "how many shops is this?" is the thing the
            store scope exists to answer, and it's worth knowing before you pick one. */}
        {chains.length ? (
          <View style={styles.storeRow}>
            <Text style={styles.storeCount}>{chains.length === 1 ? '1 store' : `${chains.length} stores`}</Text>
            {chains.map((c) => (
              <View key={c} style={[styles.chainPill, { backgroundColor: chainColors(c).bg }]}>
                <Text style={[styles.chainPillText, { color: chainColors(c).fg }]}>{chainLabel(c)}</Text>
              </View>
            ))}
          </View>
        ) : null}

        {rr.ingredients.map((ri, i) => {
          // Only an on-sale ingredient has a matched offer (recipes.ts sets `offer` to null for
          // "have"/"buy"), so only those rows have a flyer to open — the rest stay inert.
          const offer = ri.role === 'on_sale' ? ri.offer : null;
          const body = (
            <>
              <Text style={styles.ingLabel} numberOfLines={1}>
                {ri.ing.label}
                {ri.ing.qty ? <Text style={styles.ingQty}> · {scaleQty(ri.ing.qty, mult)}</Text> : null}
              </Text>
              {offer ? (
                <View style={styles.ingRight}>
                  <View style={[styles.chainPill, { backgroundColor: chainColors(offer.chain).bg }]}>
                    <Text style={[styles.chainPillText, { color: chainColors(offer.chain).fg }]}>
                      {chainLabel(offer.chain)}
                    </Text>
                  </View>
                  <Text style={styles.ingPrice}>{euro(offer.price_cents)}</Text>
                </View>
              ) : ri.role === 'have' ? (
                <Text style={styles.tagHave}>have</Text>
              ) : (
                <Text style={styles.tagBuy}>buy</Text>
              )}
            </>
          );
          // The WHOLE row is the tap target, not just the price block: in the Likes sheet only the
          // ~45pt price responded, so tapping the obvious thing — the product name — did nothing
          // (fixed in PR #81). Don't shrink this back to the right-hand column.
          return offer && onOpenOffer ? (
            <Pressable
              key={i}
              style={({ pressed }) => [styles.ingRow, pressed && styles.pressed]}
              onPress={() => onOpenOffer(offer)}
              accessibilityRole="button"
              accessibilityLabel={`Open deal for ${offer.name}`}
            >
              {body}
            </Pressable>
          ) : (
            <View key={i} style={styles.ingRow}>
              {body}
            </View>
          );
        })}

        <Pressable
          onPress={() => setExpanded((e) => ({ ...e, [r.id]: !e[r.id] }))}
          style={({ pressed }) => [styles.stepsToggle, pressed && styles.pressed]}
          hitSlop={6}
        >
          <Text style={styles.stepsToggleText}>{showSteps ? 'Hide steps' : `Steps (${r.steps.length})`}</Text>
        </Pressable>
        {showSteps
          ? r.steps.map((s, i) => (
              <Text key={i} style={styles.step}>
                {i + 1}. {s}
              </Text>
            ))
          : null}
      </View>
    );
  };

  // --- always-have editor ---
  const remove = (key: string) => onChangeAlwaysHave(alwaysHave.filter((a) => a.key !== key));
  const addFromCatalog = (key: string) => {
    if (alwaysHave.some((a) => a.key === key)) return;
    const c = GROCERY_CATALOG.find((x) => x.key === key);
    if (c) onChangeAlwaysHave([...alwaysHave, { key: c.key, label: c.en, keywords: c.keywords, exclude: c.exclude }]);
  };
  const q = query.trim().toLowerCase();
  const suggestions = q
    ? GROCERY_CATALOG.filter(
        (c) =>
          !alwaysHave.some((a) => a.key === c.key) &&
          (c.en.toLowerCase().includes(q) || c.de.toLowerCase().includes(q)),
      ).slice(0, 12)
    : [];

  const renderEditor = () => (
    <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
      <Text style={styles.sectionHint}>
        Staples you always have — they count as available in recipes even when they’re not on sale.
      </Text>
      <View style={styles.chips}>
        {alwaysHave.map((a) => (
          <Pressable
            key={a.key}
            onPress={() => remove(a.key)}
            style={({ pressed }) => [styles.haveChip, pressed && styles.pressed]}
          >
            <Text style={styles.haveChipText}>{a.label} ✕</Text>
          </Pressable>
        ))}
      </View>
      <TextInput
        style={styles.input}
        value={query}
        onChangeText={setQuery}
        placeholder="Add a staple… (e.g. garlic / knoblauch)"
        placeholderTextColor={colors.muted}
        autoCorrect={false}
      />
      {suggestions.length ? (
        <View style={styles.chips}>
          {suggestions.map((c) => (
            <Pressable
              key={c.key}
              onPress={() => addFromCatalog(c.key)}
              style={({ pressed }) => [styles.chip, pressed && styles.pressed]}
            >
              <Text style={styles.chipText}>+ {c.en}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      <Pressable
        onPress={() => onChangeAlwaysHave(defaultAlwaysHave())}
        style={({ pressed }) => [styles.resetBtn, pressed && styles.pressed]}
      >
        <Text style={styles.resetText}>Reset to default staples</Text>
      </Pressable>
    </ScrollView>
  );

  // The AppModal below keeps animationType="fade" on purpose: this sheet HOSTS a nested modal (the
  // deal detail), and on react-native-web a nested slide-in never resolves its transform — the child
  // parks fully off-screen. Its testID sits on the AppModal, not an inner View, so it contains that
  // nested child (which is the containment the nesting test asserts).
  const renderMain = () => (
    <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
      <Text style={styles.sectionHint}>
        Recipes from this week’s deals · as of {RECIPES.generatedAt}
      </Text>

      {choiceRow('Diet', DIET_OPTIONS, prefs.diet, (v) => set({ diet: v }))}
      {choiceRow('Cuisine', CUISINE_OPTIONS, prefs.cuisine, (v) => set({ cuisine: v }))}
      {/* Scope the whole screen to one shop, or a two-store run. Hidden below two chains —
          there'd be nothing to choose between. */}
      {presentChains.length >= 2 ? (
        <View style={styles.choiceRow}>
          <Text style={styles.choiceLabel}>Shop at</Text>
          <View style={styles.chips}>
            {chip('Any store', activeStores.length === 0, () => set({ stores: [] }), 'any', 'Shop at any store')}
            {presentChains.map((c) =>
              chip(chainLabel(c), activeStores.includes(c), () => toggleStore(c), c, `Shop at ${chainLabel(c)}`),
            )}
          </View>
        </View>
      ) : null}
      <View style={styles.toggleRow}>
        {chip('Only on-sale', prefs.onlyOnSale, () => set({ onlyOnSale: !prefs.onlyOnSale }))}
        {chip('Cheapest €/kg', prefs.cheapestKg, () => set({ cheapestKg: !prefs.cheapestKg }))}
      </View>
      <View style={styles.toggleRow}>
        {stepper('Serves', prefs.servings, 1, 8, (v) => set({ servings: v }))}
        {stepper('Show', prefs.count, 3, 12, (v) => set({ count: v }))}
      </View>
      <Pressable
        onPress={() => {
          setQuery('');
          setEditing(true);
        }}
        style={({ pressed }) => [styles.haveSummary, pressed && styles.pressed]}
      >
        <Text style={styles.haveSummaryText}>Always have: {alwaysHave.length} staples</Text>
        <Text style={styles.change}>Edit</Text>
      </Pressable>

      {resolved.length ? (
        resolved.map(renderRecipe)
      ) : (
        <Text style={styles.empty}>No recipes match these filters. Try clearing a filter.</Text>
      )}
    </ScrollView>
  );

  return (
    <AppModal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
      testID="recipes-modal"
    >
      <KeyboardAvoidingView style={styles.backdrop} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            {editing ? (
              <Pressable onPress={() => setEditing(false)} hitSlop={10}>
                <Text style={styles.close}>‹ Back</Text>
              </Pressable>
            ) : (
              <View style={{ width: 48 }} />
            )}
            <Text style={styles.headerTitle}>{editing ? 'Always have' : 'Recipes'}</Text>
            {/* Labelled: the nested deal detail carries its own "Close", so an unlabelled one here
                is ambiguous both for a screen reader and for any label-based query. */}
            <Pressable onPress={onClose} hitSlop={10} accessibilityLabel="Close recipes">
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>
          {editing ? renderEditor() : renderMain()}
        </View>
      </KeyboardAvoidingView>
      {detail}
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
    maxHeight: '90%',
    borderWidth: 1,
    borderColor: colors.border,
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
  body: { padding: 16 },
  sectionHint: { color: colors.muted, fontSize: 12, marginBottom: 10 },
  choiceRow: { marginBottom: 8 },
  choiceLabel: { color: colors.muted, fontSize: 12, fontWeight: '700', marginBottom: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, rowGap: 6 },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  chipActive: { borderColor: colors.accent, backgroundColor: colors.card2 },
  chipText: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  chipTextActive: { color: colors.accent },
  pressed: { opacity: 0.7 },
  toggleRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8, alignItems: 'center' },
  stepper: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  stepBtn: {
    width: 28,
    height: 28,
    borderRadius: 999,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBtnText: { color: colors.accent, fontSize: 18, fontWeight: '800', lineHeight: 20 },
  stepValue: { color: colors.text, fontSize: 15, fontWeight: '700', minWidth: 18, textAlign: 'center' },
  haveSummary: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginTop: 12,
    marginBottom: 4,
  },
  haveSummaryText: { color: colors.text, fontSize: 14, fontWeight: '600' },
  change: { color: colors.accent, fontWeight: '700', fontSize: 13 },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: 14,
    marginTop: 12,
  },
  recipeTitle: { color: colors.text, fontSize: 16, fontWeight: '700' },
  recipeMeta: { color: colors.muted, fontSize: 12, marginTop: 2 },
  recipeSummary: { color: colors.muted, fontSize: 13, lineHeight: 18, marginTop: 6 },
  costRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8, marginBottom: 4 },
  costPill: {
    color: '#08130c',
    backgroundColor: colors.accent,
    fontSize: 12,
    fontWeight: '800',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    overflow: 'hidden',
  },
  costMeta: { color: colors.muted, fontSize: 12 },
  storeRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 6, marginBottom: 6 },
  storeCount: { color: colors.muted, fontSize: 12, fontWeight: '700' },
  ingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 5,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: 8,
  },
  ingLabel: { color: colors.text, fontSize: 14, flexShrink: 1 },
  ingQty: { color: colors.muted, fontSize: 13 },
  ingRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  chainPill: { borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  chainPillText: { fontSize: 11, fontWeight: '800' },
  ingPrice: { color: colors.text, fontSize: 14, fontWeight: '700' },
  tagHave: { color: colors.muted, fontSize: 12, fontWeight: '600' },
  tagBuy: { color: '#e8a33c', fontSize: 12, fontWeight: '700' },
  stepsToggle: { marginTop: 10 },
  stepsToggleText: { color: colors.accent, fontSize: 13, fontWeight: '700' },
  step: { color: colors.text, fontSize: 13, lineHeight: 19, marginTop: 6 },
  empty: { color: colors.muted, fontSize: 14, textAlign: 'center', marginTop: 24 },
  // editor
  haveChip: {
    borderWidth: 1,
    borderColor: colors.accent,
    backgroundColor: colors.card2,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  haveChipText: { color: colors.accent, fontSize: 13, fontWeight: '600' },
  input: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    color: colors.text,
    fontSize: 15,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginTop: 12,
    marginBottom: 10,
  },
  resetBtn: { marginTop: 16, alignItems: 'center', paddingVertical: 10 },
  resetText: { color: colors.muted, fontSize: 13, fontWeight: '600' },
});
