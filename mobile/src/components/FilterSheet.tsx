import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppModal } from './AppModal';

import { chainLabel } from '../chains';
import { SORT_OPTIONS } from '../sort';
import { SortMode } from '../storage';
import { colors, font, radius, space } from '../theme';
import { Icon } from './Icon';

type Opt = { label: string; active: boolean; onPress: () => void };

// One selectable pill (used for every option in the sheet).
function Pill({ label, active, onPress }: Opt) {
  return (
    <Pressable onPress={onPress} style={[styles.pill, active && styles.pillActive]}>
      <Text style={[styles.pillText, active && styles.pillTextActive]}>{label}</Text>
    </Pressable>
  );
}

function Section({ title, options }: { title: string; options: Opt[] }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionLabel}>{title}</Text>
      <View style={styles.pillRow}>
        {options.map((o) => (
          <Pill key={o.label} {...o} />
        ))}
      </View>
    </View>
  );
}

// Bottom sheet holding every secondary filter + the sort selector, so the main
// screen stays a single filter bar. All controls live-update the deals list; the
// sheet is just where they're set. Each section is hidden when it has no data.
export function FilterSheet(props: {
  visible: boolean;
  onClose: () => void;
  onReset: () => void;
  sortMode: SortMode;
  onChangeSort: (m: SortMode) => void;
  // Hidden on the "My Categories" home: there's no single sort there — each shelf uses its
  // category's own default — so a single Sort selector would be misleading.
  hideSort?: boolean;
  // Store MEMBERSHIP lives in the Stores modal (Add/Added). This is different: a
  // transient single-select "Only show" lens for quickly peeking at one store's deals —
  // one tap isolates, one tap (All / the bar chip's ✕) restores. Session-only.
  chains: string[]; // the VISIBLE chains (membership already applied)
  chainCounts: Record<string, number>;
  storeLens: string | null;
  onChangeStoreLens: (chain: string | null) => void;
  hasDayLimited: boolean;
  dayLimitedCount: number;
  specialDays: boolean;
  onChangeSpecialDays: (v: boolean) => void;
  hasBio: boolean;
  bioCount: number;
  bioOnly: boolean;
  onChangeBio: (v: boolean) => void;
  showNonFood: boolean;
  nonFoodCount: number | null;
  onToggleNonFood: () => void;
  // Deals dismissed from the deal detail. This section is the ONLY way back to a hidden deal:
  // the lens reveals them so one can be reopened and un-hidden. Like every other section it
  // renders only when it has data — i.e. once something is actually hidden.
  hiddenCount: number;
  showHidden: boolean;
  onChangeShowHidden: (v: boolean) => void;
}) {
  const { visible, onClose, onReset } = props;
  return (
    <AppModal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} />
      <View style={styles.sheet}>
        <View style={styles.grabber} />
        <View style={styles.headerRow}>
          <Text style={styles.title}>Filters & sort</Text>
          <View style={styles.headerActions}>
            <Pressable onPress={onReset} hitSlop={6}>
              <Text style={styles.reset}>Reset</Text>
            </Pressable>
            <Pressable onPress={onClose} hitSlop={6} accessibilityLabel="Close">
              <Icon name="close" size={22} color={colors.muted} />
            </Pressable>
          </View>
        </View>

        <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
          {!props.hideSort && (
            <Section
              title="Sort by"
              options={SORT_OPTIONS.map((o) => ({
                label: o.label,
                active: props.sortMode === o.value,
                onPress: () => props.onChangeSort(o.value),
              }))}
            />
          )}

          {props.chains.length >= 2 && (
            <Section
              title="Only show"
              options={[
                {
                  label: 'All',
                  active: props.storeLens == null,
                  onPress: () => props.onChangeStoreLens(null),
                },
                ...props.chains.map((c) => ({
                  label: `${chainLabel(c)} (${props.chainCounts[c] ?? 0})`,
                  active: props.storeLens === c,
                  // Tapping the active store again clears back to All.
                  onPress: () => props.onChangeStoreLens(props.storeLens === c ? null : c),
                })),
              ]}
            />
          )}

          {props.hasDayLimited && (
            <Section
              title="Sale days"
              options={[
                { label: 'All days', active: !props.specialDays, onPress: () => props.onChangeSpecialDays(false) },
                {
                  label: `Special days (${props.dayLimitedCount})`,
                  active: props.specialDays,
                  onPress: () => props.onChangeSpecialDays(true),
                },
              ]}
            />
          )}

          {props.hasBio && (
            <Section
              title="Organic"
              options={[
                { label: 'All', active: !props.bioOnly, onPress: () => props.onChangeBio(false) },
                {
                  label: `Bio only (${props.bioCount})`,
                  active: props.bioOnly,
                  onPress: () => props.onChangeBio(true),
                },
              ]}
            />
          )}

          <Section
            title="Non-food"
            options={[
              { label: 'Hidden', active: !props.showNonFood, onPress: () => props.showNonFood && props.onToggleNonFood() },
              {
                label: props.nonFoodCount ? `Shown (${props.nonFoodCount})` : 'Shown',
                active: props.showNonFood,
                onPress: () => !props.showNonFood && props.onToggleNonFood(),
              },
            ]}
          />

          {/* Only route back to a hidden deal, so it must appear whenever anything is hidden.
              Labels stay clear of the Non-food section's "Hidden"/"Shown" pills above. */}
          {props.hiddenCount > 0 && (
            <Section
              title="Hidden deals"
              options={[
                {
                  label: 'Hide',
                  active: !props.showHidden,
                  onPress: () => props.showHidden && props.onChangeShowHidden(false),
                },
                {
                  label: `Show hidden (${props.hiddenCount})`,
                  active: props.showHidden,
                  onPress: () => !props.showHidden && props.onChangeShowHidden(true),
                },
              ]}
            />
          )}
        </ScrollView>

        <Pressable style={styles.done} onPress={onClose}>
          <Text style={styles.doneText}>Done</Text>
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
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: space.lg },
  reset: { ...font.label, color: colors.accent },
  body: { marginTop: space.sm },
  bodyContent: { paddingBottom: space.md },
  section: { marginTop: space.lg },
  sectionLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: space.sm,
  },
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  pill: {
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
