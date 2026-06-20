import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { colors } from '../theme';
import { CategoryCount } from '../types';

const NON_FOOD = 'household';

type Props = {
  categories: CategoryCount[];
  selected: string | null;
  onSelect: (slug: string | null) => void;
  showNonFood: boolean;
  onToggleNonFood: () => void;
};

// A single category pill. Hoisted to module scope (not defined inside the parent's
// render) so its component identity is stable across renders.
function Chip({
  label,
  value,
  selected,
  onSelect,
}: {
  label: string;
  value: string | null;
  selected: string | null;
  onSelect: (slug: string | null) => void;
}) {
  const active = selected === value;
  return (
    <Pressable onPress={() => onSelect(value)} style={[styles.chip, active && styles.chipActive]}>
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

export function CategoryChips({
  categories,
  selected,
  onSelect,
  showNonFood,
  onToggleNonFood,
}: Props) {
  const food = categories.filter((c) => c.category !== NON_FOOD);
  const nonFood = categories.find((c) => c.category === NON_FOOD);

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.row}
    >
      <Chip label="All" value={null} selected={selected} onSelect={onSelect} />
      {food.map((c) => (
        <Chip
          key={c.category}
          label={`${c.label} (${c.count})`}
          value={c.category}
          selected={selected}
          onSelect={onSelect}
        />
      ))}
      {showNonFood && nonFood && (
        <Chip
          label={`${nonFood.label} (${nonFood.count})`}
          value={NON_FOOD}
          selected={selected}
          onSelect={onSelect}
        />
      )}
      <Pressable onPress={onToggleNonFood} style={[styles.chip, styles.toggle]}>
        <Text style={styles.toggleText}>{showNonFood ? '− Non-food' : '+ Non-food'}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // flexGrow:0 + maxHeight stop the strip from expanding to fill the column.
  scroll: { flexGrow: 0, maxHeight: 56 },
  row: { paddingHorizontal: 12, gap: 8, paddingVertical: 10, alignItems: 'center' },
  chip: {
    height: 36,
    paddingHorizontal: 14,
    borderRadius: 999,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.muted, fontSize: 13, fontWeight: '500' },
  chipTextActive: { color: '#08130c' },
  toggle: { backgroundColor: 'transparent', borderStyle: 'dashed' },
  toggleText: { color: colors.muted, fontSize: 13, fontWeight: '600' },
});
