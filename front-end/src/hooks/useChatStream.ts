import { useCallback, useRef } from 'react';

import { takeCompleteFrames, parseFrame, type StreamHandlers } from './helper';

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

      // flush any remaining buffer
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
