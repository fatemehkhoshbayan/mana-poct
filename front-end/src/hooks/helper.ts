import type { Decision, SseError, StateEvent } from '@/services';

export interface StreamHandlers {
  onToken: (text: string) => void;
  onState: (state: StateEvent) => void;
  onDecision: (decision: Decision) => void;
  onError: (err: SseError) => void;
  onDone: () => void;
}

export function parseFrame(frame: string, handlers: StreamHandlers): void {
  const lines = frame.split('\n');
  let eventType = 'message';
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
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

export function takeCompleteFrames(buf: string): { frames: string[]; rest: string } {
  const normalized = buf.replace(/\r\n/g, '\n');
  const parts = normalized.split('\n\n');
  const rest = parts.pop() ?? '';
  return { frames: parts, rest };
}
