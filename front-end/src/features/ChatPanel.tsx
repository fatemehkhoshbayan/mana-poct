import { useEffect, useReducer, useRef } from 'react';
import { useChatStream } from '@/hooks';
import { createSession } from '@/services';
import { Composer, MessageBubble } from '@/ui';
import { chatReducer, initialState } from '@/state/chatReducer';
import { DecisionCard } from './DecisionCard';
import { ProgressPanel } from './ProgressPanel';

export function ChatPanel() {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const { stream } = useChatStream();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Create session on mount
  useEffect(() => {
    createSession()
      .then(res =>
        dispatch({
          type: 'SESSION_CREATED',
          sessionId: res.session_id,
          fsm: res.state,
          greeting: res.greeting,
        }),
      )
      .catch(err => dispatch({ type: 'STREAM_ERROR', message: String(err) }));
  }, []);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.streamingText]);

  const handleSend = async (text: string) => {
    if (!state.sessionId || state.isStreaming) return;

    dispatch({ type: 'USER_MESSAGE', text });
    dispatch({ type: 'STREAM_START' });

    await stream(
      `/api/sessions/${state.sessionId}/messages`,
      { message: text },
      {
        onToken: t => dispatch({ type: 'STREAM_TOKEN', text: t }),
        onState: e => dispatch({ type: 'STREAM_STATE', event: e }),
        onDecision: d => dispatch({ type: 'STREAM_DECISION', decision: d }),
        onError: e => dispatch({ type: 'STREAM_ERROR', message: e.message }),
        onDone: () => dispatch({ type: 'STREAM_DONE' }),
      },
    );
  };

  return (
    <div className="flex w-full max-w-5xl gap-4" style={{ height: 'calc(100vh - 9rem)' }}>
      {/* Chat column */}
      <div className="flex min-h-0 flex-1 flex-col rounded-xl border border-slate-800 bg-slate-900">
        {/* Message list — flex-1 + overflow so it scrolls while Composer stays pinned */}
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
          {state.messages.map(m => (
            <MessageBubble key={m.id} role={m.role} content={m.content} />
          ))}

          {/* Streaming bubble */}
          {state.isStreaming && state.streamingText && (
            <MessageBubble role="assistant" content={state.streamingText} streaming />
          )}

          {/* Decision card inline in chat */}
          {state.decision && (
            <div className="mt-2">
              <DecisionCard decision={state.decision} />
            </div>
          )}

          {state.error && (
            <p className="rounded-lg bg-red-900/30 px-3 py-2 text-xs text-red-400">{state.error}</p>
          )}

          <div ref={bottomRef} />
        </div>

        <Composer onSend={handleSend} disabled={state.isStreaming || !state.sessionId} />
      </div>

      {/* Sidebar */}
      <div className="w-56 shrink-0 overflow-y-auto">
        <ProgressPanel
          extraction={state.extraction}
          variableStatuses={state.variableStatuses}
          currentFsm={state.fsm}
        />
      </div>
    </div>
  );
}
