/**
 * Sticky application header.
 *
 * Contains the app name / subtitle on the left and a theme-toggle `IconButton`
 * on the right. Sits above the gradient background using `bg-surface` so the
 * header colour responds correctly in both light and dark modes.
 */
import { Sun, Moon } from 'lucide-react';
import { type ThemeId } from '@/context';
import { IconButton } from '@/ui';

interface IHeaderProps {
  toggleTheme: () => void;
  theme: ThemeId;
}

function Header({ toggleTheme, theme }: IHeaderProps) {
  return (
    <header className="px-2xl py-md bg-surface sticky top-0 z-50 flex w-full items-center justify-between border-b border-white/20">
      <div className="gap-sm flex items-baseline">
        <span className="text-on-surface text-headline-lg font-bold">Mana POCT</span>
        <span className="font-label-md text-label-md text-on-surface/60">QC Assistant</span>
      </div>
      <div className="gap-md flex items-center">
        <IconButton
          id="theme-toggle"
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="text-on-surface hover:bg-surface-bright"
        >
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </IconButton>
      </div>
    </header>
  );
}

export default Header;
