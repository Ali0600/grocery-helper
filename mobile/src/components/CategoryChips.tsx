import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { colors } from '../theme';
import { CategoryCount } from '../types';
import { Icon, IconName } from './Icon';

const NON_FOOD = 'household';

type Props = {
  categories: CategoryCount[];
  selected: string | null;
  onSelect: (slug: string | null) => void;
  showNonFood: boolean;
  // The personalized "My Categories" home. `mine` = that view is active (so All / a category
  // chip are not); `hasMine` = the user has chosen at least one category, so the ★ chip is worth
  // showing (until then the pencil is the only, and discovery, entry point).
  mine: boolean;
  hasMine: boolean;
  onSelectMine: () => void;
  onEditCategories: () => void;
};

// A single pill. `active` is passed in (not derived from `selected`) because Mine/All/category
// activeness all depend on the `mine` flag too. Hoisted to module scope for a stable identity.
function Chip({
  label,
  icon,
  active,
  onPress,
  accessibilityLabel,
}: {
  label?: string;
  icon?: IconName;
  active: boolean;
  onPress: () => void;
  accessibilityLabel?: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.chip, active && styles.chipActive]}
      accessibilityLabel={accessibilityLabel}
    >
      {icon ? (
        <Icon name={icon} size={14} color={active ? colors.onAccent : colors.muted} />
      ) : null}
      {label ? (
        <Text style={[styles.chipText, active && styles.chipTextActive, icon ? styles.chipTextGap : null]}>
          {label}
        </Text>
      ) : null}
    </Pressable>
  );
}

export function CategoryChips({
  categories,
  selected,
  onSelect,
  showNonFood,
  mine,
  hasMine,
  onSelectMine,
  onEditCategories,
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
      {hasMine ? (
        <Chip label="Mine" icon="star" active={mine} onPress={onSelectMine} />
      ) : null}
      <Chip label="All" active={!mine && selected === null} onPress={() => onSelect(null)} />
      {food.map((c) => (
        <Chip
          key={c.category}
          label={`${c.label} (${c.count})`}
          active={!mine && selected === c.category}
          onPress={() => onSelect(c.category)}
        />
      ))}
      {showNonFood && nonFood && (
        <Chip
          label={`${nonFood.label} (${nonFood.count})`}
          active={!mine && selected === NON_FOOD}
          onPress={() => onSelect(NON_FOOD)}
        />
      )}
      {/* Always last: the entry to pick/edit your categories (and the only one before you have any). */}
      <Chip
        icon="pencil"
        active={false}
        onPress={onEditCategories}
        accessibilityLabel="Edit my categories"
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // flexGrow:0 + maxHeight stop the strip from expanding to fill the column.
  scroll: { flexGrow: 0, maxHeight: 56 },
  row: { paddingHorizontal: 12, gap: 8, paddingVertical: 10, alignItems: 'center' },
  chip: {
    flexDirection: 'row',
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
  chipTextActive: { color: colors.onAccent },
  chipTextGap: { marginLeft: 5 },
});
