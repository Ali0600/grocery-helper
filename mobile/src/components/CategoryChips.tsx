import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { colors } from '../theme';
import { CategoryCount } from '../types';

type Props = {
  categories: CategoryCount[];
  selected: string | null;
  onSelect: (slug: string | null) => void;
};

export function CategoryChips({ categories, selected, onSelect }: Props) {
  const Chip = ({ label, value }: { label: string; value: string | null }) => {
    const active = selected === value;
    return (
      <Pressable
        onPress={() => onSelect(value)}
        style={[styles.chip, active && styles.chipActive]}
      >
        <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
      </Pressable>
    );
  };

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.row}
    >
      <Chip label="All" value={null} />
      {categories.map((c) => (
        <Chip key={c.category} label={`${c.label} (${c.count})`} value={c.category} />
      ))}
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
});
