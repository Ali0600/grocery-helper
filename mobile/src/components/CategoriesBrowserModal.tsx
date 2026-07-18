import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { headlineDiscountPct, headlinePriceCents } from '../appPrice';
import { CategoryCard } from '../dealFilters';
import { euro, pct } from '../format';
import { colors, font, radius, space } from '../theme';
import { Offer } from '../types';
import { AppModal } from './AppModal';
import { Icon } from './Icon';

export type BrowserMode = 'mine' | 'all';

// Used for the visible meta line AND the card's accessibility label, so a screen reader never
// announces "1 deals".
const dealCount = (n: number): string => `${n} deal${n === 1 ? '' : 's'}`;

// One deal row inside a category card: name, its discount badge (only when it actually has one —
// filler rows have no discount to badge), and the headline price.
function DealRow({ offer }: { offer: Offer }) {
  const discount = headlineDiscountPct(offer);
  return (
    <View style={styles.dealRow}>
      <Text style={styles.dealName} numberOfLines={1}>
        {offer.name}
      </Text>
      <View style={styles.dealRight}>
        {discount != null ? (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{pct(discount)}</Text>
          </View>
        ) : null}
        <Text style={styles.dealPrice}>{euro(headlinePriceCents(offer))}</Text>
      </View>
    </View>
  );
}

/**
 * The "My Categories" browser: every category as a wide card — name centred, deal count, and its
 * three headline deals — tap a card to open that category in the deals list.
 *
 * Two modals open FROM here, so both follow the iOS presentation rules (see AppModal / PR #81):
 *  * the Mine editor is passed in as `editor` and rendered INSIDE this modal (nested, never a
 *    sibling — RN presents from the first view controller up the responder chain);
 *  * "Compare stores" is a REPLACE, so the parent closes this sheet and opens Compare on dismissal.
 */
export function CategoriesBrowserModal(props: {
  visible: boolean;
  mode: BrowserMode;
  onChangeMode: (m: BrowserMode) => void;
  cards: CategoryCard[];
  hasMine: boolean;
  onOpenCategory: (slug: string) => void;
  onOpenEditor: () => void;
  onOpenCompare: () => void;
  onClose: () => void;
  onDismiss?: () => void;
  editor?: React.ReactNode;
}) {
  const { visible, mode, cards, onClose } = props;
  return (
    <AppModal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
      onDismiss={props.onDismiss}
      // On the AppModal, not the sheet View, so it contains the nested `editor` too — that
      // containment is what the iOS-nesting test asserts (see LikesModal's "likes-modal").
      testID="categories-browser"
    >
      <Pressable style={styles.backdrop} onPress={onClose} />
      <View style={styles.sheet}>
        <View style={styles.grabber} />
        <View style={styles.headerRow}>
          <Text style={styles.title}>My Categories</Text>
          <View style={styles.headerActions}>
            <Pressable onPress={props.onOpenEditor} hitSlop={8} accessibilityLabel="Edit my categories">
              <Icon name="settings-outline" size={21} color={colors.muted} />
            </Pressable>
            <Pressable onPress={onClose} hitSlop={8} accessibilityLabel="Close my categories">
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>
        </View>

        <View style={styles.modeRow}>
          {(['mine', 'all'] as BrowserMode[]).map((m) => (
            <Pressable
              key={m}
              onPress={() => props.onChangeMode(m)}
              style={[styles.modePill, mode === m && styles.modePillActive]}
              accessibilityRole="button"
              accessibilityState={{ selected: mode === m }}
            >
              <Text style={[styles.modeText, mode === m && styles.modeTextActive]}>
                {m === 'mine' ? 'Mine' : 'All'}
              </Text>
            </Pressable>
          ))}
        </View>

        <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
          {cards.map((card) => (
            <Pressable
              key={card.slug}
              style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
              onPress={() => props.onOpenCategory(card.slug)}
              accessibilityRole="button"
              accessibilityLabel={`Open ${card.label}, ${dealCount(card.total)}`}
            >
              <Text style={styles.cardTitle}>{card.label}</Text>
              <Text style={styles.cardMeta}>{dealCount(card.total)}</Text>
              {card.top.map((o) => (
                <DealRow key={o.id} offer={o} />
              ))}
            </Pressable>
          ))}

          {cards.length === 0 ? (
            <View style={styles.empty}>
              <Text style={styles.emptyText}>
                {mode === 'mine' && !props.hasMine
                  ? 'Pick the categories you shop and they’ll show up here.'
                  : 'No categories have deals right now — pull to refresh on the deals list.'}
              </Text>
              {mode === 'mine' && !props.hasMine ? (
                <Pressable style={styles.emptyBtn} onPress={props.onOpenEditor}>
                  <Text style={styles.emptyBtnText}>Pick categories</Text>
                </Pressable>
              ) : null}
            </View>
          ) : null}

          {/* Moved out of the header (a 7th icon overflows 375pt) — text-labelled here so it stays
              discoverable, and it belongs with categories: Compare works per product group. */}
          <Pressable style={styles.compareBtn} onPress={props.onOpenCompare}>
            <Icon name="git-compare-outline" size={16} color={colors.text} />
            <Text style={styles.compareText}>Compare stores</Text>
          </Pressable>
        </ScrollView>
      </View>
      {props.editor}
    </AppModal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  sheet: {
    backgroundColor: colors.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: space.lg,
    paddingBottom: space.xl,
    maxHeight: '92%',
  },
  grabber: {
    alignSelf: 'center',
    width: 36,
    height: 4,
    borderRadius: radius.pill,
    backgroundColor: colors.border,
    marginTop: space.sm,
    marginBottom: space.md,
  },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { ...font.h2, color: colors.text },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: space.lg },
  close: { ...font.label, color: colors.accent },
  modeRow: { flexDirection: 'row', gap: space.sm, marginTop: space.md },
  modePill: {
    paddingHorizontal: 16,
    height: 32,
    borderRadius: radius.pill,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modePillActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  modeText: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  modeTextActive: { color: colors.onAccent },
  body: { marginTop: space.md },
  bodyContent: { paddingBottom: space.md, gap: space.md },
  card: {
    backgroundColor: colors.bg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.md,
  },
  cardPressed: { opacity: 0.7 },
  cardTitle: { color: colors.text, fontSize: 15, fontWeight: '700', textAlign: 'center' },
  cardMeta: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 2,
    marginBottom: space.sm,
  },
  dealRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingVertical: 6,
    gap: space.sm,
  },
  dealName: { color: colors.text, fontSize: 12, flexShrink: 1 },
  dealRight: { flexDirection: 'row', alignItems: 'center', gap: space.sm, flexShrink: 0 },
  badge: {
    backgroundColor: colors.badge,
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  badgeText: { color: '#fff', fontSize: 10, fontWeight: '700' },
  dealPrice: { color: colors.accent, fontSize: 12, fontWeight: '700' },
  empty: { alignItems: 'center', paddingVertical: space.xl, gap: space.md },
  emptyText: { color: colors.muted, fontSize: 13, textAlign: 'center', lineHeight: 19 },
  emptyBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 10,
    paddingHorizontal: 22,
  },
  emptyBtnText: { color: colors.onAccent, fontSize: 14, fontWeight: '700' },
  compareBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.sm,
    height: 44,
    borderRadius: radius.md,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    marginTop: space.sm,
  },
  compareText: { color: colors.text, fontSize: 14, fontWeight: '600' },
});
