// Mirrors backend app/schemas/domain.py and app/schemas/api.py (Section 4 contracts).
// Hand-mirrored — SSE event payloads are not in OpenAPI.

export type VarStatus = 'PASS' | 'FAIL';
export type EqaStatus = 'WARN' | 'STANDARD';
export type Scenario = 'A' | 'B' | 'C' | 'D' | 'E';
export type Color = 'RED' | 'YELLOW' | 'BLUE' | 'GREEN';

export type FsmState =
  | 'GREETING'
  | 'ASK_CONSUMABLE'
  | 'ASK_STORAGE'
  | 'ASK_HISTORICAL'
  | 'ASK_EQA'
  | 'RESOLVING'
  | 'RESOLVED';

export interface ConsumableInput {
  lot_number?: string | null;
  lot_expiry_date?: string | null;
  open_vial_date?: string | null;
  open_vial_age_days?: number | null;
}

export interface StorageInput {
  storage_type?: string | null;
  max_excursion_temp_c?: number | null;
  excursion_duration_hours?: number | null;
  freeze_indicator_tripped?: boolean | null;
}

export interface HistoricalInput {
  consecutive_qc_failures_30d?: number | null;
  device_serial?: string | null;
}

export interface EqaInput {
  eqa_deadline_date?: string | null;
  eqa_submission_status?: string | null;
  has_active_cycle?: boolean | null;
}

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

export interface Decision {
  session_id: string;
  tenant_id: string;
  device_serial?: string | null;
  lot_number?: string | null;
  variables: Record<string, string>;
  scenario: Scenario;
  scenario_name: string;
  color: Color;
  system_action: string;
  is_qc_locked: boolean;
  resolved_action: string;
  directives: string[];
  resolved_at: string;
}

// --- SSE event types (Section 4.2) ---
// token → raw text chunk (not JSON)
// state → ExtractionStateEvent (JSON)
// decision → Decision (JSON)
// error → { message: string } (JSON)
// done → "[DONE]" (not JSON)

export interface StateEvent extends ExtractionState {
  current_state: FsmState;
  current_objective: string;
}

export interface SseError {
  message: string;
}

export type SseEvent =
  | { type: 'token'; data: string }
  | { type: 'state'; data: StateEvent }
  | { type: 'decision'; data: Decision }
  | { type: 'error'; data: SseError }
  | { type: 'done' };

// --- HTTP response shapes ---

export interface CreateSessionResponse {
  session_id: string;
  state: FsmState;
  greeting: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}
