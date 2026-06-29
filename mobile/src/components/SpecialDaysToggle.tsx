import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { colors } from '../theme';

const OPTIONS: { value: boolean; label: string }[] = [
  { value: false, label: 'All days' },
  { value: true, label: 'Special days' },
];

/** Session toggle: when on, show only "special days" deals — day-limited specials
 *  whose sale window is shorter than the normal Mon–Sat week (a Thu–Sat
 *  Wochenend-Kracher, a Friday-only deal, …), regardless of today's weekday. `count` is
 *  the number of day-limited offers, shown on the "Special days" pill. */
export function SpecialDaysToggle({
  value,
  count,
  onChange,
}: {
  value: boolean;
  count: number;
  onChange: (value: boolean) => void;
}) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.row}
    >
      <Text style={styles.label}>Days</Text>
      {OPTIONS.map((o) => {
        const active = value === o.value;
        const label = o.value ? `${o.label} (${count})` : o.label;
        return (
          <Pressable
            key={String(o.value)}
            onPress={() => onChange(o.value)}
            style={[styles.pill, active && styles.pillActive]}
          >
            <Text style={[styles.text, active && styles.textActive]}>{label}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 0 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 12, paddingBottom: 8 },
  label: { color: colors.muted, fontSize: 12, fontWeight: '600', marginRight: 2 },
  pill: {
    height: 30,
    paddingHorizontal: 12,
    borderRadius: 999,
    backgroundColor: colors.card2,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  text: { color: colors.muted, fontSize: 12, fontWeight: '600' },
  textActive: { color: '#08130c' },
});
