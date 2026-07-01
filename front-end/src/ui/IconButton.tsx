/**
 * Icon-only circular button.
 *
 * | Variant | Use case |
 * |---|---|
 * | `ghost` (default) | Transparent with white icon; hover adds a frosted overlay — used in `Header` |
 * | `default` | Filled primary colour with dark icon — used as the send button in `Composer` |
 *
 * Use `className` to override shape (e.g. `rounded-lg`) or positioning (`absolute bottom-md`).
 * Conflicts are resolved by `cn` / `twMerge`.
 *
 * Always renders `type="button"` to prevent accidental form submissions.
 *
 * @example
 * ```tsx
 * <IconButton onClick={toggleTheme} aria-label="Toggle theme">
 *   <Moon size={20} />
 * </IconButton>
 *
 * <IconButton variant="default" className="absolute bottom-md right-md rounded-lg">
 *   <SendHorizonal size={18} />
 * </IconButton>
 * ```
 */
import { cn } from '@/lib';
import type { ButtonHTMLAttributes } from 'react';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'ghost';
}

function IconButton({ className, variant = 'ghost', children, ...rest }: IconButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        'p-xs flex items-center justify-center rounded-full transition-all active:scale-95',
        variant === 'ghost' && 'text-white hover:bg-white/20',
        variant === 'default' && 'bg-primary text-on-primary-fixed shadow-sm hover:brightness-105',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

export default IconButton;
