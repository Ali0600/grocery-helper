import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { SortMode } from '../storage';
import { colors } from '../theme';

const OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'discount', label: 'Top deals' },
  { value: 'unit', label: 'Cheapest €/kg' },
];

export function SortToggle({
  mode,
  onChange,
}: {
  mode: SortMode;
  onChange: (mode: SortMode) => void;
}) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>Sort</Text>
      {OPTIONS.map((o) => {
        const active = mode === o.value;
        return (
          <Pressable
            key={o.value}
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
