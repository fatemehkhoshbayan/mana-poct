import { type ClassValue, clsx } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

/**
 * Extended `tailwind-merge` instance that knows about the project's custom
 * Tailwind v4 design tokens (colors, typography) defined in `index.css`.
 *
 * Without this extension, `twMerge` would not recognise tokens like
 * `text-body-sm` or `bg-primary` as Tailwind utilities and would fail to
 * de-duplicate conflicting class names correctly.
 */
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      color: [
        'primary',
        'secondary',
        'background',
        'surface',
        'surface-bright',
        'surface-dim',
        'surface-variant',
        'surface-tint',
        'surface-container',
        'surface-container-low',
        'surface-container-high',
        'surface-container-lowest',
        'on-primary-fixed',
        'on-primary-fixed-variant',
        'on-secondary',
        'on-secondary-fixed',
        'on-secondary-container',
        'on-tertiary',
        'on-tertiary-fixed',
        'on-tertiary-fixed-variant',
        'on-tertiary-container',
        'on-surface',
        'on-surface-variant',
        'on-background',
        'primary-fixed',
        'primary-fixed-dim',
        'secondary-fixed',
        'secondary-fixed-dim',
        'tertiary',
        'tertiary-fixed',
        'tertiary-fixed-dim',
        'tertiary-container',
        'error',
        'error-container',
        'outline',
        'inverse-surface',
        'inverse-on-surface',
        'inverse-primary',
      ],
      text: [
        'body-sm',
        'body-md',
        'body-lg',
        'label-sm',
        'label-md',
        'headline-sm',
        'headline-md',
        'headline-lg',
        'display',
      ],
    },
  },
});

/**
 * Merge Tailwind class names safely.
 *
 * Combines `clsx` (conditional class composition) with an extended
 * `tailwind-merge` instance that resolves conflicts between both standard
 * Tailwind utilities and the project's custom design tokens.
 *
 * @param inputs - Any mix of strings, arrays, or conditional objects accepted by `clsx`.
 * @returns A single deduplicated class string with conflicts resolved.
 *
 * @example
 * ```ts
 * cn('px-md py-sm', isActive && 'bg-primary', className)
 * cn('text-body-sm', 'text-headline-sm') // → 'text-headline-sm' (conflict resolved)
 * ```
 */
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
