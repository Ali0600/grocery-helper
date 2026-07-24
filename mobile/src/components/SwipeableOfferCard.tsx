import React, { memo } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import * as Haptics from 'expo-haptics';
import { Swipeable } from 'react-native-gesture-handler';

import { colors, radius, space, tint } from '../theme';
import { Offer } from '../types';
import { Icon } from './Icon';
import { OfferCard } from './OfferCard';

// Swipe a deal LEFT to add it to the basket (green "Basket" panel on the right), or
// RIGHT to Like the product (pink "Like" panel on the left — see likes.ts). Releasing
// past the threshold acts, buzzes, and snaps the row shut — fling-to-act, the row never
// stays open. NOTE the legacy Swipeable's `direction` names the PANEL SIDE that opened,
// not the finger motion: a right-swipe opens the LEFT panel → direction === 'left'.
//
// FREEZE HARDENING: the gesture's completion callback must stay pure. Mutating app
// state inside it (basket + toast → the whole list re-renders mid-gesture) and only
// then force-closing the row is a known stuck-active-gesture recipe — the pan never
// settles and gesture-handler's root keeps claiming EVERY touch (app-wide freeze,
// no taps, no scroll). So: close first, and defer the action + haptic by a frame. The
// component is memoized (ALL props must stay identity-stable) so live gestures aren't
// re-rendered under.
/** The swipe→action seam, exported for tests (the native pan can't run under jest).
 * `direction` routes by PANEL SIDE: 'right' panel (left-swipe) → basket, 'left' panel
 * (right-swipe) → like. Close FIRST, then defer the state write + haptic by a frame —
 * the freeze-hardening contract above. */
export function handleSwipeableOpen(
  direction: 'left' | 'right',
  swipeable: { close: () => void },
  offer: Offer,
  actions: { onAdd: (offer: Offer) => void; onLike: (offer: Offer) => void },
): void {
  swipeable.close();
  requestAnimationFrame(() => {
    if (direction === 'right') actions.onAdd(offer);
    else actions.onLike(offer);
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    }
  });
}

export const SwipeableOfferCard = memo(function SwipeableOfferCard({
  offer,
  onPressOffer,
  onAdd,
  onLike,
  liked,
  inBasket,
}: {
  offer: Offer;
  onPressOffer: (offer: Offer) => void;
  onAdd: (offer: Offer) => void;
  onLike: (offer: Offer) => void;
  // Primitive props: booleans compare by value under memo(), so only the row whose flag actually
  // flips re-renders — the freeze contract (identity-stable props) is preserved.
  liked?: boolean;
  inBasket?: boolean;
}) {
  return (
    <Swipeable
      friction={2}
      rightThreshold={40}
      leftThreshold={40}
      overshootRight={false}
      overshootLeft={false}
      renderRightActions={() => (
        <View style={styles.action}>
          <Icon name="cart" size={20} color={colors.onAccent} />
          <Text style={styles.label}>Basket</Text>
        </View>
      )}
      renderLeftActions={() => (
        <View style={[styles.action, styles.likeAction]}>
          <Icon name="heart" size={20} color={tint.like.fg} />
          <Text style={[styles.label, styles.likeLabel]}>Like</Text>
        </View>
      )}
      onSwipeableOpen={(direction, swipeable) =>
        handleSwipeableOpen(direction, swipeable, offer, { onAdd, onLike })
      }
    >
      <OfferCard offer={offer} onPress={() => onPressOffer(offer)} liked={liked} inBasket={inBasket} />
    </Swipeable>
  );
});

const styles = StyleSheet.create({
  action: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    marginVertical: 5,
    marginRight: space.md,
    paddingHorizontal: 22,
  },
  // The left (Like) panel mirrors the right one: its own margin side, pink tint.
  likeAction: {
    backgroundColor: tint.like.bg,
    marginRight: 0,
    marginLeft: space.md,
  },
  label: { color: colors.onAccent, fontWeight: '700', fontSize: 13 },
  likeLabel: { color: tint.like.fg },
});
