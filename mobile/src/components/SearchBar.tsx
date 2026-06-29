import React from 'react';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { colors, radius, space } from '../theme';
import { Icon } from './Icon';

type Props = {
  value: string;
  onChange: (text: string) => void;
};

export function SearchBar({ value, onChange }: Props) {
  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <Icon name="search" size={17} color={colors.muted} />
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
          <Pressable onPress={() => onChange('')} hitSlop={10} accessibilityLabel="Clear search">
            <Icon name="close-circle" size={18} color={colors.muted} />
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { paddingHorizontal: space.md, paddingTop: space.sm, paddingBottom: space.sm },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    backgroundColor: colors.card2,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 14,
  },
  input: { flex: 1, color: colors.text, fontSize: 16, paddingVertical: 11 },
});
