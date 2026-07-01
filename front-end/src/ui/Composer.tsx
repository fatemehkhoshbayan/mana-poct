/**
 * Chat message input with a pinned send button and optional voice dictation.
 *
 * - `Enter` submits; `Shift+Enter` inserts a newline.
 * - Exposes a `focus()` imperative handle so `ChatPanel` can re-focus the textarea
 *   programmatically as soon as streaming ends.
 * - `disabled` blocks submission and dims the control while the assistant is responding;
 *   any in-progress dictation is stopped automatically when this flips to `true`.
 * - `resolved` switches the placeholder text when the session is locked after a decision.
 * - A microphone button (hidden on browsers without `SpeechRecognition` support, e.g.
 *   desktop Firefox) lets the user dictate instead of typing via `useSpeechRecognition`.
 *   Final transcript chunks are appended to the textarea; interim (in-progress) words are
 *   shown live and replaced once the browser settles on a final transcript.
 *
 * @example
 * ```tsx
 * const composerRef = useRef<ComposerHandle>(null);
 * composerRef.current?.focus(); // re-focus after streaming
 *
 * <Composer ref={composerRef} onSend={handleSend} disabled={isStreaming} />
 * ```
 */
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { Mic, SendHorizonal } from 'lucide-react';
import { useSpeechRecognition } from '@/hooks';
import { cn } from '@/lib';
import IconButton from './IconButton';

interface ComposerProps {
  onSend: (text: string) => void;
  disabled: boolean;
  resolved?: boolean;
}

export interface ComposerHandle {
  focus: () => void;
}

function appendTranscript(base: string, transcript: string): string {
  if (!transcript) return base;
  const needsSpace = base.length > 0 && !/[\s\n]$/.test(base);
  return `${base}${needsSpace ? ' ' : ''}${transcript}`;
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { onSend, disabled, resolved = false },
  ref,
) {
  const [text, setText] = useState('');
  const [speechError, setSpeechError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Snapshot of `text` at the moment dictation starts — interim results are
  // previewed on top of it, final results are permanently folded into it.
  const baseTextRef = useRef('');

  const {
    isSupported: isMicSupported,
    isListening,
    start,
    stop,
  } = useSpeechRecognition({
    onResult: (transcript, isFinal) => {
      setSpeechError(null);
      if (isFinal) {
        baseTextRef.current = appendTranscript(baseTextRef.current, transcript);
        setText(baseTextRef.current);
      } else {
        setText(appendTranscript(baseTextRef.current, transcript));
      }
    },
    onError: err => setSpeechError(err === 'not-allowed' ? 'Microphone access denied' : err),
  });

  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
  }));

  // Don't leave the mic listening once the composer is disabled (e.g. assistant streaming).
  useEffect(() => {
    if (disabled && isListening) stop();
  }, [disabled, isListening, stop]);

  const submit = () => {
    if (isListening) stop();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    baseTextRef.current = '';
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const toggleMic = () => {
    if (disabled) return;
    if (isListening) {
      stop();
    } else {
      baseTextRef.current = text;
      setSpeechError(null);
      start();
    }
  };

  return (
    <div className="pt-xs relative">
      <div className="relative">
        <textarea
          id="composer-textarea"
          name="composer-textarea"
          ref={textareaRef}
          value={text}
          onChange={e => {
            baseTextRef.current = e.target.value;
            setText(e.target.value);
          }}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={3}
          placeholder={
            resolved
              ? 'Session resolved — start a new check below'
              : disabled
                ? 'Waiting for assistant…'
                : isListening
                  ? 'Listening…'
                  : 'Type or tap the mic to talk…'
          }
          className={cn(
            'p-md text-body-md text-on-surface focus:ring-primary/50 w-full resize-none rounded-xl border-0 bg-white pr-24 placeholder-slate-400 shadow-xl transition outline-none focus:ring-4 disabled:opacity-50 dark:placeholder-slate-500',
            isListening && 'ring-primary/50 ring-4',
          )}
        />
        <div className="bottom-md right-sm gap-xs absolute flex flex-col items-center">
          {isMicSupported && (
            <IconButton
              variant="default"
              onClick={toggleMic}
              disabled={disabled}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
              aria-pressed={isListening}
              title={speechError ?? undefined}
              className={cn(
                'rounded-lg shadow-md',
                isListening ? 'animate-pulse bg-red-500 text-white hover:brightness-105' : '',
              )}
            >
              <Mic size={18} />
            </IconButton>
          )}
          <IconButton
            variant="default"
            onClick={submit}
            disabled={disabled || !text.trim()}
            aria-label="Send message"
            className="rounded-lg shadow-md disabled:cursor-not-allowed disabled:opacity-40"
          >
            <SendHorizonal size={18} />
          </IconButton>
        </div>
      </div>
      {speechError && (
        <p className="text-body-xs sm:text-body-sm mt-xs px-base text-red-600 dark:text-red-400">
          {speechError}
        </p>
      )}
    </div>
  );
});
