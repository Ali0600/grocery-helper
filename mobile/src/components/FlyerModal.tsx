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
import {
  counterfactuals,
  layerLabel,
  reasonLabel,
  ruleAddress,
  verdictDetail,
  winningLayer,
} from '../categoryTrace';
import { chainLabel } from '../chains';
import { cleanUnit, euro, fmtPricePerUnit, formatBrand } from '../format';
import { getPayloadCache, getTraceCache } from '../storage';
import { colors, tint } from '../theme';
import { Icon } from './Icon';
import { Offer, OfferCategoryTrace, OfferPayload } from '../types';

/** "Why this category?" — the winning rule, then every layer's verdict.
 *
 * The layer list is the point, not decoration: a layer that decided *after* the winner is
 * what the classifier would have said without it, which is how you tell "this rule is
 * wrong" from "this rule is correctly beating a mis-filed source path".
 */
function CategoryTraceView({ data }: { data: OfferCategoryTrace }) {
  const winner = winningLayer(data.trace);
  const alternatives = counterfactuals(data.trace);
  const path = data.trace.inputs.category_path;
  return (
    <View>
      <Text style={styles.traceVerdict}>
        {data.computed_label}
        {winner ? ` — ${layerLabel(winner.layer)} ${verdictDetail(winner)}` : ''}
      </Text>

      {data.stale && (
        <Text style={styles.traceStale}>
          {`Shown as ${data.stored_label}, but the current rules say ${data.computed_label} — this row predates a rules change (re-scrape to fix).`}
        </Text>
      )}

      {alternatives.length > 0 && (
        <Text style={styles.traceMuted}>
          {`Otherwise: ${alternatives
            .map((l) => `${layerLabel(l.layer)} → ${l.slug}`)
            .join(', ')}`}
        </Text>
      )}

      <View style={styles.traceRule}>
        {data.trace.layers.map((l) => {
          const isWinner = l === winner;
          const detail =
            l.status === 'skipped'
              ? `skipped — ${reasonLabel(l.reason)}`
              : l.status === 'no_match'
                ? 'no match'
                : `${l.slug}${l.matched ? ` — "${l.matched}"` : ''}${
                    l.reason && !l.matched ? ` (${reasonLabel(l.reason)})` : ''
                  }${l.blocked_slug ? ` (blocked a ${l.blocked_slug} rescue)` : ''}`;
          return (
            <Text
              key={l.layer}
              style={[
                styles.traceLayer,
                isWinner && styles.traceLayerWin,
                l.status !== 'decided' && styles.traceLayerOff,
              ]}
            >
              {`${isWinner ? '▸' : ' '} ${l.layer.padEnd(2)} ${layerLabel(l.layer)}: ${detail}`}
            </Text>
          );
        })}
      </View>

      {/* The source taxonomy path drives layers 1 and 3 but is absent from the deals API,
          so this is the only place it's visible — and it's the usual culprit. */}
      <Text style={styles.traceMuted}>
        {path ? `Source path: ${path.join(' › ')}` : 'Source path: none'}
      </Text>
      {winner && ruleAddress(winner) && (
        <Text style={styles.traceMuted}>{`Rule: categories.py ${ruleAddress(winner)}`}</Text>
      )}
    </View>
  );
}

// Per-chain link to the full weekly online leaflet (Prospekt).
const FLYER_LINKS: Record<string, { label: string; url: string }> = {
  lidl: { label: 'Lidl', url: 'https://www.lidl.de/c/online-prospekte/s10005610' },
  rewe: { label: 'REWE', url: 'https://www.meinprospekt.de/rewe-de' },
};

