/** The join key into the `grocery-price-history` dataset — NOT the app's own product identity.
 *
 * A verbatim port of `grocery-price-history/src/normalize.ts`, which is itself the careful port
 * of `grocery-helper/backend/app/dedup.py::_norm_name`. The collector keys every product on
 * `(region, chain, name_key)`, so this must agree with it exactly or a lookup silently misses.
 *
 * ── Why this is NOT `normName` (edekaVs.ts) ──────────────────────────────────────────────────
 * `normName` keeps only `[a-z0-9äöüß]`, so it maps an apostrophe to a SPACE and deletes accents
 * outright; `nameKey` DELETES apostrophes and KEEPS accents. Measured on a real snapshot they
 * disagree on 4% of names — 55 of 1,388:
 *     "Lay's Bugles"    normName "lay s bugles"    nameKey "lays bugles"
 *     "NESCAFÉ Gold"    normName "nescaf gold"     nameKey "nescafé gold"
 *     "Schäfer's …"     normName "schäfer s …"     nameKey "schäfers …"
 * Both must exist, and `normName` must NOT be "fixed" to match: it is the app's PERSISTED
 * identity (`HistoryItem.key`, and `HiddenItem.key`'s second half), so changing it would orphan
 * every entry already on the user's device — silently, with no migration signal. The divergence
 * test asserts both columns so that reasoning survives contact with a future tidy-up.
 *
 * ── Hermes ───────────────────────────────────────────────────────────────────────────────────
 * The grade regex uses a LOOKBEHIND and `\p{…}` under `/u`. Jest runs on Node/V8 where both are
 * fine, so a green suite proves nothing about the device. Checked against Hermes' own compiler
 * (`node_modules/hermes-compiler/.../hermesc`), which validates regex literals at build time:
 * this file compiles clean (exit 0), while `/\p{NotARealProperty}/gu` is rejected with "Invalid
 * property name" and `/(?<=abc/gu` with "Parenthesized expression not closed" (both exit 2). So
 * the instrument demonstrably fails on unsupported syntax — the pass is real, not a no-op.
 * Python's `\w`/`\b` are Unicode-aware and JavaScript's are ASCII-only, which is why the
 * explicit classes and lookarounds are required rather than cosmetic.
 */
const GRADE = /(?<![\p{L}\p{N}_])kl(?:asse)?\.?\s*(?:i{1,3}|[123])(?![\p{L}\p{N}_])/gu;

export function nameKey(name: string | null | undefined): string {
  let s = (name ?? '').normalize('NFKC').toLowerCase();
  // split/join rather than the upstream's `replaceAll` — the only deviation from a verbatim
  // copy, and it's for Hermes: identical semantics for a literal, no ES2021 dependency.
  for (const ch of ['’', '‘', '`', '´', "'"]) s = s.split(ch).join('');
  s = s.replace(GRADE, ' ');
  s = s.replace(/[^\p{L}\p{N}_ ]+/gu, ' ');
  return s.replace(/\s+/g, ' ').trim();
}
