import { colors } from './theme';

/** Display data for the supermarket chains, shared by the offer cards, the stores
 * directory, and the store filter so the labels + brand colours stay in one place. */
export const CHAIN_LABELS: Record<string, string> = { lidl: 'Lidl', rewe: 'REWE', edeka: 'Edeka' };

export const CHAIN_COLORS: Record<string, { bg: string; fg: string }> = {
  lidl: { bg: 'rgba(0,90,200,0.18)', fg: '#6ea8ff' }, // Lidl blue
  rewe: { bg: 'rgba(204,12,45,0.18)', fg: '#ff8597' }, // REWE red
  edeka: { bg: 'rgba(255,205,0,0.16)', fg: '#ffd84d' }, // EDEKA yellow
};

export function chainLabel(chain: string): string {
  return CHAIN_LABELS[chain] ?? chain.charAt(0).toUpperCase() + chain.slice(1);
}

export function chainColors(chain: string): { bg: string; fg: string } {
  return CHAIN_COLORS[chain] ?? { bg: colors.card2, fg: colors.muted };
}
