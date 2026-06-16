import React from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors } from '../theme';

type Props = {
  value: string;
  onChange: (text: string) => void;
};

export function SearchBar({ value, onChange }: Props) {
  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <TextInput
          style={styles.input}
          value={value}
          onChangeText={onChange}
          placeholder="Search deals…"
          placeholderTextColor={colors.muted}
          returnKeyType="search"
          autoCorrect={false}
          autoCapitalize="none"
        />
        {value.length > 0 ? (
          <Pressable onPress={() => onChange('')} hitSlop={10} style={styles.clearBtn}>
            <Text style={styles.clear}>✕</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 6,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.bg,
  },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card2,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 14,
  },
  input: { flex: 1, color: colors.text, fontSize: 16, paddingVertical: 11 },
  clearBtn: { paddingLeft: 8 },
  clear: { color: colors.muted, fontSize: 15, fontWeight: '600' },
});
