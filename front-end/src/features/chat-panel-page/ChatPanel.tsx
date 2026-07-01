/**
 * Main chat interaction panel.
 *
 * Responsibilities:
 * - Creates a backend session on mount via `createSession()`.
 * - Renders the scrollable message list (`MessageBubble`, `TypingIndicator`, `DecisionCard`).
 * - Pins the `Composer` at the bottom; re-focuses it automatically after each assistant turn.
 * - Streams responses via `useChatStream` and dispatches SSE events to the shared `chatReducer`.
 * - Renders the **New QC Check** button once a `decision` event locks the session.
 *
 * All state is external (passed as `state` + `dispatch`) — this component is purely presentational
 * with side-effects confined to the three `useEffect` hooks.
 */
import { useEffect, useRef, type Dispatch } from 'react';
import { useChatStream } from '@/hooks';
import { createSession } from '@/services';
import { Button, Composer, MessageBubble, TypingIndicator, type ComposerHandle } from '@/ui';
import type { ChatAction, ChatState } from '@/state';
import { DecisionCard } from './DecisionCard';

interface ChatPanelProps {
  state: ChatState;
  dispatch: Dispatch<ChatAction>;
}

export function ChatPanel({ state, dispatch }: ChatPanelProps) {
  const { stream } = useChatStream();
  const listRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<ComposerHandle>(null);
  const prevStreamingRef = useRef(false);

  // Refocus the input as soon as streaming ends so the user can type immediately.
  useEffect(() => {
    if (prevStreamingRef.current && !state.isStreaming) {
      composerRef.current?.focus();
    }
    prevStreamingRef.current = state.isStreaming;
  }, [state.isStreaming]);

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

  // Auto-scroll: set scrollTop directly on the list container instead of using
  // scrollIntoView, which traverses all ancestors and can trigger layout
  // recalculations in surrounding flex elements once the list becomes scrollable.
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [state.messages, state.streamingText]);

  const handleNewSession = async () => {
    try {
      const res = await createSession();
      dispatch({
        type: 'SESSION_CREATED',
        sessionId: res.session_id,
        fsm: res.state,
        greeting: res.greeting,
      });
    } catch (err) {
      dispatch({ type: 'STREAM_ERROR', message: String(err) });
    }
  };

  const handleSend = async (text: string) => {
    if (!state.sessionId || state.isStreaming || !!state.decision) return;

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
    <div className="flex min-h-0 w-full flex-1 flex-col">
      {/* Message list — flex-1 + overflow so it scrolls while Composer stays pinned */}
      <div
        ref={listRef}
        className="gap-xs sm:gap-lg pb-lg pr-sm scrollbar-hide flex min-h-0 flex-1 flex-col overflow-y-auto"
      >
        {state.messages.map(m => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}

        {/* Waiting for first token — show typing indicator */}
        {state.isStreaming && !state.streamingText && <TypingIndicator />}

        {/* Streaming bubble — shown once tokens start arriving */}
        {state.isStreaming && state.streamingText && (
          <MessageBubble role="assistant" content={state.streamingText} streaming />
        )}

        {/* Decision card inline in chat */}
        {state.decision && (
          <div className="mt-sm">
            <DecisionCard decision={state.decision} />
          </div>
        )}

        {state.error && (
          <p className="px-md py-sm text-body-sm rounded-lg bg-red-100 text-red-700">
            {state.error}
          </p>
        )}
      </div>

      <div className="shrink-0">
        <Composer
          ref={composerRef}
          onSend={handleSend}
          disabled={state.isStreaming || !state.sessionId || !!state.decision}
          resolved={!!state.decision}
        />
      </div>

      {state.decision && (
        <div className="shrink-0">
          <Button onClick={handleNewSession} fullWidth>
            New QC Check
          </Button>
        </div>
      )}
    </div>
  );
}
