import type { ChatMessage, Decision, ExtractionState, FsmState, StateEvent } from '@/services';

/**
 * The complete state of a single QC chat session.
 *
 * All fields are reset when a `SESSION_CREATED` action is dispatched
 * (i.e. on mount and when the user clicks **New QC Check**).
 */
export interface ChatState {
  /** Backend session identifier; `null` until the first `SESSION_CREATED` action. */
  sessionId: string | null;
  /** Current backend FSM state; drives which ProgressPanel pill is highlighted. */
  fsm: FsmState | null;
  /** Committed messages shown in the chat list. Streaming text lives in `streamingText`. */
  messages: ChatMessage[];
  /** Accumulates streamed tokens before they are committed as an assistant message. */
  streamingText: string;
  /** Structured extraction data populated by `state` SSE events. */
  extraction: ExtractionState | null;
  /** `Record<statusKey, value>` e.g. `{ consumable_status: 'PASS' }`. Populated by SSE. */
  variableStatuses: Record<string, string>;
  /** Set once a `decision` SSE event arrives; locks the composer. */
  decision: Decision | null;
  /** `true` while the SSE stream is open. */
  isStreaming: boolean;
  /** Last error message from an SSE `error` event or network failure. */
  error: string | null;
}

/** Initial blank state used on first mount and after each session reset. */
export const initialState: ChatState = {
  sessionId: null,
  fsm: null,
  messages: [],
  streamingText: '',
  extraction: null,
  variableStatuses: {},
  decision: null,
  isStreaming: false,
  error: null,
};

/**
 * All actions that can be dispatched to {@link chatReducer}.
 *
 * | Action | Trigger |
 * |---|---|
 * | `SESSION_CREATED` | Session API response on mount or New QC Check |
 * | `USER_MESSAGE` | User submits the Composer |
 * | `STREAM_START` | Just before the fetch is sent |
 * | `STREAM_TOKEN` | Each `token` SSE chunk |
 * | `STREAM_STATE` | Each `state` SSE event |
 * | `STREAM_DECISION` | The final `decision` SSE event |
 * | `STREAM_ERROR` | Any SSE or network error |
 * | `STREAM_DONE` | Stream ended cleanly; commits `streamingText` |
 */
export type ChatAction =
  | { type: 'SESSION_CREATED'; sessionId: string; fsm: FsmState; greeting: string }
  | { type: 'USER_MESSAGE'; text: string }
  | { type: 'STREAM_START' }
  | { type: 'STREAM_TOKEN'; text: string }
  | { type: 'STREAM_STATE'; event: StateEvent }
  | { type: 'STREAM_DECISION'; decision: Decision }
  | { type: 'STREAM_ERROR'; message: string }
  | { type: 'STREAM_DONE' };

/** Monotonically increasing message ID counter. Module-scoped to survive re-renders. */
let _msgId = 0;
const nextId = () => `msg-${++_msgId}`;

/**
 * Pure reducer for all QC chat state transitions.
 *
 * Notable invariants:
 * - `SESSION_CREATED` performs a full state reset via `initialState` spread, so
 *   stale extraction data and decisions are never carried across sessions.
 * - `STREAM_DONE` promotes `streamingText` to a committed assistant message only
 *   if the buffer is non-empty, preventing blank bubbles on empty responses.
 * - `streamingText` is never surfaced as a `ChatMessage`; components render it
 *   separately so the cursor animation is isolated.
 */
export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SESSION_CREATED':
      return {
        ...initialState,
        sessionId: action.sessionId,
        fsm: action.fsm,
        variableStatuses: {},
        messages: [
          {
            id: nextId(),
            role: 'assistant',
            content: action.greeting,
          },
        ],
      };

    case 'USER_MESSAGE':
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: nextId(), role: 'user', content: action.text },
        ],
        error: null,
      };

    case 'STREAM_START':
      return { ...state, isStreaming: true, streamingText: '', error: null };

    case 'STREAM_TOKEN':
      return { ...state, streamingText: state.streamingText + action.text };

    case 'STREAM_STATE':
      return {
        ...state,
        extraction: action.event,
        variableStatuses: action.event.variable_statuses ?? state.variableStatuses,
        fsm: action.event.current_state,
      };

    case 'STREAM_DECISION':
      return {
        ...state,
        decision: action.decision,
        fsm: 'RESOLVED',
      };

    case 'STREAM_ERROR':
      return { ...state, error: action.message };

    case 'STREAM_DONE': {
      const assistantMsg = state.streamingText.trim()
        ? [{ id: nextId(), role: 'assistant' as const, content: state.streamingText }]
        : [];
      return {
        ...state,
        isStreaming: false,
        streamingText: '',
        messages: [...state.messages, ...assistantMsg],
      };
    }

    default:
      return state;
  }
}
