import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, font, radius, space } from '../theme';
import { CategoryCount } from '../types';
import { AppModal } from './AppModal';
import { Icon } from './Icon';

// The editor for the personalized "My Categories" home: a toggle-pill grid of the food categories,
// active = chosen. Its OWN modal (not a FilterSheet section) because `myCategories` is a persisted
// preference the Filters sheet's Reset must never clear — same reasoning as the Stores modal owning
// store membership. Toggling persists immediately (the parent writes on each tap).
export function CategoriesModal(props: {
  visible: boolean;
  onClose: () => void;
  categories: CategoryCount[]; // food categories only (household is non-food, gated elsewhere)
  myCategories: string[];
  onToggle: (slug: string) => void;
}) {
  const { visible, onClose, categories, myCategories, onToggle } = props;
  const chosen = new Set(myCategories);
  const count = categories.filter((c) => chosen.has(c.category)).length;

  return (
    <AppModal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} />
      <View style={styles.sheet} testID="categories-modal">
        <View style={styles.grabber} />
        <View style={styles.headerRow}>
          <Text style={styles.title}>My categories</Text>
          <Pressable onPress={onClose} hitSlop={6} accessibilityLabel="Close my categories">
            <Icon name="close" size={22} color={colors.muted} />
          </Pressable>
        </View>
        <Text style={styles.subtitle}>
          Pick what shows on your home. Untouched categories stay in All.
        </Text>

        <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
          <View style={styles.pillRow}>
            {categories.map((c) => {
              const active = chosen.has(c.category);
              return (
                <Pressable
                  key={c.category}
                  onPress={() => onToggle(c.category)}
                  style={[styles.pill, active && styles.pillActive]}
                  accessibilityRole="button"
                  accessibilityState={{ selected: active }}
                  accessibilityLabel={`${active ? 'Remove' : 'Add'} ${c.label}`}
                >
                  {active ? (
                    <Icon name="checkmark" size={14} color={colors.onAccent} />
                  ) : null}
                  <Text
                    style={[styles.pillText, active && styles.pillTextActive, active && styles.pillTextGap]}
                  >
                    {`${c.label} (${c.count})`}
                  </Text>
                </Pressable>
              );
            })}
          </View>
          {categories.length === 0 ? (
            <Text style={styles.empty}>No categories loaded yet — pull to refresh on the deals list.</Text>
          ) : null}
        </ScrollView>

        <Pressable style={styles.done} onPress={onClose}>
          <Text style={styles.doneText}>{count > 0 ? `Done · ${count} chosen` : 'Done'}</Text>
        </Pressable>
      </View>
    </AppModal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  sheet: {
    backgroundColor: colors.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: space.lg,
    paddingBottom: space.xl,
    maxHeight: '80%',
  },
  grabber: {
    alignSelf: 'center',
    width: 36,
    height: 4,
    borderRadius: radius.pill,
    backgroundColor: colors.border,
    marginTop: space.sm,
    marginBottom: space.md,
  },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { ...font.h2, color: colors.text },
  subtitle: { color: colors.muted, fontSize: 12, marginTop: space.xs },
  body: { marginTop: space.md },
  bodyContent: { paddingBottom: space.md },
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  pill: {
    flexDirection: 'row',
    paddingHorizontal: 14,
    height: 34,
    borderRadius: radius.pill,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  pillText: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  pillTextActive: { color: colors.onAccent },
  pillTextGap: { marginLeft: 5 },
  empty: { color: colors.muted, fontSize: 13, paddingVertical: space.lg, textAlign: 'center' },
  done: {
    marginTop: space.lg,
    height: 46,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneText: { color: colors.onAccent, fontSize: 15, fontWeight: '700' },
});
