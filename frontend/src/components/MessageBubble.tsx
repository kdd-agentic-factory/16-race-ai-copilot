import type { Message } from '../types/chat'
import ToolCallTimeline from './ToolCallTimeline'
import ApprovalBadge from './ApprovalBadge'
import { useChatStore } from '../stores/useChatStore'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const toggleEvidenceDrawer = useChatStore((s) => s.toggleEvidenceDrawer)

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] md:max-w-[70%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-red-600 text-white rounded-br-md'
            : 'bg-zinc-900 text-zinc-100 border border-zinc-800 rounded-bl-md'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 mb-1.5">
          <span className="text-xs font-medium opacity-70">
            {isUser ? 'You' : 'Copilot'}
          </span>
          {message.confidence !== undefined && !isUser && (
            <span
              className={`text-[10px] font-mono ${
                message.confidence >= 0.8
                  ? 'text-emerald-400'
                  : message.confidence >= 0.5
                    ? 'text-yellow-400'
                    : 'text-red-400'
              }`}
            >
              {(message.confidence * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>

        {/* Content */}
        <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {message.content}
        </div>

        {/* Uncertainty disclaimer */}
        {message.uncertainty && (
          <p className="mt-2 text-xs text-yellow-400/80 italic">
            ⚠ {message.uncertainty}
          </p>
        )}

        {/* Tool calls timeline */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <ToolCallTimeline calls={message.tool_calls} />
        )}

        {/* Approval badge */}
        {message.approval_required && (
          <div className="mt-3">
            <ApprovalBadge approverRole={message.approver_role} />
          </div>
        )}

        {/* Evidence & Next actions footer */}
        {!isUser && (
          <div className="mt-3 pt-2 border-t border-zinc-800 flex flex-wrap items-center gap-2">
            {message.evidence && message.evidence.length > 0 && (
              <button
                onClick={toggleEvidenceDrawer}
                className="text-[11px] text-red-500 hover:text-red-400 transition-colors font-medium"
              >
                {message.evidence.length} evidence source
                {message.evidence.length !== 1 ? 's' : ''}
              </button>
            )}

            {message.next_actions && message.next_actions.length > 0 && (
              <details className="text-[11px] text-zinc-500">
                <summary className="cursor-pointer hover:text-zinc-300 transition-colors">
                  Next actions
                </summary>
                <ul className="mt-1 space-y-0.5 list-disc list-inside">
                  {message.next_actions.map((action, i) => (
                    <li key={i} className="text-zinc-400">
                      {action}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
