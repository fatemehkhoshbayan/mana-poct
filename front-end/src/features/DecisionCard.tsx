import { useState } from 'react';
import type { Decision } from '@/services';

interface DecisionCardProps {
  decision: Decision;
}

const COLOR_STYLES: Record<string, { border: string; badge: string; text: string }> = {
  RED: {
    border: 'border-red-500/60',
    badge: 'bg-red-500/20 text-red-300',
    text: 'text-red-300',
  },
  YELLOW: {
    border: 'border-amber-400/60',
    badge: 'bg-amber-400/20 text-amber-300',
    text: 'text-amber-300',
  },
  BLUE: {
    border: 'border-blue-400/60',
    badge: 'bg-blue-400/20 text-blue-300',
    text: 'text-blue-300',
  },
  GREEN: {
    border: 'border-emerald-500/60',
    badge: 'bg-emerald-500/20 text-emerald-300',
    text: 'text-emerald-300',
  },
};

const COLOR_EMOJI: Record<string, string> = {
  RED: '🔴',
  YELLOW: '🟡',
  BLUE: '🔵',
  GREEN: '🟢',
};

export function DecisionCard({ decision }: DecisionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const styles = COLOR_STYLES[decision.color] ?? COLOR_STYLES.GREEN;

  return (
    <div className={`rounded-xl border-2 bg-slate-900 p-5 ${styles.border}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg">{COLOR_EMOJI[decision.color]}</span>
            <span className={`text-lg font-bold ${styles.text}`}>{decision.scenario_name}</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Scenario {decision.scenario} · {decision.system_action.replace(/_/g, ' ')}
          </p>
        </div>
        {decision.is_qc_locked && (
          <span className="shrink-0 rounded-full bg-red-900/60 px-2.5 py-1 text-xs font-semibold text-red-300">
            QC LOCKED
          </span>
        )}
      </div>

      {/* Resolved action */}
      <p className="mt-3 text-sm leading-relaxed text-slate-300">{decision.resolved_action}</p>

      {/* Directives */}
      {decision.directives.length > 0 && (
        <ul className="mt-3 space-y-1">
          {decision.directives.map(d => (
            <li key={d} className="flex items-center gap-2 text-xs text-slate-400">
              <span className={`h-1.5 w-1.5 rounded-full ${styles.badge}`} />
              {d.replace(/_/g, ' ')}
            </li>
          ))}
        </ul>
      )}

      {/* Variables summary */}
      <div className="mt-4 grid grid-cols-2 gap-2">
        {Object.entries(decision.variables).map(([k, v]) => (
          <div key={k} className="rounded-lg bg-slate-800 px-3 py-1.5">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">
              {k.replace(/_/g, ' ')}
            </p>
            <p
              className={`text-xs font-semibold ${
                v === 'FAIL' ? 'text-red-400' : v === 'WARN' ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {v}
            </p>
          </div>
        ))}
      </div>

      {/* Collapsible raw JSON */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="mt-3 text-xs text-slate-500 underline hover:text-slate-400"
      >
        {expanded ? 'Hide raw payload' : 'Show raw payload'}
      </button>
      {expanded && (
        <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-[10px] text-slate-400">
          {JSON.stringify(decision, null, 2)}
        </pre>
      )}
    </div>
  );
}
