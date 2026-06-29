import type { ExtractionState, FsmState } from '@/services';

interface ProgressPanelProps {
  extraction: ExtractionState | null;
  variableStatuses: Record<string, string>;
  currentFsm: FsmState | null;
}

interface VariableRow {
  label: string;
  statusKey: string;
  known: boolean;
  activeState: FsmState;
  /** Small supplementary label shown under the variable name when data came from DB lookup */
  dbHint?: string | null;
}

function Chip({ known, value }: { known: boolean; value: string | undefined }) {
  if (!known || value === undefined) {
    return (
      <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-400">
        PENDING
      </span>
    );
  }
  const color =
    value === 'FAIL'
      ? 'bg-red-900/60 text-red-300'
      : value === 'WARN'
        ? 'bg-amber-900/60 text-amber-300'
        : 'bg-emerald-900/60 text-emerald-300';
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{value}</span>
  );
}

export function ProgressPanel({ extraction, variableStatuses, currentFsm }: ProgressPanelProps) {
  const deviceSerial = extraction?.historical?.device_serial;
  const lotNumber = extraction?.consumable?.lot_number;

  const rows: VariableRow[] = [
    {
      label: 'Consumable',
      statusKey: 'consumable_status',
      known: extraction?.consumable_known ?? false,
      activeState: 'ASK_CONSUMABLE',
      dbHint: lotNumber ? `Lot: ${lotNumber}` : null,
    },
    {
      label: 'Storage',
      statusKey: 'storage_condition',
      known: extraction?.storage_known ?? false,
      activeState: 'ASK_STORAGE',
    },
    {
      label: 'Historical',
      statusKey: 'historical_error_flag',
      known: extraction?.historical_known ?? false,
      activeState: 'ASK_HISTORICAL',
      dbHint: deviceSerial ? `DB: ${deviceSerial}` : null,
    },
    {
      label: 'EQA',
      statusKey: 'eqa_status',
      known: extraction?.eqa_known ?? false,
      activeState: 'ASK_EQA',
    },
  ];

  return (
    <aside className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
        QC Variables
      </h2>
      <ul className="space-y-2">
        {rows.map(row => {
          const isActive = currentFsm === row.activeState;
          return (
            <li
              key={row.label}
              className={`flex items-center justify-between rounded-lg px-3 py-2 transition-colors ${
                isActive ? 'bg-slate-800 ring-1 ring-emerald-600/40' : ''
              }`}
            >
              <span className="flex flex-col">
                <span className={`text-sm ${isActive ? 'text-slate-100' : 'text-slate-400'}`}>
                  {row.label}
                  {isActive && <span className="ml-1.5 text-emerald-400">←</span>}
                </span>
                {row.dbHint && (
                  <span className="mt-0.5 text-[10px] text-sky-400/80">{row.dbHint}</span>
                )}
              </span>
              <Chip known={row.known} value={variableStatuses[row.statusKey]} />
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
