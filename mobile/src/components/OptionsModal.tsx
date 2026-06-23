import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { fmtAsOf } from '../format';
import { colors } from '../theme';

type ActionKey = 'clearCache' | 'resetAll' | 'rescrape' | 'wipeServer';

type Props = {
  visible: boolean;
  plz: string;
  updatedAt: number | null;
  apiBase: string;
  onClose: () => void;
  // Each returns a short result message to show; throws on failure.
  onClearCache: () => Promise<string>;
  onResetAll: () => Promise<string>;
  onRescrape: () => Promise<string>;
  onWipeServer: () => Promise<string>;
};

export function OptionsModal({
  visible,
  plz,
  updatedAt,
  apiBase,
  onClose,
  onClearCache,
  onResetAll,
  onRescrape,
  onWipeServer,
}: Props) {
  const [busy, setBusy] = useState<ActionKey | null>(null);
  const [pending, setPending] = useState<ActionKey | null>(null); // destructive: awaiting confirm
  const [status, setStatus] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  // Fresh state every time the sheet opens.
  useEffect(() => {
    if (visible) {
      setBusy(null);
      setPending(null);
      setStatus(null);
      setFailed(false);
    }
  }, [visible]);

  const run = async (key: ActionKey, fn: () => Promise<string>) => {
    setBusy(key);
    setPending(null);
    setStatus(null);
    setFailed(false);
    try {
      setStatus(await fn());
    } catch (e) {
      setFailed(true);
      setStatus(`Failed: ${e instanceof Error ? e.message : 'unknown error'}`);
    } finally {
      setBusy(null);
    }
  };

  const cacheLine = updatedAt ? `Deals cached ${fmtAsOf(updatedAt)}` : 'No cached deals yet';

  // A plain render helper (not a component) so it isn't re-created during render.
  const renderAction = ({
    k,
    title,
    subtitle,
    destructive,
    confirmLabel,
    fn,
  }: {
    k: ActionKey;
    title: string;
    subtitle: string;
    destructive?: boolean;
    confirmLabel?: string;
    fn: () => Promise<string>;
  }) => {
    const isBusy = busy === k;
    const isPending = pending === k;
    const disabled = busy !== null;
    return (
      <View style={styles.action}>
        {isPending ? (
          <View style={styles.confirmRow}>
            <Pressable
              style={({ pressed }) => [styles.btn, styles.btnGhost, pressed && styles.pressed]}
              onPress={() => setPending(null)}
            >
              <Text style={styles.btnGhostText}>Cancel</Text>
            </Pressable>
            <Pressable
              style={({ pressed }) => [styles.btn, styles.btnDanger, pressed && styles.pressed]}
              onPress={() => run(k, fn)}
            >
              <Text style={styles.btnDangerText}>{confirmLabel ?? 'Confirm'}</Text>
            </Pressable>
          </View>
        ) : (
          <Pressable
            style={({ pressed }) => [
              styles.btn,
              destructive ? styles.btnDangerOutline : styles.btnOutline,
              disabled && styles.btnDisabled,
              pressed && styles.pressed,
            ]}
            onPress={() => (destructive ? setPending(k) : run(k, fn))}
            disabled={disabled}
          >
            {isBusy ? (
              <ActivityIndicator color={destructive ? colors.badge : colors.accent} />
            ) : (
              <Text style={destructive ? styles.btnDangerOutlineText : styles.btnOutlineText}>
                {title}
              </Text>
            )}
          </Pressable>
        )}
        <Text style={styles.actionSub}>{subtitle}</Text>
      </View>
    );
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Options</Text>
            <Pressable onPress={onClose} hitSlop={10}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>

          <ScrollView contentContainerStyle={styles.body}>
            <Text style={styles.sectionLabel}>THIS DEVICE</Text>
            <Text style={styles.meta}>
              PLZ {plz} · {cacheLine}
            </Text>
            {renderAction({
              k: 'clearCache',
              title: 'Clear cached deals & reload',
              subtitle:
                'Drops the on-device cache and re-downloads now — use this when deals look stale and won’t update.',
              fn: onClearCache,
            })}
            {renderAction({
              k: 'resetAll',
              title: 'Reset all app data',
              subtitle: 'Clears PLZ, saved stores, basket, sort, and cache — back to a fresh install.',
              destructive: true,
              confirmLabel: 'Reset everything',
              fn: onResetAll,
            })}

            <View style={styles.divider} />

            <Text style={styles.sectionLabel}>ON THE SERVER</Text>
            <Text style={styles.meta} numberOfLines={1}>
              {apiBase.replace(/^https?:\/\//, '')}
            </Text>
            {renderAction({
              k: 'rescrape',
              title: `Re-scrape deals (${plz})`,
              subtitle: "Backend re-fetches this week's flyers and upserts them. Slow on a cold start.",
              fn: onRescrape,
            })}
            {renderAction({
              k: 'wipeServer',
              title: 'Wipe & re-scrape server DB',
              subtitle:
                'Deletes every stored offer on the server, then re-scrapes from scratch (removes stale rows too).',
              destructive: true,
              confirmLabel: 'Wipe & re-scrape',
              fn: onWipeServer,
            })}

            {status ? (
              <Text style={[styles.status, failed && styles.statusFail]}>{status}</Text>
            ) : null}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingBottom: 28,
    maxHeight: '88%',
    borderWidth: 1,
    borderColor: colors.border,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: { color: colors.text, fontSize: 17, fontWeight: '700' },
  close: { color: colors.accent, fontSize: 15, fontWeight: '600' },
  body: { padding: 16 },
  sectionLabel: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
    marginBottom: 4,
  },
  meta: { color: colors.muted, fontSize: 12, marginBottom: 12 },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: 18 },
  action: { marginBottom: 14 },
  actionSub: { color: colors.muted, fontSize: 12, lineHeight: 17, marginTop: 6 },
  btn: { borderRadius: 12, paddingVertical: 13, alignItems: 'center', justifyContent: 'center' },
  btnOutline: { borderWidth: 1, borderColor: colors.accent, backgroundColor: colors.card },
  btnOutlineText: { color: colors.accent, fontSize: 15, fontWeight: '700' },
  btnDangerOutline: { borderWidth: 1, borderColor: colors.badge, backgroundColor: colors.card },
  btnDangerOutlineText: { color: colors.badge, fontSize: 15, fontWeight: '700' },
  btnDisabled: { opacity: 0.4 },
  pressed: { opacity: 0.75 },
  confirmRow: { flexDirection: 'row', gap: 10 },
  btnGhost: { flex: 1, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
  btnGhostText: { color: colors.text, fontSize: 15, fontWeight: '700' },
  btnDanger: { flex: 1, backgroundColor: colors.badge },
  btnDangerText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  status: {
    color: colors.accent,
    fontSize: 13,
    lineHeight: 18,
    marginTop: 6,
    fontWeight: '600',
  },
  statusFail: { color: colors.badge },
});
