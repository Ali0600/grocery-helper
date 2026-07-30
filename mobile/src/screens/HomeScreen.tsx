import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Icon } from '../components/Icon';
import { getDealsCache } from '../storage';
import { colors, font, radius, space } from '../theme';
import {
  Vertical,
  VERTICAL_BLURBS,
  VERTICAL_ICONS,
  VERTICAL_LABELS,
  VERTICALS,
} from '../verticals';

type Props = { onPick: (v: Vertical) => void };

/**
 * The app's landing screen: one big button per vertical.
 *
 * The subtitle shows that vertical's **cached deal count** when there is one, falling back
 * to a short blurb otherwise. Deliberately not a hardcoded chain list — that would be a
 * second source of truth for "which chains are grocery" (the backend owns that) and would
 * go stale the moment a chain is added.
 */
export default function HomeScreen({ onPick }: Props) {
  const [counts, setCounts] = useState<Partial<Record<Vertical, number>>>({});

  useEffect(() => {
    let alive = true;
    (async () => {
      const entries = await Promise.all(
        VERTICALS.map(async (v) => [v, (await getDealsCache(v))?.offers.length] as const),
      );
      if (!alive) return;
      setCounts(Object.fromEntries(entries.filter(([, n]) => n != null)));
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>Grocery Helper</Text>
      <Text style={styles.subtitle}>What are you shopping for?</Text>

      <View style={styles.cards}>
        {VERTICALS.map((v) => {
          const n = counts[v];
          const sub = n != null ? `${n.toLocaleString('de-DE')} deals` : VERTICAL_BLURBS[v];
          return (
            <Pressable
              key={v}
              style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
              onPress={() => onPick(v)}
              accessibilityRole="button"
              accessibilityLabel={`${VERTICAL_LABELS[v]}, ${sub}`}
              testID={`vertical-${v}`}
            >
              <View style={styles.iconWrap}>
                <Icon name={VERTICAL_ICONS[v]} size={30} color={colors.accent} />
              </View>
              <Text style={styles.cardTitle}>{VERTICAL_LABELS[v]}</Text>
              <Text style={styles.cardSub}>{sub}</Text>
            </Pressable>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: space.lg,
    paddingVertical: space.xl,
    backgroundColor: colors.bg,
  },
  title: { ...font.title, color: colors.text, textAlign: 'center' },
  subtitle: {
    ...font.body,
    color: colors.muted,
    textAlign: 'center',
    marginTop: space.xs,
    marginBottom: space.xl,
  },
  cards: { gap: space.lg },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: space.xl,
    paddingHorizontal: space.lg,
    alignItems: 'center',
  },
  cardPressed: { backgroundColor: colors.card2 },
  iconWrap: { marginBottom: space.md },
  cardTitle: { ...font.h2, color: colors.text },
  cardSub: { ...font.small, color: colors.muted, marginTop: space.xs },
});
