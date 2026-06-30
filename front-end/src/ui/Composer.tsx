/**
 * Chat message input with a pinned send button.
 *
 * - `Enter` submits; `Shift+Enter` inserts a newline.
 * - Exposes a `focus()` imperative handle so `ChatPanel` can re-focus the textarea
 *   programmatically as soon as streaming ends.
 * - `disabled` blocks submission and dims the control while the assistant is responding.
 * - `resolved` switches the placeholder text when the session is locked after a decision.
 *
 * @example
 * ```tsx
 * const composerRef = useRef<ComposerHandle>(null);
 * composerRef.current?.focus(); // re-focus after streaming
 *
 * <Composer ref={composerRef} onSend={handleSend} disabled={isStreaming} />
 * ```
 */
import { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import { SendHorizonal } from 'lucide-react';
import IconButton from './IconButton';

interface ComposerProps {
  onSend: (text: string) => void;
  disabled: boolean;
  resolved?: boolean;
}

export interface ComposerHandle {
  focus: () => void;
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { onSend, disabled, resolved = false },
  ref,
) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
  }));

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="relative pt-2">
      <div className="relative">
        <textarea
          id="composer-textarea"
          name="composer-textarea"
          ref={textareaRef}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={2}
          placeholder={
            resolved
              ? 'Session resolved — start a new check below'
              : disabled
                ? 'Waiting for assistant…'
                : 'Type your answer…'
          }
          className="p-md text-body-md text-on-surface focus:ring-primary/50 w-full resize-none rounded-xl border-0 bg-white placeholder-slate-400 shadow-xl transition outline-none focus:ring-4 disabled:opacity-50 dark:placeholder-slate-500"
        />
        <IconButton
          variant="default"
          onClick={submit}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
          className="bottom-md right-md absolute rounded-lg shadow-md disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SendHorizonal size={18} />
        </IconButton>
      </div>
    </div>
  );
});
