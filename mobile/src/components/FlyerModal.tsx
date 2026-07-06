import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { AppModal } from './AppModal';

import { api } from '../api';
import { chainLabel } from '../chains';
import { cleanUnit, euro, fmtPricePerUnit, formatBrand } from '../format';
import { getPayloadCache } from '../storage';
import { colors } from '../theme';
import { Offer, OfferPayload } from '../types';

// Per-chain link to the full weekly online leaflet (Prospekt).
const FLYER_LINKS: Record<string, { label: string; url: string }> = {
  lidl: { label: 'Lidl', url: 'https://www.lidl.de/c/online-prospekte/s10005610' },
  rewe: { label: 'REWE', url: 'https://www.meinprospekt.de/rewe-de' },
};

export function FlyerModal({ offer, onClose }: { offer: Offer | null; onClose: () => void }) {
  const flyer = offer ? FLYER_LINKS[offer.chain] : null;

  // "View payload": lazily fetch the offer's full raw source payload on demand.
  const [showPayload, setShowPayload] = useState(false);
  const [payload, setPayload] = useState<OfferPayload | undefined>(undefined);
  const [loadingPayload, setLoadingPayload] = useState(false);
  const [payloadError, setPayloadError] = useState<string | null>(null);

  // Reset the payload view whenever the modal opens a different offer (or closes).
  useEffect(() => {
    setShowPayload(false);
    setPayload(undefined);
    setLoadingPayload(false);
    setPayloadError(null);
  }, [offer?.id]);

  const togglePayload = useCallback(() => {
    if (showPayload) {
      setShowPayload(false);
      return;
    }
    setShowPayload(true);
    if (payload === undefined && offer) {
      setLoadingPayload(true);
      setPayloadError(null);
      // Prefer the on-device prefetch cache (instant + offline, no Render cold start); fall
      // back to the per-offer endpoint only if this offer wasn't prefetched (cache miss / an
      // older cache from before the prefetch ran).
      (async () => {
        try {
          const cache = await getPayloadCache();
          const key = String(offer.id);
          if (cache && key in cache.byId) {
            setPayload({ id: offer.id, source: offer.source, payload: cache.byId[key] });
          } else {
            setPayload(await api.offerPayload(offer.id));
          }
        } catch {
          setPayloadError('Could not load the payload.');
        } finally {
          setLoadingPayload(false);
        }
      })();
    }
  }, [showPayload, payload, offer]);

  return (
    <AppModal visible={!!offer} transparent animationType="fade" onRequestClose={onClose}>
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
              <Text style={styles.meta}>
                {`${chainLabel(offer.chain)} · ${offer.source === 'flyer' ? 'Prospekt' : 'Coupon'}`}
                {offer.day_limited && offer.valid_days ? ` · nur ${offer.valid_days}` : ''}
                {offer.is_bio ? ' · Bio' : ''}
              </Text>
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

              <Pressable
                style={({ pressed }) => [styles.payloadBtn, pressed && styles.flyerBtnPressed]}
                onPress={togglePayload}
              >
                <Text style={styles.payloadBtnText}>
                  {showPayload ? 'Hide payload' : 'View payload'}
                </Text>
              </Pressable>

              {showPayload && (
                <View style={styles.payloadBox}>
                  {loadingPayload ? (
                    <ActivityIndicator color={colors.accent} />
                  ) : payloadError ? (
                    <Text style={styles.muted}>{payloadError}</Text>
                  ) : payload?.payload ? (
                    <Text style={styles.payloadText} selectable>
                      {JSON.stringify(payload.payload, null, 2)}
                    </Text>
                  ) : (
                    <Text style={styles.muted}>
                      Payload not captured yet — re-scrape to record it.
                    </Text>
                  )}
                </View>
              )}
            </ScrollView>
          )}
        </View>
      </View>
    </AppModal>
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
  payloadBtn: {
    marginTop: 10,
    backgroundColor: colors.card2,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignSelf: 'stretch',
    alignItems: 'center',
  },
  payloadBtnText: { color: colors.muted, fontSize: 14, fontWeight: '600' },
  payloadBox: {
    marginTop: 12,
    alignSelf: 'stretch',
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    minHeight: 44,
    justifyContent: 'center',
  },
  payloadText: {
    color: colors.text,
    fontSize: 11,
    lineHeight: 16,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
});
