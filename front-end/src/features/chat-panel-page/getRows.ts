import type { ExtractionState, FsmState } from '@/services';

interface IGetRows {
  lotNumber?: string | null;
  extraction: ExtractionState | null;
  deviceSerial?: string | null;
}

/**
 * A single row in the QC variable progress strip.
 */
export interface VariableRow {
  /** Display label shown in the pill (e.g. `'Consumable'`). */
  label: string;
  /** Key used to look up the variable's verdict in `ChatState.variableStatuses`. */
  statusKey: string;
  /** Whether the backend has marked this variable as fully collected. */
  known: boolean;
  /** The FSM state at which this variable is the current focus; used to highlight the active pill. */
  activeState: FsmState;
  /** Small supplementary hint shown below the status chip when data came from a DB lookup. */
  dbHint?: string | null;
}

/**
 * Build the ordered list of QC variable rows for {@link ProgressPanel}.
 *
 * The order matches the backend FSM progression:
 * Consumable → Storage → Historical → EQA.
 *
 * @param extraction - Current extraction state (may be `null` before the first `state` SSE event).
 * @param lotNumber - Populated when the consumable lot was looked up; shown as `Lot: …` hint.
 * @param deviceSerial - Populated when the device serial was looked up; shown as `DB: …` hint.
 */
export function getRows({ extraction, lotNumber, deviceSerial }: IGetRows): VariableRow[] {
  return [
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
}
