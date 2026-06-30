/** Supported colour scheme identifiers. Re-exported for consumers that don't need the full context. */
export type ThemeId = 'light' | 'dark';

/**
 * Adds or removes the `dark` class on `<html>` so Tailwind's
 * `@custom-variant dark` selector activates the dark-mode token overrides.
 *
 * @param themeId - The scheme to apply.
 */
export function applyThemeClass(themeId: ThemeId): void {
  document.documentElement.classList.toggle('dark', themeId === 'dark');
}

/** The scheme applied on first load when no preference is stored. */
export const DEFAULT_THEME_ID: ThemeId = 'light';

/** `localStorage` key used to persist the user's theme choice across sessions. */
export const THEME_STORAGE_KEY = 'mono-poct:theme';
