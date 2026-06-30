import { useCallback, useRef } from 'react';
import { takeCompleteFrames, parseFrame, type StreamHandlers } from './helper';

/**
 * Low-level SSE streaming hook used by {@link ChatPanel}.
 *
 * Uses the native `fetch` API with a `ReadableStream` reader instead of `EventSource`
 * so the caller can send a `POST` body and custom headers (which `EventSource` does not support).
 *
 * **Abort behaviour:** calling `stream()` a second time automatically cancels any
 * in-flight request before starting the new one. `abort()` can also be called explicitly.
 *
 * @returns `{ stream, abort }`:
 *   - `stream(url, body, handlers)` — POST to `url`, consume the SSE response, dispatch to `handlers`.
 *   - `abort()` — cancel the current request.
 *
 * @example
 * ```ts
 * const { stream, abort } = useChatStream();
 * await stream('/api/sessions/123/messages', { message: 'hello' }, {
 *   onToken: t => console.log(t),
 *   onState: s => dispatch({ type: 'STREAM_STATE', event: s }),
 *   onDecision: d => dispatch({ type: 'STREAM_DECISION', decision: d }),
 *   onError: e => dispatch({ type: 'STREAM_ERROR', message: e.message }),
 *   onDone: () => dispatch({ type: 'STREAM_DONE' }),
 * });
 * ```
 */
export function useChatStream() {
  const abortRef = useRef<AbortController | null>(null);

  const stream = useCallback(async (url: string, body: unknown, handlers: StreamHandlers) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) {
        handlers.onError({ message: `HTTP ${res.status}: ${res.statusText}` });
        handlers.onDone();
        return;
      }

      const reader = res.body!.getReader();
      const dec = new TextDecoder();
      let buf = '';

      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const { frames, rest } = takeCompleteFrames(buf);
        buf = rest;
        for (const frame of frames) {
          if (frame.trim()) parseFrame(frame, handlers);
        }
      }

      // Flush any data that arrived without a terminal blank line.
      if (buf.trim()) {
        for (const frame of takeCompleteFrames(buf + '\n\n').frames) {
          if (frame.trim()) parseFrame(frame, handlers);
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        handlers.onError({ message: (err as Error).message ?? 'Stream error' });
        handlers.onDone();
      }
    }
  }, []);

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { stream, abort };
}
