import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { euro } from '../format';
import { chainLabel } from '../chains';
import { PricePoint, PriceTrail as Trail, Verdict } from '../priceHistory';
import { colors, font, radius, space } from '../theme';

/**
 * The weekly price trail under a History row — rendered TIERED BY EVIDENCE.
 *
 * 93.75% of the collector's products have exactly one data point, so this component's most
 * important behaviour is that **tier 0 renders `null`**: no "no history yet" placeholder,
 * no empty chart frame, nothing. The row above it is already complete (what you paid vs
 * what it costs now is local data), and a placeholder on 94% of rows would read as a broken
 * feature rather than an honest absence.
 */

const VERDICT_LABEL: Record<Exclude<Verdict, 'new'>, string> = {
  true_low: 'Cheapest yet',
  typical: 'Usual price',
  worse: 'Above usual',
};

/**
 * Eight bars from plain Views — no charting dependency for what is a 60×18 pt sketch.
 * The cheapest bar is accented so the shape reads at a glance.
 */
function Sparkline({ series }: { series: PricePoint[] }) {
  const values = series.map((p) => p.cents);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return (
    <View style={styles.spark} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {series.map((p) => (
        <View
          key={p.week}
          testID="spark-bar"
          style={[
            styles.sparkBar,
            // 3–16pt: even the cheapest week keeps a visible stub, so the bar count is
            // always readable as "how many weeks do we have".
            { height: 3 + Math.round(((p.cents - min) / span) * 13) },
            p.cents === min && styles.sparkBarLow,
          ]}
        />
      ))}
    </View>
  );
}

export function PriceTrail({ trail }: { trail: Trail }) {
  if (trail.tier === 0) return null; // see the docstring — this is the feature

  // Whose history this is, stated only when it ISN'T the chain the user bought from.
  // Without it a cross-chain fallback silently attributes one shop's prices to another.
  const attribution =
    trail.crossChain ? <Text style={styles.attr}>{chainLabel(trail.chain)} history</Text> : null;

  if (trail.tier === 1) {
    return (
      <View style={styles.wrap} accessibilityLabel={`Seen once, ${euro(trail.cents)}, week ${trail.week}`}>
        <Text style={styles.line}>
          Seen once · <Text style={styles.strong}>{euro(trail.cents)}</Text> · {trail.week}
        </Text>
        {attribution}
      </View>
    );
  }

  if (trail.tier === 2) {
    const down = trail.lastCents < trail.firstCents;
    const pct = trail.deltaPct;
    return (
      <View style={styles.wrap}>
        <Text style={styles.line}>
          {trail.weeksSeen} weeks · {euro(trail.firstCents)} →{' '}
          <Text style={styles.strong}>{euro(trail.lastCents)}</Text>
          {pct !== null ? (
            // Down is good news (accent); up is merely information (muted). Never
            // colors.badge — in this app that red means discount/error, not "went up".
            <Text style={down ? styles.down : styles.up}>
              {'  '}
              {pct > 0 ? '+' : ''}
              {pct}%
            </Text>
          ) : null}
        </Text>
        {attribution}
      </View>
    );
  }

  return (
    <View style={styles.wrap}>
      <View style={styles.tier3Head}>
        {trail.verdict ? (
          <View style={styles.verdict}>
            <Text style={styles.verdictText}>{VERDICT_LABEL[trail.verdict]}</Text>
          </View>
        ) : null}
        <Sparkline series={trail.series} />
      </View>

      {trail.noisy ? (
        // The stats would describe a can, a bottle and a crate averaged together, so they
        // are suppressed rather than stated confidently. The shape still tells a story.
        <Text style={styles.caption}>
          {trail.weeksSeen} weeks · prices vary a lot — pack sizes may differ
        </Text>
      ) : (
        <Text style={styles.line}>
          {trail.weeksSeen} weeks ·{' '}
          {trail.flat ? (
            // min === max: "low X · usual X" is a tautology dressed up as insight.
            <>
              always <Text style={styles.strong}>{euro(trail.min)}</Text>
            </>
          ) : (
            <>
              low <Text style={styles.strong}>{euro(trail.min)}</Text>
              {trail.minWeek ? ` (${trail.minWeek})` : ''} · usual {euro(trail.median)}
            </>
          )}
        </Text>
      )}

      {trail.todayPctOfUsual !== null ? (
        <Text style={styles.line}>
          today{' '}
          <Text style={trail.todayPctOfUsual <= 100 ? styles.down : styles.up}>
            {trail.todayPctOfUsual}%
          </Text>{' '}
          of usual
        </Text>
      ) : null}
      {attribution}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: space.xs, gap: 2 },
  line: { ...font.small, color: colors.muted },
  strong: { color: colors.text, fontWeight: '700' },
  down: { color: colors.accent, fontWeight: '700' },
  up: { color: colors.muted, fontWeight: '700' },
  caption: { ...font.small, color: colors.muted, fontStyle: 'italic' },
  attr: { ...font.tiny, color: colors.muted },
  tier3Head: { flexDirection: 'row', alignItems: 'flex-end', gap: space.sm },
  verdict: {
    backgroundColor: colors.card2,
    borderRadius: radius.pill,
    paddingHorizontal: space.sm,
    paddingVertical: 2,
  },
  verdictText: { ...font.tiny, color: colors.text, fontWeight: '700' },
  spark: { flexDirection: 'row', alignItems: 'flex-end', gap: 2, height: 16 },
  sparkBar: { width: 4, borderRadius: 1, backgroundColor: colors.border },
  sparkBarLow: { backgroundColor: colors.accent },
});
