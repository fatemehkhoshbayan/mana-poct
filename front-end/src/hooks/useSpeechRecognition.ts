/**
 * Thin wrapper around the browser's native Web Speech API (`SpeechRecognition` /
 * `webkitSpeechRecognition`) for hands-free dictation. Entirely client-side —
 * no backend involvement, no audio ever leaves the browser's own speech service.
 *
 * - Feature-detects support; `isSupported` is `false` on browsers without it
 *   (e.g. desktop Firefox), so callers can hide the mic affordance gracefully.
 * - Runs in `continuous` + `interimResults` mode so `onResult` fires repeatedly
 *   with live partial transcripts (`isFinal: false`) as well as settled chunks
 *   (`isFinal: true`) — callers decide how to merge them into their own text state.
 * - `toggle()` is the primary control surface; `start()` / `stop()` are exposed
 *   for callers that need to force a particular state (e.g. stop on submit).
 *
 * @example
 * ```tsx
 * const { isSupported, isListening, toggle } = useSpeechRecognition({
 *   onResult: (transcript, isFinal) => {
 *     if (isFinal) appendFinal(transcript);
 *     else showInterim(transcript);
 *   },
 * });
 * ```
 */
import { useCallback, useEffect, useRef, useState } from 'react';

type SpeechRecognitionResultCallback = (transcript: string, isFinal: boolean) => void;

interface UseSpeechRecognitionOptions {
  onResult: SpeechRecognitionResultCallback;
  onError?: (error: string) => void;
  lang?: string;
}

interface UseSpeechRecognitionReturn {
  isSupported: boolean;
  isListening: boolean;
  start: () => void;
  stop: () => void;
  toggle: () => void;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognition) | undefined {
  if (typeof window === 'undefined') return undefined;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

export function useSpeechRecognition({
  onResult,
  onError,
  lang,
}: UseSpeechRecognitionOptions): UseSpeechRecognitionReturn {
  const [isSupported] = useState(() => !!getSpeechRecognitionCtor());
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Keep latest callbacks without re-creating the recognition instance on every render.
  const onResultRef = useRef(onResult);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onResultRef.current = onResult;
    onErrorRef.current = onError;
  }, [onResult, onError]);

  useEffect(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = lang ?? navigator.language ?? 'en-US';

    recognition.onresult = event => {
      let finalChunk = '';
      let interimChunk = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalChunk += result[0].transcript;
        } else {
          interimChunk += result[0].transcript;
        }
      }
      if (finalChunk) onResultRef.current(finalChunk, true);
      if (interimChunk) onResultRef.current(interimChunk, false);
    };

    recognition.onerror = event => {
      // "no-speech" / "aborted" fire routinely (e.g. brief silence) — not real errors.
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        onErrorRef.current?.(event.error);
      }
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;

    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [lang]);

  const start = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch {
      // Throws if already started — safe to ignore.
    }
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const toggle = useCallback(() => {
    if (isListening) stop();
    else start();
  }, [isListening, start, stop]);

  return { isSupported, isListening, start, stop, toggle };
}
