/**
 * Sticky application footer.
 *
 * Minimal copyright strip anchored to the bottom of the viewport.
 * Uses `bg-surface` so it inherits the correct token in both light and dark modes.
 */
import { Copyright } from 'lucide-react';

function Footer() {
  return (
    <footer className="py-lg px-2xl bg-surface sticky bottom-0 z-50 flex w-full items-center justify-between border-t border-white/20">
      <div className="gap-sm text-on-surface/60 flex items-center">
        <Copyright className="material-symbols-outlined" size={16} />
        <p className="text-label-md text-center">2026 Mana POCT</p>
      </div>
    </footer>
  );
}

export default Footer;
