import React from 'react';
import { Modal, ModalProps, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

// react-native's <Modal> renders its content in a SEPARATE native root, outside the app's
// top-level GestureHandlerRootView (App.tsx). The RNGH docs require each modal to have its OWN
// GestureHandlerRootView, so every modal in the app uses this wrapper in place of <Modal> — it
// can't regress in a new modal that forgets it.
//
// CAVEAT, verified 2026-07-17: this is load-bearing on ANDROID only. GestureHandlerRootView ships
// just `.android.tsx` and `.web.tsx` variants, so iOS falls through to the generic one — a plain
// <View> + a context provider — and `RNGestureHandlerRootViewCls()` returns nil ("RNGestureHandler
// RootView is Android-only", apple/RNGestureHandlerRootViewComponentView.mm). So on iOS this
// wrapper creates nothing native, and the app-wide-freeze story this file used to tell as its
// rationale cannot be the iOS mechanism. Keep the wrapper; don't trust that explanation.
//
// Rendering a modal INSIDE another modal's children is deliberate and required — see LikesModal:
// RN presents from the first view controller up the responder chain, so sibling modals share the
// root VC and iOS refuses the second one.
export function AppModal({ children, ...props }: ModalProps) {
  return (
    <Modal {...props}>
      <GestureHandlerRootView style={styles.root}>{children}</GestureHandlerRootView>
    </Modal>
  );
}

const styles = StyleSheet.create({ root: { flex: 1 } });
