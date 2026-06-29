import { Ionicons } from '@expo/vector-icons';
import React from 'react';

import { colors } from '../theme';

// Thin wrapper over the icon set so the app references one component (and one set —
// Ionicons) everywhere; swap the underlying set here if it ever changes.
export type IconName = React.ComponentProps<typeof Ionicons>['name'];

export function Icon({
  name,
  size = 18,
  color = colors.text,
  style,
}: {
  name: IconName;
  size?: number;
  color?: string;
  style?: React.ComponentProps<typeof Ionicons>['style'];
}) {
  return <Ionicons name={name} size={size} color={color} style={style} />;
}
