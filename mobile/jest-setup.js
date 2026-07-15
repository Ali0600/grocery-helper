// Jest environment setup for component tests (React Native Testing Library).
//
// jest-expo's preset does not set `IS_REACT_ACT_ENVIRONMENT`, and React 19 refuses to run
// `act()` without it — RNTL's `render` wraps in `act()` internally, so every component test
// died with "render function has not been called" (the real cause being swallowed).
global.IS_REACT_ACT_ENVIRONMENT = true;

// The official in-memory AsyncStorage mock, so storage-touching components (DealsScreen,
// anything using src/storage.ts) are testable. Each test seeds it via plain setItem calls;
// state is cleared between tests below.
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

// Vector icons load fonts through expo-asset, which Metro resolves transitively but jest
// cannot. Every icon in the app goes through components/Icon.tsx -> Ionicons; a queryable
// text stub ("icon:<name>") keeps component tests rendering without the font machinery.
jest.mock('@expo/vector-icons', () => {
  const React = require('react');
  const { Text } = require('react-native');
  const Ionicons = ({ name }) => React.createElement(Text, null, `icon:${name}`);
  return { Ionicons };
});

beforeEach(() => {
  const mod = require('@react-native-async-storage/async-storage');
  (mod.default ?? mod).clear();
});

// Silence the Animated/act noise RN emits under test; real failures still surface.
jest.spyOn(console, 'error').mockImplementation((...args) => {
  const msg = String(args[0] ?? '');
  if (msg.includes('not configured to support act(')) return;
  console.warn(...args);
});