export function FlyerModal({
  offer,
  onClose,
  onAddToBasket,
  onToggleHidden,
  inBasket = false,
  hidden = false,
}: {
  offer: Offer | null;
  onClose: () => void;
  onAddToBasket?: (offer: Offer) => void;
  /** Dismiss this deal from the list (and from Basket/Recipes/Compare) for this flyer week.
   * A TOGGLE, unlike the add-only Basket button below: this is the only place to un-hide,
   * reached via the Filters sheet's "Show hidden" lens. It's also the button counterpart of
   * the card's right-swipe. */
  onToggleHidden?: (offer: Offer) => void;
  inBasket?: boolean;
  hidden?: boolean;
}) {
  const flyer = offer ? FLYER_LINKS[offer.chain] : null;

  // "View payload": lazily fetch the offer's full raw source payload on demand.
  const [showPayload, setShowPayload] = useState(false);
  const [payload, setPayload] = useState<OfferPayload | undefined>(undefined);
  const [loadingPayload, setLoadingPayload] = useState(false);
  const [payloadError, setPayloadError] = useState<string | null>(null);

  // "Why this category?": same lazy, cache-first shape as the payload above.
  const [showTrace, setShowTrace] = useState(false);
  const [trace, setTrace] = useState<OfferCategoryTrace | undefined>(undefined);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);

  // Reset both debug views whenever the modal opens a different offer (or closes).
  useEffect(() => {
    setShowPayload(false);
    setPayload(undefined);
    setLoadingPayload(false);
    setPayloadError(null);
    setShowTrace(false);
    setTrace(undefined);
    setLoadingTrace(false);
    setTraceError(null);
  }, [offer?.id]);

  const toggleTrace = useCallback(() => {
    if (showTrace) {
      setShowTrace(false);
      return;
    }
    setShowTrace(true);
    if (trace === undefined && offer) {
      setLoadingTrace(true);
      setTraceError(null);
      // Cache first (instant + offline, no Render cold start), network only on a miss —
      // identical to the payload path. `undefined` is the never-fetched sentinel.
      (async () => {
        try {
          const cache = await getTraceCache();
          const key = String(offer.id);
          setTrace(
            cache && key in cache.byId ? cache.byId[key] : await api.offerCategoryTrace(offer.id),
          );
        } catch {
          setTraceError('Could not load the category rules.');
        } finally {
          setLoadingTrace(false);
        }
      })();
    }
  }, [showTrace, trace, offer]);

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
            <View style={styles.headerLeft}>
              <Text style={styles.headerTitle} numberOfLines={1}>
                {flyer ? `${flyer.label} flyer` : 'Flyer'}
              </Text>
              {/* Hide sits next to the title, per the request. `flexShrink` on the title above
                  keeps a long chain name from pushing this into Close at 375pt. */}
              {offer && onToggleHidden ? (
                <Pressable
                  onPress={() => onToggleHidden(offer)}
                  hitSlop={8}
                  style={({ pressed }) => [
                    styles.hideBtn,
                    hidden && styles.hideBtnOn,
                    pressed && styles.flyerBtnPressed,
                  ]}
                  accessibilityRole="button"
                  accessibilityLabel={hidden ? `Un-hide ${offer.name}` : `Hide ${offer.name}`}
                >
                  <Icon
                    name={hidden ? 'eye-outline' : 'eye-off-outline'}
                    size={13}
                    color={hidden ? colors.accent : colors.muted}
                  />
                  <Text style={[styles.hideBtnText, hidden && { color: colors.accent }]}>
                    {hidden ? 'Un-Hide' : 'Hide'}
                  </Text>
                </Pressable>
              ) : null}
            </View>
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

              {/* The non-gesture path to the left-swipe (Basket): a swipe is unreachable for
                  screen-reader/keyboard users. Add-only and DISABLED once added, so the control is
                  never inert-looking; removing lives on the Basket page. The state flip is the
                  feedback — DealsScreen's toast renders *under* this modal. The right-swipe's
                  counterpart is the Hide button in this modal's header. */}
              <View style={styles.actions}>
                <Pressable
                  style={({ pressed }) => [
                    styles.actionBtn,
                    inBasket && styles.actionBtnDone,
                    pressed && styles.flyerBtnPressed,
                  ]}
                  onPress={() => onAddToBasket?.(offer)}
                  disabled={inBasket}
                  accessibilityRole="button"
                  accessibilityState={{ disabled: inBasket }}
                  accessibilityLabel={
                    inBasket ? `${offer.name} is in your basket` : `Add ${offer.name} to basket`
                  }
                >
                  <Icon
                    name={inBasket ? 'cart' : 'cart-outline'}
                    size={16}
                    color={inBasket ? colors.accent : colors.text}
                  />
                  <Text style={[styles.actionText, inBasket && { color: colors.accent }]}>
                    {inBasket ? 'In basket ✓' : 'Basket'}
                  </Text>
                </Pressable>
              </View>

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
                onPress={toggleTrace}
                accessibilityRole="button"
                accessibilityLabel={showTrace ? 'Hide category rules' : 'Why this category?'}
              >
                <Text style={styles.payloadBtnText}>
                  {showTrace ? 'Hide category rules' : 'Why this category?'}
                </Text>
              </Pressable>

              {showTrace && (
                <View style={styles.payloadBox}>
                  {loadingTrace ? (
                    <ActivityIndicator color={colors.accent} />
                  ) : traceError ? (
                    <Text style={styles.muted}>{traceError}</Text>
                  ) : trace ? (
                    <CategoryTraceView data={trace} />
                  ) : (
                    <Text style={styles.muted}>No rule trace for this offer.</Text>
                  )}
                </View>
              )}

              <Pressable
                style={({ pressed }) => [styles.payloadBtn, pressed && styles.flyerBtnPressed]}
                onPress={togglePayload}
                accessibilityRole="button"
                accessibilityLabel={showPayload ? 'Hide payload' : 'View payload'}
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
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, flexShrink: 1, minWidth: 0 },
  headerTitle: { color: colors.text, fontSize: 17, fontWeight: '700', flexShrink: 1 },
  hideBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card2,
  },
  hideBtnOn: { borderColor: colors.accent },
  hideBtnText: { color: colors.muted, fontSize: 12, fontWeight: '700' },
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

  // Like / Basket — the button counterparts of the swipe gestures.
  actions: { flexDirection: 'row', gap: 10, marginTop: 20, alignSelf: 'stretch' },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    backgroundColor: colors.card2,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 13,
  },
  actionBtnDone: { opacity: 0.85 },
  actionText: { color: colors.text, fontSize: 15, fontWeight: '600' },
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
  // "Why this category?" — the verdict reads as a headline, the layer list as a log.
  traceVerdict: { color: colors.text, fontSize: 13, fontWeight: '700', marginBottom: 6 },
  traceStale: {
    color: tint.day.fg,
    fontSize: 11,
    lineHeight: 15,
    marginBottom: 6,
  },
  traceMuted: { color: colors.muted, fontSize: 11, lineHeight: 16, marginTop: 4 },
  traceRule: {
    borderTopColor: colors.border,
    borderTopWidth: 1,
    marginTop: 8,
    paddingTop: 8,
  },
  traceLayer: {
    color: colors.text,
    fontSize: 10,
    lineHeight: 15,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  traceLayerWin: { color: colors.accent, fontWeight: '700' },
  traceLayerOff: { color: colors.muted },
  payloadText: {
    color: colors.text,
    fontSize: 11,
    lineHeight: 16,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
});
