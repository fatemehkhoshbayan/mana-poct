/**
 * Horizontal strip of four QC variable pills shown above the chat panel.
 *
 * Each pill represents one data collection step (Consumable, Storage, Historical, EQA).
 * The pill matching the current backend FSM state is highlighted with the primary colour.
 * When backend DB lookups populate lot number or device serial, a small hint is shown
 * below the status chip.
 *
 * Data flows in via `ChatState` (no internal state); updates are driven by `state` SSE events.
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
    <div className="gap-sm flex">
      {rows.map(row => {
        const isActive = currentFsm === row.activeState;
        return (
          <div
            key={row.label}
            className={`gap-xs px-md py-sm flex flex-1 flex-col rounded-xl transition-all ${
              isActive ? 'bg-primary shadow-md' : 'bg-surface backdrop-blur-sm'
            }`}
          >
            <p className="text-body-sm text-on-surface flex items-center gap-2 align-middle font-semibold">
              {row.label}
              {isActive && <ArrowRight size={15} />}
            </p>
            <div className="gap-xs flex items-center justify-between">
              <Chip known={row.known} value={variableStatuses[row.statusKey]} />
              {row.dbHint && (
                <p className="text-label-sm text-inverse-surface truncate">{row.dbHint}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
