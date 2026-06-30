import { createContext } from 'react';

/** Supported colour scheme identifiers. */
export type ThemeId = 'light' | 'dark';

/**
 * Value exposed by {@link ThemeContext}.
 *
 * - `theme` — the currently active scheme.
 * - `setTheme` — set an exact scheme.
 * - `toggleTheme` — flip between light and dark.
 */
export type ThemeContextValue = {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  toggleTheme: () => void;
};

/**
 * React context for the application colour scheme.
 * Consume via the {@link useTheme} hook rather than reading this directly.
 */
export const ThemeContext = createContext<ThemeContextValue | null>(null);
