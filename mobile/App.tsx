import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StatusBar } from 'expo-status-bar';
import { Platform, StyleSheet, View } from 'react-native';

import DealsScreen from './src/screens/DealsScreen';
import { colors } from './src/theme';
import { useOtaUpdates } from './src/useOtaUpdates';

export default function App() {
  // Prompt to reload when an OTA update is available (no-op in dev / web).
  useOtaUpdates();

  // On the web, center the phone-width app in a column so it doesn't stretch
  // across a wide desktop window; native renders the screen full-bleed.
  if (Platform.OS === 'web') {
    return (
      <GestureHandlerRootView style={styles.root}>
        <View style={styles.webPage}>
          <StatusBar style="light" />
          <View style={styles.webColumn}>
            <DealsScreen />
          </View>
        </View>
      </GestureHandlerRootView>
    );
  }

  return (
    <GestureHandlerRootView style={styles.root}>
      <StatusBar style="light" />
      <DealsScreen />
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
