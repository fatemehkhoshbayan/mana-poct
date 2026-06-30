/**
 * Tailwind class bundles for each QC decision colour (`RED`, `YELLOW`, `BLUE`, `GREEN`).
 * Used by {@link DecisionCard} to apply colour-matched styling throughout the card.
 */
export interface ColorStyle {
  border: string;
  bg: string;
  title: string;
  dot: string;
  lockedBadge: string;
  messageBorder: string;
}

/**
 * Maps each `Decision.color` value to its full set of Tailwind class bundles.
 * Falls back to `GREEN` for any unrecognised colour value.
 */
export const COLOR_STYLES: Record<string, ColorStyle> = {
  RED: {
    border: 'border-red-400',
    bg: 'bg-red-50/70',
    title: 'text-red-600',
    dot: 'bg-red-500',
    lockedBadge: 'bg-red-600 text-white',
    messageBorder: 'border-red-100',
  },
  YELLOW: {
    border: 'border-amber-400',
    bg: 'bg-amber-50/70',
    title: 'text-amber-600',
    dot: 'bg-amber-500',
    lockedBadge: 'bg-amber-600 text-white',
    messageBorder: 'border-amber-100',
  },
  BLUE: {
    border: 'border-blue-400',
    bg: 'bg-blue-50/70',
    title: 'text-blue-600',
    dot: 'bg-blue-500',
    lockedBadge: 'bg-blue-600 text-white',
    messageBorder: 'border-blue-100',
  },
  GREEN: {
    border: 'border-emerald-400',
    bg: 'bg-emerald-50/70',
    title: 'text-emerald-600',
    dot: 'bg-emerald-500',
    lockedBadge: 'bg-emerald-600 text-white',
    messageBorder: 'border-emerald-100',
  },
};

/**
 * Per-verdict Tailwind classes for individual variable cells inside `DecisionCard`.
 * Independent of the decision colour — FAIL is always red, WARN amber, PASS green.
 */
export const VAR_STATUS_STYLES: Record<string, { text: string; chip: string }> = {
  FAIL: {
    text: 'text-red-600',
    chip: 'bg-red-100 text-red-600 border border-red-200',
  },
  WARN: {
    text: 'text-amber-600',
    chip: 'bg-amber-100 text-amber-700 border border-amber-200',
  },
  PASS: {
    text: 'text-emerald-600',
    chip: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  },
};
