import React from 'react';
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
export function SwipeableOfferCard({
  offer,
  onPress,
  onAdd,
}: {
  offer: Offer;
  onPress?: () => void;
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
        onAdd(offer);
        if (Platform.OS !== 'web') {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
        }
        swipeable.close();
      }}
    >
      <OfferCard offer={offer} onPress={onPress} />
    </Swipeable>
  );
}

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
