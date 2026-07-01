/**
 * A single chat message bubble with a frosted-glass avatar.
 *
 * - **User** messages: right-aligned, pink `bg-primary` bubble, `User` icon avatar.
 * - **Assistant** messages: left-aligned, white bubble (dark mode: `bg-surface-bright`),
 *   `Bot` icon avatar. Content is rendered as Markdown via `react-markdown`.
 * - When `streaming` is `true`, a blinking cursor is appended to indicate live output.
 * - The avatar is hidden on mobile screens (`< sm`) and only shown from the `sm` breakpoint up.
 *
 * @param role - `'user'` | `'assistant'`
 * @param content - Raw message text or Markdown string.
 * @param streaming - When `true`, shows an animated cursor at the end of the content.
 */
import { Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

function MessageBubble({ role, content, streaming }: MessageBubbleProps) {
  const isUser = role === 'user';
  return (
    <div
      className={`gap-md flex items-start ${isUser ? 'flex-row-reverse justify-start' : ''} max-w-[85%] ${isUser ? 'ml-auto' : ''}`}
    >
      {/* Avatar (hidden on mobile) */}
      <div className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/40 bg-white/30 sm:flex">
        {isUser ? (
          <User size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-white" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`text-body-sm p-md sm:text-body-md rounded-xl shadow-sm ${
          isUser
            ? 'bg-primary text-on-primary-fixed font-medium'
            : 'dark:bg-surface-bright dark:text-on-surface bg-white text-[#1A2535]'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-xs last:mb-0">{children}</p>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              ul: ({ children }) => <ul className="mb-xs pl-md list-disc">{children}</ul>,
              ol: ({ children }) => <ol className="mb-xs pl-md list-decimal">{children}</ol>,
              li: ({ children }) => <li className="mb-0.5">{children}</li>,
              code: ({ children }) => (
                <code className="px-base rounded bg-slate-100 py-0.5 font-mono text-xs dark:bg-slate-700">
                  {children}
                </code>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
        {streaming && (
          <p className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-current align-middle" />
        )}
      </div>
    </div>
  );
}

export default MessageBubble;
