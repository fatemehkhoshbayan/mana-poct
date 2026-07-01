/**
 * Horizontal strip of four QC variable pills shown above the chat panel.
 *
 * Each pill represents one data collection step (Consumable, Storage, Historical, EQA).
 * The pill matching the current backend FSM state is highlighted with the primary colour.
 * When backend DB lookups populate lot number or device serial, a small hint is shown
 * below the status chip.
 *
 * Data flows in via `ChatState` (no internal state); updates are driven by `state` SSE events.
 *
 * Always renders as a single row of 4 pills. On small screens, text shrinks to fit and
 * the DB lookup hint (e.g. lot number) drops below the status chip instead of sitting
 * inline next to it, since there isn't enough horizontal room for both.
 */
import type { ExtractionState, FsmState } from '@/services';
import { Chip } from '@/ui';
import { getRows } from './getRows';
import { ArrowRight } from 'lucide-react';

interface ProgressPanelProps {
  extraction: ExtractionState | null;
  variableStatuses: Record<string, string>;
  currentFsm: FsmState | null;
}

export function ProgressPanel({ extraction, variableStatuses, currentFsm }: ProgressPanelProps) {
  const deviceSerial = extraction?.historical?.device_serial;
  const lotNumber = extraction?.consumable?.lot_number;

  const rows = getRows({ extraction, lotNumber, deviceSerial });

  return (
    <section className="gap-base sm:gap-xs flex flex-row">
      {rows.map(row => {
        const isActive = currentFsm === row.activeState;
        return (
          <div
            key={row.label}
            className={`gap-base p-sm sm:px-md sm:py-sm flex flex-1 flex-col overflow-hidden rounded-lg transition-all sm:rounded-xl ${
              isActive ? 'bg-primary shadow-md' : 'bg-surface backdrop-blur-sm'
            }`}
          >
            <p className="text-label-sm sm:text-body-sm text-on-surface gap-base flex items-center truncate align-middle font-semibold">
              <span className="truncate">{row.label}</span>
              {isActive && <ArrowRight size={12} className="shrink-0" />}
            </p>
            <div className="gap-base flex flex-col items-start sm:flex-row sm:items-center sm:justify-between">
              <Chip known={row.known} value={variableStatuses[row.statusKey]} />
              {row.dbHint && (
                <p className="text-label-xs sm:text-label-sm text-inverse-surface">{row.dbHint}</p>
              )}
            </div>
          </div>
        );
      })}
    </section>
  );
}
