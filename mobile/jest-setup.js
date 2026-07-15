// Jest environment setup for component tests (React Native Testing Library).
//
// jest-expo's preset does not set `IS_REACT_ACT_ENVIRONMENT`, and React 19 refuses to run
// `act()` without it — RNTL's `render` wraps in `act()` internally, so every component test
// died with "render function has not been called" (the real cause being swallowed).
global.IS_REACT_ACT_ENVIRONMENT = true;

// Silence the Animated/act noise RN emits under test; real failures still surface.
jest.spyOn(console, 'error').mockImplementation((...args) => {
  const msg = String(args[0] ?? '');
  if (msg.includes('not configured to support act(')) return;
  // eslint-disable-next-line no-console
  console.warn(...args);
});
