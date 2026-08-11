import { colors } from './theme';

/** Display data for the supermarket chains, shared by the offer cards, the stores
 * directory, and the store filter so the labels + brand colours stay in one place. */
export const CHAIN_LABELS: Record<string, string> = {
  lidl: 'Lidl',
  rewe: 'REWE',
  edeka: 'Edeka',
  edeka_center: 'E center',
  // ALDI Nord and ALDI SÜD are separate companies, but their territories are disjoint — the
  // backend scrapes whichever one operates at the PLZ, so only ever one "Aldi" is present.
  // Which division it is shows in the store name, not the chip.
  aldi: 'Aldi',
  penny: 'Penny',
  rossmann: 'Rossmann', // drugstore vertical
  dm: 'dm', // drugstore vertical — lowercase is the brand's own styling
};

export const CHAIN_COLORS: Record<string, { bg: string; fg: string }> = {
  lidl: { bg: 'rgba(0,90,200,0.18)', fg: '#6ea8ff' }, // Lidl blue
  rewe: { bg: 'rgba(204,12,45,0.18)', fg: '#ff8597' }, // REWE red
  edeka: { bg: 'rgba(255,205,0,0.16)', fg: '#ffd84d' }, // EDEKA yellow
  edeka_center: { bg: 'rgba(255,140,0,0.18)', fg: '#ffb15c' }, // E center orange (vs EDEKA yellow)
  // ALDI's own navy+orange would collide with Lidl's blue and E center's orange, so the
  // pill uses its lighter cyan instead — the point is telling the chains apart at a glance.
  aldi: { bg: 'rgba(0,170,190,0.18)', fg: '#5fd6de' },
  // Penny's own red is the same family as REWE's (they are both REWE Group), and the two
  // sit side by side in the grocery list — so the pill takes Penny's secondary yellow-
  // orange instead. It has to stay clear of EDEKA's yellow and E center's orange too,
  // hence the warmer, deeper tone.
  penny: { bg: 'rgba(212,105,20,0.20)', fg: '#f0a35e' },
  // Rossmann's own red would read as `colors.badge` (#e8453c), which means discount/error
  // everywhere else in the app — so its pill uses a distinct magenta instead. It only ever
  // shares a screen with other drugstore chains, so it needn't dodge the grocery palette.
  rossmann: { bg: 'rgba(214,51,132,0.18)', fg: '#f472b6' },
  // dm's own blue — must not read as Lidl's royal blue, and must stay clear of
  // Rossmann's pink since the two sit side by side in the drugstore vertical.
  dm: { bg: 'rgba(0,150,214,0.18)', fg: '#38bdf8' },
};

export function chainLabel(chain: string): string {
  return CHAIN_LABELS[chain] ?? chain.charAt(0).toUpperCase() + chain.slice(1);
}

export function chainColors(chain: string): { bg: string; fg: string } {
  return CHAIN_COLORS[chain] ?? { bg: colors.card2, fg: colors.muted };
}
