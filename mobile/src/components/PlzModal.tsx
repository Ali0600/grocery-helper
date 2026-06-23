import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { api } from '../api';
import { colors } from '../theme';

type Props = {
  visible: boolean;
  initialPlz: string;
  onClose: () => void;
  onApplied: (plz: string, storeName: string | null) => void;
};

export function PlzModal({ visible, initialPlz, onClose, onApplied }: Props) {
  const [plz, setPlz] = useState(initialPlz);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset to the current PLZ each time the sheet opens.
  useEffect(() => {
    if (visible) {
      setPlz(initialPlz);
      setError(null);
      setSubmitting(false);
    }
  }, [visible, initialPlz]);

  const valid = /^\d{5}$/.test(plz);

  const submit = async () => {
    if (!valid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.scrape(plz);
      const store = res.stores.find((s) => s.plz === plz) ?? res.stores[0] ?? null;
      // A null market_code means no real store resolved (sample-data fallback).
      if (!store || !store.market_code) {
        setError('No Lidl store found for that postal code. Try another nearby PLZ.');
        setSubmitting(false);
        return;
      }
      onApplied(plz, store.name);
    } catch {
      setError(`Could not load deals from ${api.base}. Is the backend running?`);
      setSubmitting(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={styles.backdrop}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Set your postal code</Text>
            <Pressable onPress={onClose} hitSlop={10}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>

          <View style={styles.body}>
            <Text style={styles.label}>
              Enter a German postal code (PLZ) to find deals at your nearest Lidl.
            </Text>
            <TextInput
              style={styles.input}
              value={plz}
              onChangeText={(t) => setPlz(t.replace(/[^0-9]/g, '').slice(0, 5))}
              keyboardType="number-pad"
              placeholder="e.g. 10713"
              placeholderTextColor={colors.muted}
              maxLength={5}
              editable={!submitting}
              autoFocus
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}

            <Pressable
              style={({ pressed }) => [
                styles.btn,
                (!valid || submitting) && styles.btnDisabled,
                pressed && styles.btnPressed,
              ]}
              onPress={submit}
              disabled={!valid || submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#08130c" />
              ) : (
                <Text style={styles.btnText}>Use this PLZ</Text>
              )}
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
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
  label: { color: colors.muted, fontSize: 14, lineHeight: 20, marginBottom: 12 },
  input: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    color: colors.text,
    fontSize: 20,
    fontWeight: '600',
    letterSpacing: 2,
    paddingHorizontal: 16,
    paddingVertical: 14,
    textAlign: 'center',
  },
  error: { color: colors.badge, fontSize: 13, marginTop: 10, lineHeight: 18 },
  btn: {
    marginTop: 18,
    backgroundColor: colors.accent,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
  },
  btnDisabled: { opacity: 0.4 },
  btnPressed: { opacity: 0.8 },
  btnText: { color: '#08130c', fontSize: 15, fontWeight: '700' },
});
