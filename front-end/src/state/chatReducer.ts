import type { ChatMessage, Decision, ExtractionState, FsmState, StateEvent } from '@/services';

export interface ChatState {
  sessionId: string | null;
  fsm: FsmState | null;
  messages: ChatMessage[];
  streamingText: string;
  extraction: ExtractionState | null;
  variableStatuses: Record<string, string>;
  decision: Decision | null;
  isStreaming: boolean;
  error: string | null;
}

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

export type ChatAction =
  | { type: 'SESSION_CREATED'; sessionId: string; fsm: FsmState; greeting: string }
  | { type: 'USER_MESSAGE'; text: string }
  | { type: 'STREAM_START' }
  | { type: 'STREAM_TOKEN'; text: string }
  | { type: 'STREAM_STATE'; event: StateEvent }
  | { type: 'STREAM_DECISION'; decision: Decision }
  | { type: 'STREAM_ERROR'; message: string }
  | { type: 'STREAM_DONE' };

let _msgId = 0;
const nextId = () => `msg-${++_msgId}`;

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
