import React from 'react';
import { Modal, ModalProps, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

// react-native's <Modal> renders its content in a SEPARATE native root, outside the app's
// top-level GestureHandlerRootView (App.tsx). With react-native-gesture-handler installed,
// interacting with (scroll / press) then dismissing such a modal can leave the gesture root
// capturing every touch — an app-wide freeze (no taps, no scroll). The RNGH docs require each
// modal to have its OWN GestureHandlerRootView, so every modal in the app uses this wrapper in
// place of <Modal> — it can't regress in a new modal that forgets it.
export function AppModal({ children, ...props }: ModalProps) {
  return (
    <Modal {...props}>
      <GestureHandlerRootView style={styles.root}>{children}</GestureHandlerRootView>
    </Modal>
  );
}

const styles = StyleSheet.create({ root: { flex: 1 } });
