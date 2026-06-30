/**
 * Three-dot animated placeholder shown while the assistant is composing a reply
 * but no tokens have arrived yet (`isStreaming && !streamingText`).
 *
 * Accessibility: `role="status"` + `aria-live="polite"` announces the pending state
 * to screen readers without interrupting the user. `aria-atomic="true"` ensures the
 * full label is read if the element updates.
 */
function TypingIndicator() {
  return (
    <div className="gap-md ml-12 flex items-start">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        aria-label="Assistant is typing"
        className="gap-xs px-sm py-xs flex items-center rounded-full border border-white/30 bg-white/20"
      >
        <p className="sr-only">Assistant is typing</p>
        <p
          aria-hidden="true"
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-white [animation-delay:-0.32s]"
        />
        <p
          aria-hidden="true"
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-white [animation-delay:-0.16s]"
        />
        <p aria-hidden="true" className="h-1.5 w-1.5 animate-bounce rounded-full bg-white" />
      </div>
    </div>
  );
}

export default TypingIndicator;
