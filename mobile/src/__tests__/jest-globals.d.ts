// Makes the Jest ambient globals (describe/it/expect/jest/…) visible to `tsc --noEmit`
// without restricting the project's `compilerOptions.types`. Picked up via `include`.
/// <reference types="jest" />
