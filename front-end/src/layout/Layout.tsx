/**
 * Top-level application shell.
 *
 * - Fills the full viewport (`h-screen overflow-hidden`) to prevent a page-level scrollbar.
 * - Applies the gradient background via the `.bg-app` CSS utility (switches between
 *   light and dark gradients based on the `dark` class on `<html>`).
 * - Reads the current theme from `useTheme` and passes `toggleTheme` down to `Header`.
 * - The `<main>` element constrains content to 1024 px and uses `flex-1 min-h-0` to
 *   participate correctly in the vertical flex chain.
 */
import { useTheme } from '@/hooks';
import Header from './Header';
import Footer from './Footer';

interface ILayoutProps {
  children: React.ReactNode;
}

export const Layout = ({ children }: ILayoutProps) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="bg-app flex h-screen flex-col overflow-hidden">
      <Header toggleTheme={toggleTheme} theme={theme} />
      <main className="p-md sm:p-lg gap-md sm:gap-lg mx-auto flex min-h-0 w-full max-w-[1024px] flex-1 flex-col">
        {children}
      </main>
      <Footer />
    </div>
  );
};

export default Layout;
