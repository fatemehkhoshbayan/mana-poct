import type { Decision, SseError, StateEvent } from '@/services';

/**
 * Callbacks supplied to {@link useChatStream} to react to each SSE event type.
 *
 * - `onToken` — called once per streamed text chunk.
 * - `onState` — called when the backend emits a `state` event containing updated extraction fields.
 * - `onDecision` — called once when the QC decision is ready.
 * - `onError` — called on any SSE `error` event or network failure.
 * - `onDone` — called when the stream ends cleanly (`done` event or reader EOF).
 */
export interface StreamHandlers {
  onToken: (text: string) => void;
  onState: (state: StateEvent) => void;
  onDecision: (decision: Decision) => void;
  onError: (err: SseError) => void;
  onDone: () => void;
}

/**
 * Parse a single SSE frame (a block of lines delimited by a blank line) and
 * dispatch to the appropriate handler.
 *
 * Handles event types: `token`, `state`, `decision`, `error`, `done`.
 * Unknown event types with non-empty data are silently ignored.
 *
 * @param frame - One complete SSE frame (no surrounding blank lines needed).
 * @param handlers - Callback map from {@link StreamHandlers}.
 */
export function parseFrame(frame: string, handlers: StreamHandlers): void {
  const lines = frame.split('\n');
  let eventType = 'message';
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''));
    }
  }

  const raw = dataLines.join('\n');

  switch (eventType) {
    case 'done':
      handlers.onDone();
      return;
    case 'token':
      handlers.onToken(raw);
      return;
    case 'state':
      if (!raw) return;
      try {
        handlers.onState(JSON.parse(raw) as StateEvent);
      } catch {
        // ignore malformed
      }
      break;
    case 'decision':
      if (!raw) return;
      try {
        handlers.onDecision(JSON.parse(raw) as Decision);
      } catch {
        // ignore malformed
      }
      break;
    case 'error':
      if (!raw) return;
      try {
        handlers.onError(JSON.parse(raw) as SseError);
      } catch {
        handlers.onError({ message: raw });
      }
      break;
    default:
      if (!raw) return;
      break;
  }
}

/**
 * Split a raw byte buffer into complete SSE frames, returning any incomplete
 * trailing data as `rest` to be prepended to the next chunk.
 *
 * Frames are separated by `\n\n` (after normalising `\r\n` → `\n`).
 *
 * @param buf - Accumulated undecoded string from the stream reader.
 * @returns `{ frames, rest }` — complete frames ready to parse, and the leftover tail.
 */
export function takeCompleteFrames(buf: string): { frames: string[]; rest: string } {
  const normalized = buf.replace(/\r\n/g, '\n');
  const parts = normalized.split('\n\n');
  const rest = parts.pop() ?? '';
  return { frames: parts, rest };
}
