/**
 * What each tier actually draws. The load-bearing assertion is the first one: tier 0 must
 * render NOTHING — not an empty frame, not a "no history yet" line. 93.75% of products have
 * a single data point, so a placeholder would be the dominant visual on this page and would
 * read as a broken feature rather than an honest absence.
 */
import { render, screen } from '@testing-library/react-native';
import React from 'react';

import { PriceTrail } from '../components/PriceTrail';
import { PriceTrail as Trail } from '../priceHistory';

const point = (week: string, cents: number) => ({ week, cents, unitCents: null });

const base = { chain: 'lidl', crossChain: false, label: 'Test' };

describe('PriceTrail', () => {
  it('tier 0 renders NOTHING AT ALL — no placeholder, no empty frame', async () => {
    const { toJSON } = await render(<PriceTrail trail={{ tier: 0 }} />);
    expect(toJSON()).toBeNull();
  });

  it('tier 1 states the single observation without implying a trend', async () => {
    const trail: Trail = { tier: 1, ...base, cents: 179, week: 'W29' };
    await render(<PriceTrail trail={trail} />);
    expect(screen.getByText(/Seen once/)).toBeTruthy();
    expect(screen.getByText('1,79 €')).toBeTruthy();
    // No stats vocabulary may appear — there is nothing to compare against.
    expect(screen.queryByText(/usual/)).toBeNull();
    expect(screen.queryByText(/low /)).toBeNull();
  });

  it('tier 2 shows the delta, and a DROP is the accented one', async () => {
    const trail: Trail = {
      tier: 2,
      ...base,
      weeksSeen: 2,
      firstCents: 199,
      lastCents: 149,
      deltaPct: -25,
    };
    await render(<PriceTrail trail={trail} />);
    const delta = screen.getByText(/-25%/);
    // Down = accent (good news). Never colors.badge (#e8453c) — in this app that red means
    // discount/error, so using it for "the price went up" would invert the meaning.
    expect(JSON.stringify(delta.props.style)).toContain('#3ddc84');
    expect(JSON.stringify(delta.props.style)).not.toContain('#e8453c');
  });

  it('tier 3 FLAT says "always", never a tautological low-vs-usual', async () => {
    const trail: Trail = {
      tier: 3,
      ...base,
      weeksSeen: 5,
      series: [point('2026-W27', 69), point('2026-W28', 69), point('2026-W29', 69)],
      min: 69,
      median: 69,
      max: 69,
      minWeek: 'W27',
      flat: true,
      noisy: false,
      verdict: 'true_low',
      todayPctOfUsual: 100,
    };
    await render(<PriceTrail trail={trail} />);
    expect(screen.getByText(/always/)).toBeTruthy();
    expect(screen.queryByText(/usual 0,69/)).toBeNull();
  });

  it('tier 3 NOISY suppresses the stats and says why, but keeps the shape', async () => {
    const trail: Trail = {
      tier: 3,
      ...base,
      weeksSeen: 5,
      series: [point('2026-W27', 399), point('2026-W28', 69), point('2026-W29', 1169)],
      min: 69,
      median: 399,
      max: 1169,
      minWeek: 'W28',
      flat: false,
      noisy: true,
      verdict: null,
      todayPctOfUsual: null,
    };
    await render(<PriceTrail trail={trail} />);
    expect(screen.getByText(/pack sizes may differ/)).toBeTruthy();
    // The numbers it would otherwise state are the ones that would be wrong.
    expect(screen.queryByText(/low /)).toBeNull();
    expect(screen.queryByText(/of usual/)).toBeNull();
    expect(screen.queryByText(/Above usual/)).toBeNull();
  });

  it('tier 3 normal states low + usual and the verdict', async () => {
    const trail: Trail = {
      tier: 3,
      ...base,
      weeksSeen: 3,
      series: [point('2026-W27', 175), point('2026-W29', 149), point('2026-W31', 249)],
      min: 149,
      median: 175,
      max: 249,
      minWeek: 'W29',
      flat: false,
      noisy: false,
      verdict: 'worse',
      todayPctOfUsual: 142,
    };
    await render(<PriceTrail trail={trail} />);
    expect(screen.getByText(/low /)).toBeTruthy();
    expect(screen.getByText(/Above usual/)).toBeTruthy();
    expect(screen.getByText('142%')).toBeTruthy();
  });

  // These two were one test with a manual `unmount()` in the middle. Don't put it back:
  // after an explicit unmount, `screen` keeps pointing at the dead tree for the REST OF THE
  // FILE, so a later test's assertions silently run against an empty render and pass or
  // fail for reasons that have nothing to do with the code. Two tests, RNTL's own cleanup.
  it('does NOT name the chain when the history is the one the user bought from', async () => {
    const own: Trail = { tier: 1, ...base, cents: 100, week: 'W30' };
    await render(<PriceTrail trail={own} />);
    expect(screen.queryByText(/history$/)).toBeNull();
  });

  it('names the chain when the history came from a DIFFERENT one', async () => {
    // Silently attributing REWE's price history to a Lidl purchase would be a lie the user
    // has no way to detect.
    const cross: Trail = {
      tier: 1,
      ...base,
      chain: 'rewe',
      crossChain: true,
      cents: 100,
      week: 'W30',
    };
    await render(<PriceTrail trail={cross} />);
    expect(screen.getByText(/REWE history/)).toBeTruthy();
  });

  it('draws one sparkline bar per observation', async () => {
    const trail: Trail = {
      tier: 3,
      ...base,
      weeksSeen: 4,
      series: [point('2026-W27', 100), point('2026-W28', 200), point('2026-W29', 150)],
      min: 100,
      median: 150,
      max: 200,
      minWeek: 'W27',
      flat: false,
      noisy: false,
      verdict: null,
      todayPctOfUsual: null,
    };
    await render(<PriceTrail trail={trail} />);
    // The sparkline is DECORATIVE and deliberately hidden from screen readers: every number
    // it encodes is already stated as text above it, so announcing eight unlabelled bars
    // would be noise. That hiding also makes it unreachable via `*ByTestId` (RNTL filters
    // on accessibility, and `includeHiddenElements` does not lift `no-hide-descendants`
    // here), so count the rendered tree instead of querying it.
    expect(screen.queryAllByTestId('spark-bar')).toHaveLength(0); // pins the hiding
    // `screen.toJSON()`, not the destructured one: a previous test in this file calls
    // `unmount()`, after which the destructured helper returns null and every match here
    // silently becomes zero — a green-looking assertion over an empty tree.
    // `spark-bar` appears only as this testID, so counting occurrences is unambiguous.
    const j = JSON.stringify(screen.toJSON());
    expect(j.split('spark-bar').length - 1).toBe(3); // one bar per observation
  });
});
