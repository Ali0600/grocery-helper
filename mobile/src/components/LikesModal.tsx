import React, { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { chainColors, chainLabel } from '../chains';
import { euro, fmtPricePerUnit } from '../format';
import { matchLiked } from '../likes';
import { colors, tint } from '../theme';
import { LikedItem, Offer } from '../types';
import { AppModal } from './AppModal';
import { Icon } from './Icon';

// The Likes page: every product the user right-swiped, re-checked against the currently
// loaded offers. A liked product that's on sale again shows its cheapest current deal
// (tap → the deal detail); one whose exact name is gone falls back to its brand's other
// products ("More from McCain") or, brandless, its sub-group ("Other Tomaten") — see
// likes.ts for the matching tiers. Offers passed in follow the Basket/Recipes convention
// (hidden stores excluded). Tapped offers surface via onOpenOffer → DealsScreen's sibling
// FlyerModal (never a nested modal).

type Props = {
  visible: boolean;
  likes: LikedItem[];
  offers: Offer[];
  onRemove: (key: string) => void;
  onOpenOffer: (offer: Offer) => void;
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

function LikeRow({
  item,
  exact,
  related,
  relatedLabel,
  onOpenOffer,
  onRemove,
}: {
  item: LikedItem;
  exact: Offer[];
  related: Offer[];
  relatedLabel: string | null;
  onOpenOffer: (offer: Offer) => void;
  onRemove: () => void;
}) {
  const best = exact[0];
  const ppu = best ? fmtPricePerUnit(best.price_per_unit) : null;
  return (
    <View style={styles.row}>
      <View style={styles.rowMain}>
        <View style={styles.nameLine}>
          <Icon name="heart" size={12} color={tint.like.fg} />
          <Text style={styles.itemName} numberOfLines={1}>
            {item.name}
          </Text>
        </View>
        <Text style={styles.meta}>
          {chainLabel(item.chain)} · liked at {euro(item.likedPriceCents)}
        </Text>
        {best ? (
          <Pressable
            onPress={() => onOpenOffer(best)}
            accessibilityRole="button"
            accessibilityLabel={`Open deal for ${item.name}`}
            style={({ pressed }) => pressed && styles.pressed}
          >
            <View style={styles.matchLine}>
              <Pill chain={best.chain} />
              <Text style={styles.price}>{euro(best.price_cents)}</Text>
              {ppu ? <Text style={styles.ppu}>· {ppu}</Text> : null}
            </View>
            <Text style={styles.matchName} numberOfLines={1}>
              {best.name}
              {exact.length > 1 ? ` · ${exact.length} deals ›` : ' ›'}
            </Text>
          </Pressable>
        ) : (
          <>
            <Text style={styles.noDeal}>Not on sale this week</Text>
            {related.length ? (
              <View style={styles.related}>
                <Text style={styles.relatedTitle}>{relatedLabel}</Text>
                {related.map((o) => (
                  <Pressable
                    key={o.id}
                    onPress={() => onOpenOffer(o)}
                    accessibilityRole="button"
                    accessibilityLabel={`Open deal ${o.name}`}
                    style={({ pressed }) => [styles.relatedRow, pressed && styles.pressed]}
                  >
                    <Pill chain={o.chain} />
                    <Text style={styles.relatedName} numberOfLines={1}>
                      {o.name}
                    </Text>
                    <Text style={styles.relatedPrice}>{euro(o.price_cents)}</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
          </>
        )}
      </View>
      <Pressable
        onPress={onRemove}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={`Remove ${item.name} from likes`}
        style={({ pressed }) => [styles.removeBtn, pressed && styles.pressed]}
      >
        <Text style={styles.remove}>✕</Text>
      </Pressable>
    </View>
  );
}

export function LikesModal({ visible, likes, offers, onRemove, onOpenOffer, onClose }: Props) {
  // Re-match every like against the current offers; on-sale-now first, then newest like.
  const rows = useMemo(
    () =>
      likes
        .map((item) => ({ item, ...matchLiked(item, offers) }))
        .sort(
          (a, b) =>
            Number(b.exact.length > 0) - Number(a.exact.length > 0) ||
            b.item.likedAt - a.item.likedAt,
        ),
    [likes, offers],
  );

  return (
    <AppModal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Likes</Text>
            <Pressable onPress={onClose} hitSlop={10}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.list}>
            {rows.length === 0 ? (
              <Text style={styles.empty}>
                Swipe a deal to the right to like it. Liked products show up here whenever
                they&apos;re on sale again.
              </Text>
            ) : (
              rows.map(({ item, exact, related, relatedLabel }) => (
                <LikeRow
                  key={item.key}
                  item={item}
                  exact={exact}
                  related={related}
                  relatedLabel={relatedLabel}
                  onOpenOffer={onOpenOffer}
                  onRemove={() => onRemove(item.key)}
                />
              ))
            )}
          </ScrollView>
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

  list: { paddingVertical: 8, paddingBottom: 16 },
  empty: { color: colors.muted, fontSize: 14, lineHeight: 20, textAlign: 'center', padding: 28 },

  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowMain: { flex: 1, paddingRight: 12 },
  nameLine: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  itemName: { color: colors.text, fontSize: 15, fontWeight: '700', flexShrink: 1 },
  meta: { color: colors.muted, fontSize: 12, marginTop: 3 },
  matchLine: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 7 },
  price: { color: colors.text, fontSize: 15, fontWeight: '700' },
  ppu: { color: colors.muted, fontSize: 12 },
  matchName: { color: colors.muted, fontSize: 12, marginTop: 3 },
  noDeal: { color: colors.muted, fontSize: 13, marginTop: 6, fontStyle: 'italic' },

  related: { marginTop: 8 },
  relatedTitle: { color: tint.like.fg, fontSize: 12, fontWeight: '700', marginBottom: 4 },
  relatedRow: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 4 },
  relatedName: { color: colors.text, fontSize: 13, flexShrink: 1, flexGrow: 1 },
  relatedPrice: { color: colors.text, fontSize: 13, fontWeight: '700' },

  removeBtn: { paddingHorizontal: 8, paddingVertical: 6 },
  remove: { color: colors.muted, fontSize: 16, fontWeight: '700' },
  pressed: { opacity: 0.6 },

  pill: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  pillText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },
});
