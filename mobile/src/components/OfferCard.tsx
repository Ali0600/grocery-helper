import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { chainColors, chainLabel } from '../chains';
import { cleanUnit, euro, fmtPricePerUnit, formatBrand, pct } from '../format';
import { colors } from '../theme';
import { Offer } from '../types';

export function OfferCard({ offer, onPress }: { offer: Offer; onPress?: () => void }) {
  const meta = [formatBrand(offer.brand), cleanUnit(offer.unit)].filter(Boolean).join(' · ');
  const pill = chainColors(offer.chain);
  const perUnit = fmtPricePerUnit(offer.price_per_unit);
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View style={styles.thumbWrap}>
        {offer.image_url ? (
          <Image source={{ uri: offer.image_url }} style={styles.thumb} resizeMode="contain" />
        ) : (
          <View style={[styles.thumb, styles.thumbEmpty]} />
        )}
        {offer.discount_pct != null && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{pct(offer.discount_pct)}</Text>
          </View>
        )}
      </View>

      <View style={styles.body}>
        <Text style={styles.name} numberOfLines={2}>
          {offer.name}
        </Text>
        {meta ? <Text style={styles.meta}>{meta}</Text> : null}
        <View style={styles.tagRow}>
          <Text style={styles.tag}>{offer.category_label}</Text>
          <View style={[styles.chainPill, { backgroundColor: pill.bg }]}>
            <Text style={[styles.chainText, { color: pill.fg }]}>{chainLabel(offer.chain)}</Text>
          </View>
          <View
            style={[
              styles.srcPill,
              offer.source === 'flyer' ? styles.srcFlyer : styles.srcCoupon,
            ]}
          >
            <Text
              style={[
                styles.srcText,
                offer.source === 'flyer' ? styles.srcTextFlyer : styles.srcTextCoupon,
              ]}
            >
              {offer.source === 'flyer' ? 'Prospekt' : 'Coupon'}
            </Text>
          </View>
          {offer.loyalty_note ? (
            <View style={styles.loyaltyPill}>
              <Text style={styles.loyaltyText}>{offer.loyalty_note}</Text>
            </View>
          ) : null}
          {offer.app_price_cents != null && offer.app_price_cents < offer.price_cents ? (
            <View style={styles.appPill}>
              <Text style={styles.appText}>App {euro(offer.app_price_cents)}</Text>
            </View>
          ) : null}
          {offer.day_limited && offer.valid_days ? (
            <View style={styles.dayPill}>
              <Text style={styles.dayText}>🗓 {offer.valid_days}</Text>
            </View>
          ) : null}
        </View>
      </View>

      <View style={styles.priceCol}>
        <Text style={styles.price}>{euro(offer.price_cents)}</Text>
        {offer.regular_price_cents != null && (
          <Text style={styles.was}>{euro(offer.regular_price_cents)}</Text>
        )}
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
    borderRadius: 14,
    padding: 12,
    marginHorizontal: 12,
    marginVertical: 5,
    borderWidth: 1,
    borderColor: colors.border,
  },
  pressed: { opacity: 0.7 },
  thumbWrap: { width: 60, height: 60, marginRight: 10 },
  thumb: { width: 60, height: 60, borderRadius: 8, backgroundColor: '#fff' },
  thumbEmpty: { backgroundColor: colors.card2 },
  badge: {
    position: 'absolute',
    top: -6,
    left: -6,
    backgroundColor: colors.badge,
    borderRadius: 8,
    paddingHorizontal: 6,
    paddingVertical: 3,
  },
  badgeText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  body: { flex: 1, paddingRight: 8 },
  name: { color: colors.text, fontSize: 15, fontWeight: '600' },
  meta: { color: colors.muted, fontSize: 12, marginTop: 2 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6, alignItems: 'center' },
  tag: { color: colors.accent, fontSize: 11, fontWeight: '600' },
  chainPill: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  chainText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },
  srcPill: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  srcText: { fontSize: 10, fontWeight: '700', letterSpacing: 0.3 },
  srcCoupon: { backgroundColor: 'rgba(61,139,253,0.16)' },
  srcFlyer: { backgroundColor: 'rgba(240,180,60,0.16)' },
  srcTextCoupon: { color: '#7da7ff' },
  srcTextFlyer: { color: '#e6b34d' },
  loyaltyPill: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 6,
    backgroundColor: 'rgba(61,220,132,0.16)',
  },
  loyaltyText: { color: colors.accent, fontSize: 10, fontWeight: '700' },
  appPill: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 6,
    backgroundColor: 'rgba(255,205,0,0.16)', // EDEKA yellow
  },
  appText: { color: '#ffd84d', fontSize: 10, fontWeight: '700' },
  dayPill: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 6,
    backgroundColor: 'rgba(255,159,67,0.18)', // day-limited = orange
  },
  dayText: { color: '#ff9f43', fontSize: 10, fontWeight: '700' },
  priceCol: { alignItems: 'flex-end', minWidth: 72 },
  price: { color: colors.text, fontSize: 17, fontWeight: '700' },
  was: {
    color: colors.muted,
    fontSize: 12,
    textDecorationLine: 'line-through',
    marginTop: 2,
  },
  ppu: { color: colors.muted, fontSize: 11, marginTop: 3 },
});
