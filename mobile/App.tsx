import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';

import DealsScreen from './src/screens/DealsScreen';
import HomeScreen from './src/screens/HomeScreen';
import { colors } from './src/theme';
import { useOtaUpdates } from './src/useOtaUpdates';
import { Vertical } from './src/verticals';

export default function App() {
  // Prompt to reload when an OTA update is available (no-op in dev / web).
  useOtaUpdates();

  // `null` = the home screen. This is the app's only "navigation": adding a router would
  // mean a native dependency (a new build, not an OTA), and the rest of the app already
  // navigates by rendering modals over one screen.
  //
  // Deliberately NOT persisted — the app always opens on Home, because the user framed
  // this as *the homepage* and either vertical is one tap away. One line to change.
  const [vertical, setVertical] = useState<Vertical | null>(null);

  const screen =
    vertical === null ? (
      <HomeScreen onPick={setVertical} />
    ) : (
      <DealsScreen vertical={vertical} onHome={() => setVertical(null)} />
    );

  // On the web, center the phone-width app in a column so it doesn't stretch
  // across a wide desktop window; native renders the screen full-bleed.
  if (Platform.OS === 'web') {
    return (
      <GestureHandlerRootView style={styles.root}>
        <View style={styles.webPage}>
          <StatusBar style="light" />
          <View style={styles.webColumn}>{screen}</View>
        </View>
      </GestureHandlerRootView>
    );
  }

  return (
    <GestureHandlerRootView style={styles.root}>
      <StatusBar style="light" />
      {screen}
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  webPage: { flex: 1, backgroundColor: '#08090c', alignItems: 'center' },
  webColumn: {
    flex: 1,
    width: '100%',
    maxWidth: 480,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: colors.border,
  },
});
