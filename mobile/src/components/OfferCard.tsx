import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { cleanUnit, euro, formatBrand, pct } from '../format';
import { colors } from '../theme';
import { Offer } from '../types';

export function OfferCard({ offer, onPress }: { offer: Offer; onPress?: () => void }) {
  const meta = [formatBrand(offer.brand), cleanUnit(offer.unit)].filter(Boolean).join(' · ');
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
          <Text style={styles.store}>{offer.chain.toUpperCase()}</Text>
        </View>
      </View>

      <View style={styles.priceCol}>
        <Text style={styles.price}>{euro(offer.price_cents)}</Text>
        {offer.regular_price_cents != null && (
          <Text style={styles.was}>{euro(offer.regular_price_cents)}</Text>
        )}
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
  tagRow: { flexDirection: 'row', gap: 8, marginTop: 6, alignItems: 'center' },
  tag: { color: colors.accent, fontSize: 11, fontWeight: '600' },
  store: { color: colors.muted, fontSize: 11, letterSpacing: 0.5 },
  priceCol: { alignItems: 'flex-end', minWidth: 64 },
  price: { color: colors.text, fontSize: 17, fontWeight: '700' },
  was: {
    color: colors.muted,
    fontSize: 12,
    textDecorationLine: 'line-through',
    marginTop: 2,
  },
});
