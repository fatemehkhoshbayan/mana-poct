import { useState } from 'react';

import { useChatStream } from '@/hooks';
import { Button } from '@/ui';

export const ChatBox = () => {
  const [tokens, setTokens] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [done, setDone] = useState(false);
  const { stream, abort } = useChatStream();

  const handleTest = async () => {
    setTokens([]);
    setDone(false);
    setStreaming(true);
    await stream(
      '/api/hello/stream',
      {},
      {
        onToken: t => setTokens(prev => [...prev, t]),
        onState: () => {},
        onDecision: () => {},
        onError: e => {
          setTokens(prev => [...prev, `[error: ${e.message}]`]);
          setStreaming(false);
          setDone(true);
        },
        onDone: () => {
          setStreaming(false);
          setDone(true);
        },
      },
    );
  };

  return (
    <section className="flex w-full flex-col gap-4">
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="min-h-20 font-mono text-lg text-emerald-400">
          {tokens.length === 0 && !streaming && (
            <span className="text-slate-600">Click the button to test the SSE pipeline…</span>
          )}
          {tokens.map((t, i) => (
            <span key={i}>
              {t}
              {i < tokens.length - 1 && '\n'}
            </span>
          ))}
          {streaming && (
            <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-emerald-400" />
          )}
        </div>

        {done && (
          <p className="text-xs text-slate-500">
            Stream complete — {tokens.length} token(s) received.
          </p>
        )}
      </div>

      <div className="flex w-full gap-3 px-6">
        <Button onClick={handleTest} disabled={streaming}>
          {streaming ? 'Streaming…' : 'Test hello-stream'}
        </Button>

        {streaming && (
          <button
            onClick={abort}
            className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            Abort
          </button>
        )}
      </div>
    </section>
  );
};

export default ChatBox;
