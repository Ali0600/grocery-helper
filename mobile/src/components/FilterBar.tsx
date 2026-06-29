import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, radius, space } from '../theme';
import { Icon } from './Icon';

export type FilterChip = { key: string; label: string; onRemove: () => void };

// The single filter row on the deals screen: a sort summary, a "Filters" button
// (badged with the active-filter count), and a removable chip per active filter.
// Both buttons open the FilterSheet; chips clear their own filter on tap.
export function FilterBar({
  sortLabel,
  chips,
  onOpen,
}: {
  sortLabel: string;
  chips: FilterChip[];
  onOpen: () => void;
}) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.row}
    >
      <Pressable style={styles.btn} onPress={onOpen} accessibilityLabel="Change sort">
        <Icon name="swap-vertical" size={15} color={colors.muted} />
        <Text style={styles.btnText}>{sortLabel}</Text>
        <Icon name="chevron-down" size={14} color={colors.muted} />
      </Pressable>
      <Pressable style={styles.btn} onPress={onOpen} accessibilityLabel="Open filters">
        <Icon name="options-outline" size={15} color={colors.muted} />
        <Text style={styles.btnText}>Filters</Text>
        {chips.length > 0 ? (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{chips.length}</Text>
          </View>
        ) : null}
      </Pressable>
      {chips.map((c) => (
        <Pressable
          key={c.key}
          style={styles.chip}
          onPress={c.onRemove}
          accessibilityLabel={`Remove ${c.label} filter`}
        >
          <Text style={styles.chipText}>{c.label}</Text>
          <Icon name="close" size={13} color={colors.accent} />
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 0 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.md,
    paddingBottom: space.sm,
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    height: 32,
    paddingHorizontal: 12,
    borderRadius: radius.pill,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
  },
  btnText: { color: colors.text, fontSize: 12, fontWeight: '600' },
  countBadge: {
    minWidth: 16,
    height: 16,
    paddingHorizontal: 4,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 2,
  },
  countText: { color: colors.onAccent, fontSize: 10, fontWeight: '800' },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    height: 32,
    paddingHorizontal: 12,
    borderRadius: radius.pill,
    backgroundColor: 'rgba(61,220,132,0.14)',
    borderWidth: 1,
    borderColor: 'rgba(61,220,132,0.4)',
  },
  chipText: { color: colors.accent, fontSize: 12, fontWeight: '600' },
});
