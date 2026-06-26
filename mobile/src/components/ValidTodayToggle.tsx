import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors } from '../theme';

const OPTIONS: { value: boolean; label: string }[] = [
  { value: false, label: 'All days' },
  { value: true, label: 'Valid today' },
];

/** Session toggle: when on, show only deals valid on today's weekday (day-limited
 *  specials like a Thu–Sat weekend offer drop off when they aren't on sale yet/anymore). */
export function ValidTodayToggle({
  value,
  onChange,
}: {
  value: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>Days</Text>
      {OPTIONS.map((o) => {
        const active = value === o.value;
        return (
          <Pressable
            key={String(o.value)}
            onPress={() => onChange(o.value)}
            style={[styles.pill, active && styles.pillActive]}
          >
            <Text style={[styles.text, active && styles.textActive]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
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
