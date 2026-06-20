import React from 'react';
import {
  Image,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { cleanUnit, euro, fmtPricePerUnit, formatBrand } from '../format';
import { colors } from '../theme';
import { Offer } from '../types';

// Per-chain link to the full weekly online leaflet (Prospekt).
const FLYER_LINKS: Record<string, { label: string; url: string }> = {
  lidl: { label: 'Lidl', url: 'https://www.lidl.de/c/online-prospekte/s10005610' },
  rewe: { label: 'REWE', url: 'https://www.meinprospekt.de/rewe-de' },
};

export function FlyerModal({ offer, onClose }: { offer: Offer | null; onClose: () => void }) {
  const flyer = offer ? FLYER_LINKS[offer.chain] : null;
  return (
    <Modal visible={!!offer} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>{flyer ? `${flyer.label} flyer` : 'Flyer'}</Text>
            <Pressable onPress={onClose} hitSlop={10}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>

          {offer && (
            <ScrollView contentContainerStyle={styles.content}>
              {offer.image_url ? (
                <Image source={{ uri: offer.image_url }} style={styles.image} resizeMode="contain" />
              ) : (
                <View style={[styles.image, styles.imageEmpty]}>
                  <Text style={styles.muted}>No flyer image for this offer.</Text>
                </View>
              )}

              <Text style={styles.name}>{offer.name}</Text>
              <Text style={styles.price}>
                {euro(offer.price_cents)}
                {offer.regular_price_cents != null && (
                  <Text style={styles.was}>{`  statt ${euro(offer.regular_price_cents)}`}</Text>
                )}
              </Text>
              {!!(offer.brand || offer.unit) && (
                <Text style={styles.meta}>
                  {[formatBrand(offer.brand), cleanUnit(offer.unit)]
                    .filter(Boolean)
                    .join(' · ')}
                </Text>
              )}
              {!!offer.price_per_unit && (
                <Text style={styles.meta}>Grundpreis: {fmtPricePerUnit(offer.price_per_unit)}</Text>
              )}
              {!!offer.loyalty_note && (
                <Text style={styles.bonus}>{`Mit Kundenkarte: ${offer.loyalty_note}`}</Text>
              )}
              {offer.app_price_cents != null && offer.app_price_cents < offer.price_cents && (
                <Text style={styles.app}>{`Mit App: ${euro(offer.app_price_cents)}`}</Text>
              )}

              {flyer && (
                <Pressable
                  style={({ pressed }) => [styles.flyerBtn, pressed && styles.flyerBtnPressed]}
                  onPress={() => Linking.openURL(flyer.url)}
                >
                  <Text style={styles.flyerBtnText}>{`Open ${flyer.label}'s weekly flyer ↗`}</Text>
                </Pressable>
              )}
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingBottom: 28,
    maxHeight: '88%',
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
  content: { padding: 16, alignItems: 'center' },
  image: {
    width: '100%',
    height: 300,
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  imageEmpty: { alignItems: 'center', justifyContent: 'center', backgroundColor: colors.card2 },
  name: { color: colors.text, fontSize: 18, fontWeight: '700', marginTop: 16, textAlign: 'center' },
  price: { color: colors.text, fontSize: 20, fontWeight: '700', marginTop: 8 },
  was: { color: colors.muted, fontSize: 14, fontWeight: '400', textDecorationLine: 'line-through' },
  meta: { color: colors.muted, fontSize: 13, marginTop: 6 },
  bonus: { color: colors.accent, fontSize: 14, fontWeight: '600', marginTop: 8 },
  app: { color: '#ffd84d', fontSize: 14, fontWeight: '600', marginTop: 8 }, // EDEKA app price
  muted: { color: colors.muted, fontSize: 14 },
  flyerBtn: {
    marginTop: 22,
    backgroundColor: colors.card2,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 20,
    alignSelf: 'stretch',
    alignItems: 'center',
  },
  flyerBtnPressed: { opacity: 0.7 },
  flyerBtnText: { color: colors.accent, fontSize: 15, fontWeight: '600' },
});
