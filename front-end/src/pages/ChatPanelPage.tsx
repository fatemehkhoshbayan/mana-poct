/**
 * The sole page of the application.
 *
 * Owns the top-level `chatReducer` state and wires it to the two main sections:
 * - `ProgressPanel` — horizontal QC variable strip at the top.
 * - `ChatPanel` — frosted-glass scrollable chat area filling the remaining height.
 *
 * The `section` uses `flex-col min-h-0 flex-1` so it participates in the
 * `Layout` flex chain without causing a page-level overflow.
 */
import { useReducer } from 'react';
import { chatReducer, initialState } from '@/state/chatReducer';
import { ProgressPanel, ChatPanel } from '@/features';

export default function ChatPanelPage() {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  return (
    <section className="gap-md sm:gap-lg flex min-h-0 w-full flex-1 flex-col">
      {/* QC Variables — horizontal progress strip; shrink-0 prevents the flex
          algorithm from squishing it as the message list below grows */}
      <div className="shrink-0">
        <ProgressPanel
          extraction={state.extraction}
          variableStatuses={state.variableStatuses}
          currentFsm={state.fsm}
        />
      </div>

      {/* Chat panel — frosted glass */}
      <div className="p-sm sm:p-lg flex min-h-0 flex-1 flex-col rounded-2xl bg-white/10 backdrop-blur-md">
        <ChatPanel state={state} dispatch={dispatch} />
      </div>
    </section>
  );
}
