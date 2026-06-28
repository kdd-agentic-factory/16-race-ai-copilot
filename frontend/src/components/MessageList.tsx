import { useEffect, useRef } from 'react'
import { useChatStore } from '../stores/useChatStore'
import MessageBubble from './MessageBubble'

export default function MessageList() {
  const messages = useChatStore((s) => s.messages)
  const isLoading = useChatStore((s) => s.isLoading)
  const streamingContent = useChatStore((s) => s.streamingContent)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="w-8 h-8 text-red-500"
            >
              <path d="M8.25 4.5a3.75 3.75 0 117.5 0v8.25a3.75 3.75 0 11-7.5 0V4.5z" />
              <path d="M6 10.5a.75.75 0 01.75.75v1.5a5.25 5.25 0 1010.5 0v-1.5a.75.75 0 011.5 0v1.5a6.75 6.75 0 01-13.5 0v-1.5A.75.75 0 016 10.5z" />
              <path d="M11.25 16.25v5.25a.75.75 0 001.5 0v-5.25a.75.75 0 00-1.5 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-zinc-300 mb-2">
            Race AI Copilot
          </h2>
          <p className="text-sm text-zinc-500 leading-relaxed">
            Ask about telemetry, car setup, circuit specifications, parts
            compatibility, or run simulations. Every answer is grounded in
            real race data and reviewed by the Crew Chief.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {[
              'What is the tire degradation trend?',
              'Suggest a setup for understeer in T4',
              'Best brake duct for Monaco',
              'Simulate lap 5 with current fuel',
            ].map((suggestion) => (
              <button
                key={suggestion}
                disabled={isLoading}
                onClick={() => useChatStore.getState().sendMessage(suggestion)}
                className="px-3 py-1.5 text-xs bg-zinc-900 border border-zinc-800
                           rounded-lg text-zinc-400 hover:text-zinc-200
                           hover:border-zinc-700 transition-colors
                           disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-4xl mx-auto">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Streaming indicator */}
        {isLoading && streamingContent && (
          <div className="flex justify-start mb-4">
            <div className="max-w-[80%] md:max-w-[70%] rounded-2xl rounded-bl-md px-4 py-3 bg-zinc-900 border border-zinc-800 text-zinc-100">
              <span className="text-xs font-medium opacity-70 mb-1.5 block">
                Copilot
              </span>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {streamingContent}
                <span className="inline-block w-2 h-4 bg-red-500 animate-pulse ml-0.5" />
              </p>
            </div>
          </div>
        )}

        {/* Typing indicator when waiting for first token */}
        {isLoading && !streamingContent && (
          <div className="flex justify-start mb-4">
            <div className="rounded-2xl rounded-bl-md px-4 py-3 bg-zinc-900 border border-zinc-800">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-zinc-500 rounded-full animate-pulse [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-zinc-500 rounded-full animate-pulse [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-zinc-500 rounded-full animate-pulse [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
