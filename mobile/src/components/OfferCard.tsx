import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { hasAppDeal, headlineDiscountPct, headlinePriceCents, headlineStrikeCents } from '../appPrice';
import { chainColors, chainLabel } from '../chains';
import { cleanUnit, euro, fmtPricePerUnit, formatBrand, pct } from '../format';
import { colors, radius, space, tint } from '../theme';
import { Offer } from '../types';
import { Icon } from './Icon';

// A calm deal row: image (+ discount badge), name, a muted meta line (category ·
// brand · unit), and at most three small tags (chain, Bio, day-limited). The lower-
// signal markers — source, loyalty bonus, app price — live in the detail (FlyerModal).
export function OfferCard({
  offer,
  onPress,
  accessibilityLabel,
  liked,
  inBasket,
}: {
  offer: Offer;
  onPress?: () => void;
  /** Override the announced action. Defaults to "Open deal for …", which is right everywhere the
   * card opens the detail — but NOT in the Basket's picker, where pressing it picks the offer for
   * your plan. A screen reader was being told the wrong action there. */
  accessibilityLabel?: string;
  /** Show a heart / cart marker in the tag row when the product is already liked / in the basket,
   * so you don't have to open the flyer to check. The status is also folded into the spoken label
   * (the markers themselves aren't separately focusable inside the row button). Passed only from
   * the deals list — the Basket picker leaves both undefined. */
  liked?: boolean;
  inBasket?: boolean;
}) {
  const meta = [offer.category_label, formatBrand(offer.brand), cleanUnit(offer.unit)]
    .filter(Boolean)
    .join(' · ');
  const pill = chainColors(offer.chain);
  const perUnit = fmtPricePerUnit(offer.price_per_unit);
  const appDeal = hasAppDeal(offer);
  const discount = headlineDiscountPct(offer);
  const strike = headlineStrikeCents(offer);
  // Fold basket/like status into the spoken label: the Pressable is the accessible element, so the
  // markers' own labels aren't separately focusable at runtime — a screen-reader user only hears
  // the row's label, so the status has to live there too.
  const spokenLabel = onPress
    ? `${accessibilityLabel ?? `Open deal for ${offer.name}`}${inBasket ? ', in your basket' : ''}${liked ? ', liked' : ''}`
    : undefined;
  return (
    <Pressable
      onPress={onPress}
      // The card is the app's primary control and announced nothing: a screen reader read out
      // the loose price/tag texts with no hint the row opens anything. Only a button when it
      // actually is one.
      accessibilityRole={onPress ? 'button' : undefined}
      accessibilityLabel={spokenLabel}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View style={styles.thumbWrap}>
        {offer.image_url ? (
          <Image source={{ uri: offer.image_url }} style={styles.thumb} resizeMode="contain" />
        ) : (
          <View style={[styles.thumb, styles.thumbEmpty]} />
        )}
        {discount != null && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{pct(discount)}</Text>
          </View>
        )}
      </View>

      <View style={styles.body}>
        <Text style={styles.name} numberOfLines={2}>
          {offer.name}
        </Text>
        {meta ? (
          <Text style={styles.meta} numberOfLines={1}>
            {meta}
          </Text>
        ) : null}
        <View style={styles.tagRow}>
          <View style={[styles.chainPill, { backgroundColor: pill.bg }]}>
            <Text style={[styles.chainText, { color: pill.fg }]}>{chainLabel(offer.chain)}</Text>
          </View>
          {offer.is_bio ? (
            <View style={[styles.iconPill, { backgroundColor: tint.bio.bg }]}>
              <Icon name="leaf" size={11} color={tint.bio.fg} />
              <Text style={[styles.iconPillText, { color: tint.bio.fg }]}>Bio</Text>
            </View>
          ) : null}
          {offer.day_limited && offer.valid_days ? (
            <View style={[styles.iconPill, { backgroundColor: tint.day.bg }]}>
              <Icon name="calendar-outline" size={11} color={tint.day.fg} />
              <Text style={[styles.iconPillText, { color: tint.day.fg }]}>{offer.valid_days}</Text>
            </View>
          ) : null}
          {/* Status markers, icon-only: shown only when already liked / in the basket. They carry a
              label for RNTL/query purposes; the runtime announcement rides on the card label above. */}
          {liked ? (
            <View style={[styles.marker, { backgroundColor: tint.like.bg }]} accessibilityLabel="Liked">
              <Icon name="heart" size={11} color={tint.like.fg} />
            </View>
          ) : null}
          {inBasket ? (
            <View
              style={[styles.marker, { backgroundColor: tint.basket.bg }]}
              accessibilityLabel="In your basket"
            >
              <Icon name="cart" size={11} color={tint.basket.fg} />
            </View>
          ) : null}
        </View>
      </View>

      <View style={styles.priceCol}>
        <Text style={styles.price}>{euro(headlinePriceCents(offer))}</Text>
        {appDeal && (
          <View style={styles.appPill}>
            <Text style={styles.appPillText}>Mit App</Text>
          </View>
        )}
        {strike != null && <Text style={styles.was}>{euro(strike)}</Text>}
        {perUnit ? <Text style={styles.ppu}>{perUnit}</Text> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: space.md,
    marginHorizontal: space.md,
    marginVertical: 5,
    borderWidth: 1,
    borderColor: colors.border,
  },
  pressed: { opacity: 0.7 },
  thumbWrap: { width: 60, height: 60, marginRight: 10 },
  thumb: { width: 60, height: 60, borderRadius: radius.sm, backgroundColor: '#fff' },
  thumbEmpty: { backgroundColor: colors.card2 },
  badge: {
    position: 'absolute',
    top: -6,
    left: -6,
    backgroundColor: colors.badge,
    borderRadius: radius.sm,
    paddingHorizontal: 6,
    paddingVertical: 3,
  },
  badgeText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  body: { flex: 1, paddingRight: space.sm },
  name: { color: colors.text, fontSize: 15, fontWeight: '600' },
  meta: { color: colors.muted, fontSize: 12, marginTop: 2 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6, alignItems: 'center' },
  chainPill: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  chainText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },
  iconPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 6,
  },
  iconPillText: { fontSize: 10, fontWeight: '700' },
  // Icon-only status marker (heart/cart) — a square-ish pill, no text, so it stays compact next to
  // the labelled attribute pills.
  marker: { paddingHorizontal: 5, paddingVertical: 2, borderRadius: 6 },
  priceCol: { alignItems: 'flex-end', minWidth: 72 },
  price: { color: colors.text, fontSize: 17, fontWeight: '700' },
  was: { color: colors.muted, fontSize: 12, textDecorationLine: 'line-through', marginTop: 2 },
  ppu: { color: colors.muted, fontSize: 11, marginTop: 3 },
  appPill: {
    backgroundColor: tint.app.bg,
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginTop: 3,
  },
  appPillText: { color: tint.app.fg, fontSize: 10, fontWeight: '700' },
});
