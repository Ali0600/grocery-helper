import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { chainColors, chainLabel } from '../chains';
import { colors } from '../theme';

/** A thin pill row to narrow the deals to one chain: "Store [All][Lidl][REWE][Edeka]".
 * `null` = All. The active chain pill uses that chain's brand colour. */
export function StoreFilter({
  chains,
  value,
  onChange,
}: {
  chains: string[];
  value: string | null;
  onChange: (chain: string | null) => void;
}) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>Store</Text>
      <Pressable
        onPress={() => onChange(null)}
        style={[styles.pill, value === null && styles.allActive]}
      >
        <Text style={[styles.text, value === null && styles.allActiveText]}>All</Text>
      </Pressable>
      {chains.map((chain) => {
        const active = value === chain;
        const c = chainColors(chain);
        return (
          <Pressable
            key={chain}
            onPress={() => onChange(chain)}
            style={[styles.pill, active && { backgroundColor: c.bg, borderColor: c.fg }]}
          >
            <Text style={[styles.text, active && { color: c.fg }]}>{chainLabel(chain)}</Text>
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
  allActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  text: { color: colors.muted, fontSize: 12, fontWeight: '600' },
  allActiveText: { color: '#08130c' },
});
