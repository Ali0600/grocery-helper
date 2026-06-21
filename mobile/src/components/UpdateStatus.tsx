import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { fmtAsOf } from '../format';
import { colors } from '../theme';

type Props = {
  updatedAt: number | null; // when the shown deals were fetched (cache or live)
  updating: boolean; // a background refresh is in flight
  stale: boolean; // cached deals are past their weekly (Sunday) expiry
  offline: boolean; // last refresh failed but cache is shown
};

// A thin status line under the header: tells the user the deals are saved/cached, when
// they were last updated, and whether a refresh is happening, failed, or is overdue.
export function UpdateStatus({ updatedAt, updating, stale, offline }: Props) {
  if (updatedAt == null) return null; // true cold start — the spinner is showing instead

  const tail = updating ? 'updating…' : offline ? "couldn't update" : null;

  if (stale) {
    return (
      <View style={[styles.row, styles.staleRow]}>
        <Text style={styles.staleText} numberOfLines={1}>
          ⚠ Deals may have expired{tail ? ` · ${tail}` : ` · as of ${fmtAsOf(updatedAt)}`}
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.row}>
      <Text style={styles.text} numberOfLines={1}>
        Deals as of {fmtAsOf(updatedAt)}
        {tail ? ` · ${tail}` : ''}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { paddingHorizontal: 16, paddingTop: 2, paddingBottom: 4 },
  text: { color: colors.muted, fontSize: 12 },
  staleRow: {
    backgroundColor: 'rgba(240,180,60,0.12)',
    paddingVertical: 5,
    marginTop: 2,
    borderRadius: 8,
    marginHorizontal: 12,
  },
  staleText: { color: '#e6b34d', fontSize: 12, fontWeight: '600' },
});
