import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { DEFAULT_THEME_ID, THEME_STORAGE_KEY, applyThemeClass, type ThemeId } from './helper';
import { ThemeContext } from './ThemeContext';

/**
 * Read the persisted theme from `localStorage`.
 * Falls back to {@link DEFAULT_THEME_ID} when nothing is stored or the value is unrecognised.
 */
function readStoredTheme(): ThemeId {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === 'dark' ? 'dark' : DEFAULT_THEME_ID;
}

/**
 * Provides light/dark theme state to the component tree.
 *
 * - On mount it reads the last-used scheme from `localStorage`.
 * - On every change it persists the new value and applies the `dark` class to `<html>`,
 *   which activates the Tailwind v4 dark-mode token overrides defined in `index.css`.
 *
 * Wrap the application root with this provider (already done in `main.tsx`):
 * ```tsx
 * <ThemeProvider>
 *   <App />
 * </ThemeProvider>
 * ```
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>(() => readStoredTheme());

  useEffect(() => {
    applyThemeClass(theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const setTheme = useCallback((next: ThemeId) => {
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState(current => (current === 'dark' ? 'light' : 'dark'));
  }, []);

  const value = useMemo(() => ({ theme, setTheme, toggleTheme }), [theme, setTheme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
