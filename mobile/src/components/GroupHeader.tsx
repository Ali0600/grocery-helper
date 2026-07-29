import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { euro } from '../format';
import { colors } from '../theme';

/**
 * Section header for a product group inside a category (e.g. "Avocado · 2 offers ·
 * from 0,88 €"). Every sub-group gets one, including a lone offer ("Kiwi · 1 offer ·
 * from 2,49 €") — "the only Kiwi deal this week" is real information. `muted` renders
 * the small "More" header above the trailing bucket of offers with no sub-group.
 */
export function GroupHeader({
  label,
  count,
  fromCents,
  muted,
}: {
  label: string;
  count?: number;
  fromCents?: number | null;
  muted?: boolean;
}) {
  return (
    <View style={styles.row}>
      <Text style={muted ? styles.labelMuted : styles.label}>{label}</Text>
      {!muted && count != null ? (
        <Text style={styles.meta} testID="group-header-meta">
          {/* Singular matters: every sub-group gets a header now, including one-offer ones. */}
          {count} offer{count === 1 ? '' : 's'}
          {fromCents != null ? (
            <Text style={styles.from}>{`  ·  from ${euro(fromCents)}`}</Text>
          ) : null}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    backgroundColor: colors.bg,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 4,
  },
  label: { color: colors.text, fontSize: 14, fontWeight: '700' },
  labelMuted: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  meta: { color: colors.muted, fontSize: 12, fontWeight: '600' },
  from: { color: colors.accent, fontWeight: '700' },
});
