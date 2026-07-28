// Turning the classifier's trace into something readable — pure, so it's unit-tested and
// the modal stays presentational. See backend/app/categories.py for the layer order.
//
// Layer names come from HERE, never from the wire: the bulk (prefetched) form drops the
// backend's `name` field to stay ~1.3 MB, so relying on it would make a cache-hit render
// differently from a network fallback.
import { CategoryTrace, TraceLayer } from './types';

export const LAYER_LABELS: Record<string, string> = {
  '0': 'Vegan',
  '1': 'Non-food path',
  '2': 'Form words',
  '2b': 'Flyer caption',
  // Kept short on purpose: at 375pt a longer label wraps and breaks the monospace column
  // alignment that makes the layer list scannable. The full path prints below the list.
  '3': 'Path node',
  '4': 'Brand map',
  '5': 'Flavour overrides',
  '6': 'Keyword rules',
  '7': 'Fallback',
};

// The closed vocabulary the backend sends for a skipped layer / a layer-1 branch.
const REASONS: Record<string, string> = {
  no_category_path: 'no category path',
  path_is_food_root: 'path is under the food root',
  no_unit: 'no flyer caption',
  rescue_veto: 'a veto word blocked the food rescue',
  no_rescue_token: 'no food word to rescue it',
  fallback: 'nothing matched',
};

export const layerLabel = (layer: string): string => LAYER_LABELS[layer] ?? `Layer ${layer}`;
export const reasonLabel = (reason?: string): string | null =>
  reason ? (REASONS[reason] ?? reason) : null;

/** The layer that actually decided: the FIRST one that decided, matching the backend. */
export function winningLayer(trace: CategoryTrace): TraceLayer | null {
  return trace.layers.find((l) => l.status === 'decided') ?? null;
}

/**
 * Layers that decided but lost — "the path would have said fish".
 *
 * This is the part that tells you where a fix belongs: if the winner looks wrong, one of
 * these is what you wanted; if the winner looks right, these show what it's protecting
 * against. Everything after the winner, so order is preserved.
 */
export function counterfactuals(trace: CategoryTrace): TraceLayer[] {
  const winner = winningLayer(trace);
  if (!winner) return [];
  return trace.layers.slice(trace.layers.indexOf(winner) + 1).filter((l) => l.status === 'decided');
}

/**
 * The human half of the verdict, e.g. `"trockennahrung"` or `"kerrygold" (brand field)`.
 *
 * Deliberately does NOT include the rule's address — `ruleAddress` renders that on its own
 * line, and printing it twice made the verdict harder to read, not more precise.
 */
export function verdictDetail(layer: TraceLayer): string {
  const reason = reasonLabel(layer.reason);
  if (!layer.matched) return reason ?? layerLabel(layer.layer);
  const where = layer.where === 'brand_field' ? ' (brand field)' : '';
  return `"${layer.matched}"${where}`;
}

/** The rule's editable address, e.g. `_FORM_OVERRIDES[10]` — null when there's no table. */
export function ruleAddress(layer: TraceLayer): string | null {
  if (!layer.table) return null;
  return layer.index === undefined ? layer.table : `${layer.table}[${layer.index}]`;
}
