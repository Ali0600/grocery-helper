import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, space } from '../theme';
import { Icon } from './Icon';

// Header for one category "shelf" on the "My Categories" home: the category name + total, and a
// "See all ›" affordance. The whole row is pressable and drills into that category's full view.
export function CategorySectionHeader({
  label,
  total,
  onSeeAll,
}: {
  label: string;
  total: number;
  onSeeAll: () => void;
}) {
  return (
    <Pressable
      style={styles.row}
      onPress={onSeeAll}
      accessibilityRole="button"
      accessibilityLabel={`See all ${total} in ${label}`}
    >
      <Text style={styles.label}>
        {label}
        <Text style={styles.count}>{`  ·  ${total}`}</Text>
      </Text>
      <View style={styles.seeAll}>
        <Text style={styles.seeAllText}>See all</Text>
        <Icon name="chevron-forward" size={15} color={colors.accent} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.bg,
    paddingHorizontal: space.lg,
    paddingTop: 16,
    paddingBottom: 6,
  },
  label: { color: colors.text, fontSize: 16, fontWeight: '700' },
  count: { color: colors.muted, fontSize: 14, fontWeight: '500' },
  seeAll: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  seeAllText: { color: colors.accent, fontSize: 13, fontWeight: '600' },
});
