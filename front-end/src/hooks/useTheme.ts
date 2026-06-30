import { useContext } from 'react';
import { ThemeContext } from '@/context';

/**
 * Returns the current theme state and controls from the nearest {@link ThemeProvider}.
 *
 * @returns `{ theme, setTheme, toggleTheme }` — the active scheme and setters.
 * @throws If called outside of a `<ThemeProvider>` tree.
 *
 * @example
 * ```tsx
 * const { theme, toggleTheme } = useTheme();
 * // theme === 'light' | 'dark'
 * ```
 */
export function useTheme() {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }

  return context;
}
