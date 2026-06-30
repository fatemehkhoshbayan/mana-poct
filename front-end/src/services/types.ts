/**
 * TypeScript types mirroring the backend Pydantic schemas (`app/schemas/domain.py`
 * and `app/schemas/api.py`) and the SSE event contracts (Section 4.2).
 *
 * These are hand-maintained — the SSE event payloads are not in OpenAPI.
 */

/** Consumable (cartridge/reagent) quality control verdict. */
export type VarStatus = 'PASS' | 'FAIL';

/** EQA participation status. */
export type EqaStatus = 'WARN' | 'STANDARD';

/** QC decision scenario codes A–E, each mapping to a distinct clinical action. */
export type Scenario = 'A' | 'B' | 'C' | 'D' | 'E';

/** Traffic-light colour associated with a QC decision. Drives `DecisionCard` styling. */
export type Color = 'RED' | 'YELLOW' | 'BLUE' | 'GREEN';

/** Backend FSM states that the chat progresses through. Drives `ProgressPanel` highlighting. */
export type FsmState =
  | 'GREETING'
  | 'ASK_CONSUMABLE'
  | 'ASK_STORAGE'
  | 'ASK_HISTORICAL'
  | 'ASK_EQA'
  | 'RESOLVING'
  | 'RESOLVED';

/** Consumable (cartridge/strip) data extracted from the conversation. */
export interface ConsumableInput {
  lot_number?: string | null;
  lot_expiry_date?: string | null;
  open_vial_date?: string | null;
  open_vial_age_days?: number | null;
}

/** Cold-chain / storage condition data extracted from the conversation. */
export interface StorageInput {
  storage_type?: string | null;
  max_excursion_temp_c?: number | null;
  excursion_duration_hours?: number | null;
  freeze_indicator_tripped?: boolean | null;
}

/** Historical QC performance data, optionally populated from a mock DB lookup. */
export interface HistoricalInput {
  consecutive_qc_failures_30d?: number | null;
  /** Device serial used for DB lookups; shown as a hint in `ProgressPanel`. */
  device_serial?: string | null;
}

/** External Quality Assessment programme data extracted from the conversation. */
export interface EqaInput {
  eqa_deadline_date?: string | null;
  eqa_submission_status?: string | null;
  has_active_cycle?: boolean | null;
}

/**
 * Full extraction state as returned by `state` SSE events.
 * Each `*_known` flag indicates whether the corresponding domain data is complete.
 */
export interface ExtractionState {
  consumable: ConsumableInput;
  storage: StorageInput;
  historical: HistoricalInput;
  eqa: EqaInput;
  consumable_known: boolean;
  storage_known: boolean;
  historical_known: boolean;
  eqa_known: boolean;
}

/**
 * Final QC decision emitted by the backend `decision` SSE event.
 * Rendered by {@link DecisionCard}.
 */
export interface Decision {
  session_id: string;
  tenant_id: string;
  device_serial?: string | null;
  lot_number?: string | null;
  /** Per-variable verdicts, e.g. `{ consumable_status: 'PASS', storage_condition: 'FAIL' }`. */
  variables: Record<string, string>;
  scenario: Scenario;
  scenario_name: string;
  /** Traffic-light colour; controls `DecisionCard` border, background, and title colour. */
  color: Color;
  system_action: string;
  /** When `true` the device must not be used until the issue is resolved. */
  is_qc_locked: boolean;
  /** Human-readable summary of the recommended clinical action. */
  resolved_action: string;
  /** Ordered list of specific steps the operator must take. */
  directives: string[];
  resolved_at: string;
}

// ---------------------------------------------------------------------------
// SSE event types (Section 4.2)
// token    → raw text chunk           (not JSON)
// state    → ExtractionStateEvent     (JSON)
// decision → Decision                 (JSON)
// error    → { message: string }      (JSON)
// done     → "[DONE]"                 (not JSON)
// ---------------------------------------------------------------------------

/**
 * Payload of a `state` SSE event — extends {@link ExtractionState} with the
 * current FSM state and per-variable statuses used to update `ProgressPanel`.
 */
export interface StateEvent extends ExtractionState {
  current_state: FsmState;
  current_objective: string;
  /** Map of status-key → verdict string, e.g. `{ consumable_status: 'PASS' }`. */
  variable_statuses?: Record<string, string>;
}

/** Payload of an `error` SSE event. */
export interface SseError {
  message: string;
}

/** Discriminated union of all possible SSE event payloads. */
export type SseEvent =
  | { type: 'token'; data: string }
  | { type: 'state'; data: StateEvent }
  | { type: 'decision'; data: Decision }
  | { type: 'error'; data: SseError }
  | { type: 'done' };

// ---------------------------------------------------------------------------
// HTTP response shapes
// ---------------------------------------------------------------------------

/** Response from `POST /api/sessions`. */
export interface CreateSessionResponse {
  session_id: string;
  /** Initial FSM state — always `'GREETING'` on a fresh session. */
  state: FsmState;
  greeting: string;
}

/** A single message in the chat history as stored in {@link ChatState}. */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}
