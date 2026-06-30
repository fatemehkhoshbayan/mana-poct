/**
 * General-purpose button primitive built with `class-variance-authority`.
 *
 * | Variant | Use case |
 * |---|---|
 * | `primary` (default) | Primary CTAs — pink filled, e.g. **New QC Check** |
 * | `outline` | Secondary / destructive actions — frosted glass border, e.g. **Abort** |
 * | `link` | Inline text toggles — underline only, no padding, e.g. **Show raw payload** |
 *
 * Accepts all native `<button>` attributes. Pass `className` to override individual utilities
 * — conflicts are resolved by the extended `twMerge` instance in `cn.ts`.
 *
 * @example
 * ```tsx
 * <Button onClick={handleSend} fullWidth>Send</Button>
 * <Button variant="outline" onClick={abort}>Abort</Button>
 * <Button variant="link" size="sm" onClick={toggle}>Show details</Button>
 * ```
 */
import { cva, type VariantProps } from 'class-variance-authority';
import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib';

const buttonVariants = cva(
  'inline-flex items-center justify-center font-semibold transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'rounded-xl bg-primary text-on-primary-fixed shadow-sm hover:brightness-105',
        outline:
          'rounded-lg border border-white/30 bg-white/10 text-white backdrop-blur-sm hover:bg-white/20',
        link: 'text-on-surface-variant underline hover:text-on-surface',
      },
      size: {
        sm: 'px-sm py-xs text-label-md',
        md: 'px-md py-sm text-body-sm',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    compoundVariants: [
      { variant: 'link', size: 'sm', className: 'px-0 py-0 text-label-sm' },
      { variant: 'link', size: 'md', className: 'px-0 py-0 text-body-sm' },
    ],
    defaultVariants: {
      variant: 'primary',
      size: 'md',
      fullWidth: false,
    },
  },
);

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export default function Button({ variant, size, fullWidth, className, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(buttonVariants({ variant, size, fullWidth }), className)}
      {...rest}
    />
  );
}
