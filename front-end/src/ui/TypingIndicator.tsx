/**
 * TypingIndicator — three animated dots shown while the assistant is composing
 * a reply but no tokens have arrived yet.
 *
 * Accessibility:
 *   - role="status" + aria-live="polite" announces the pending state to screen readers
 *     without interrupting the user.
 *   - aria-label gives a plain-text description instead of exposing the dot glyphs.
 *   - aria-atomic="true" ensures the full label is read if the element updates.
 */
export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        aria-label="Assistant is typing"
        className="flex items-center gap-1.5 rounded-2xl bg-slate-800 px-4 py-3"
      >
        <span className="sr-only">Assistant is typing</span>
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.32s]"
        />
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.16s]"
        />
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full bg-slate-400 animate-bounce"
        />
      </div>
    </div>
  );
}
