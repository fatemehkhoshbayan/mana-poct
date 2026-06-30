/**
 * Renders the final QC decision inline in the chat after a `decision` SSE event.
 *
 * Visual structure (top to bottom):
 * 1. Colour-coded header — scenario name + optional **QC LOCKED** badge.
 * 2. Resolved action — plain-text clinical instruction.
 * 3. Variable grid — cards showing each variable's verdict (PASS/WARN/FAIL); single
 *    column on small screens, 2 columns from the `sm` breakpoint up.
 * 4. Required actions — bulleted directive list.
 * 5. Collapsible raw JSON payload for debugging.
 *
 * All colours (border, background, title, dots, locked badge) are driven by
 * `decision.color` via the `COLOR_STYLES` map in `constants.ts`.
 * Variable chip colours are always fixed (red/amber/green) regardless of decision colour.
 *
 * The card uses hard-coded slate text colours (not design tokens) so it remains readable
 * against its always-light tinted background in both light and dark app modes.
 */
import { useState } from 'react';
import { Lock } from 'lucide-react';
import type { Decision } from '@/services';
import { Button } from '@/ui';
import { cn } from '@/lib';
import { COLOR_STYLES, VAR_STATUS_STYLES } from './constants';

interface DecisionCardProps {
  decision: Decision;
}

export function DecisionCard({ decision }: DecisionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const styles = COLOR_STYLES[decision.color] ?? COLOR_STYLES.GREEN;

  return (
    <article className={cn('p-lg rounded-2xl border-2', styles.border, styles.bg)}>
      {/* Header */}
      <div className="gap-md flex items-start justify-between">
        <div className="gap-sm flex items-center">
          <p className={cn('mt-0.5 h-3 w-3 shrink-0 rounded-full', styles.dot)} />
          <h3 className={cn('text-headline-sm font-bold tracking-wide uppercase', styles.title)}>
            {decision.scenario_name}
          </h3>
        </div>
        {decision.is_qc_locked && (
          <p
            className={cn(
              'gap-xs px-sm py-xs text-label-md flex shrink-0 items-center rounded-full font-bold',
              styles.lockedBadge,
            )}
          >
            <Lock size={12} />
            QC LOCKED
          </p>
        )}
      </div>

      {/* Resolved action */}
      <div className={cn('mt-md px-md py-sm rounded-lg border bg-white/70', styles.messageBorder)}>
        <p className="text-body-md leading-relaxed text-slate-700">{decision.resolved_action}</p>
      </div>

      {/* Variables grid */}
      {Object.keys(decision.variables).length > 0 && (
        <div className="mt-md gap-sm grid grid-cols-1 sm:grid-cols-2">
          {Object.entries(decision.variables).map(([k, v]) => {
            const varStyle = VAR_STATUS_STYLES[v] ?? VAR_STATUS_STYLES.PASS;
            return (
              <div key={k} className="px-md py-sm rounded-lg border border-gray-200 bg-white/70">
                <p className="text-label-md tracking-wider text-slate-500 uppercase">
                  {k.replace(/_/g, ' ')}
                </p>
                <div className="mt-xs gap-xs flex items-center justify-between">
                  <p className={cn('text-headline-sm font-bold', varStyle.text)}>{v}</p>
                  <p className={cn('px-xs rounded py-1 text-[10px] font-bold', varStyle.chip)}>
                    {v}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Directives */}
      {decision.directives.length > 0 && (
        <div className="mt-md">
          <p className="text-label-md font-bold tracking-wider text-slate-800 uppercase">
            Required Actions:
          </p>
          <ul className="mt-sm space-y-xs">
            {decision.directives.map(d => (
              <li key={d} className="gap-sm text-body-sm flex items-start text-slate-700">
                <p className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', styles.dot)} />
                {d.replace(/_/g, ' ')}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Collapsible raw JSON */}
      <div className="mt-md">
        <Button
          variant="link"
          size="sm"
          onClick={() => setExpanded(e => !e)}
          className="text-slate-500 hover:text-slate-800"
        >
          {expanded ? 'Hide raw payload' : 'Show raw payload'}
        </Button>
        {expanded && (
          <pre className="mt-sm p-md max-h-48 overflow-auto rounded-lg bg-white/60 text-[10px] text-slate-600">
            {JSON.stringify(decision, null, 2)}
          </pre>
        )}
      </div>
    </article>
  );
}
