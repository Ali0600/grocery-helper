import React, { memo } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import * as Haptics from 'expo-haptics';
import { Swipeable } from 'react-native-gesture-handler';

import { colors, radius, space } from '../theme';
import { Offer } from '../types';
import { Icon } from './Icon';
import { OfferCard } from './OfferCard';

// Swipe a deal left to add it to the basket. The revealed green action reads "Basket";
// releasing past the threshold adds the offer's sub-category (see resolveBasketItem),
// buzzes, and snaps the row shut — a fling-to-add, so the row never stays open.
//
// FREEZE HARDENING: the gesture's completion callback must stay pure. Mutating app
// state inside it (basket + toast → the whole list re-renders mid-gesture) and only
// then force-closing the row is a known stuck-active-gesture recipe — the pan never
// settles and gesture-handler's root keeps claiming EVERY touch (app-wide freeze,
// no taps, no scroll). So: close first, and defer the add + haptic by a frame. The
// component is memoized (all props stable) so live gestures aren't re-rendered under.
export const SwipeableOfferCard = memo(function SwipeableOfferCard({
  offer,
  onPressOffer,
  onAdd,
}: {
  offer: Offer;
  onPressOffer: (offer: Offer) => void;
  onAdd: (offer: Offer) => void;
}) {
  return (
    <Swipeable
      friction={2}
      rightThreshold={40}
      overshootRight={false}
      renderRightActions={() => (
        <View style={styles.action}>
          <Icon name="cart" size={20} color={colors.onAccent} />
          <Text style={styles.label}>Basket</Text>
        </View>
      )}
      onSwipeableOpen={(direction, swipeable) => {
        if (direction !== 'right') return; // left-swipe reveals the right action
        swipeable.close();
        requestAnimationFrame(() => {
          onAdd(offer);
          if (Platform.OS !== 'web') {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
          }
        });
      }}
    >
      <OfferCard offer={offer} onPress={() => onPressOffer(offer)} />
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
  label: { color: colors.onAccent, fontWeight: '700', fontSize: 13 },
});
