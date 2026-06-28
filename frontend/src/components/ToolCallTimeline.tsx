import type { ToolCallRecord } from '../types/chat'

interface ToolCallTimelineProps {
  calls: ToolCallRecord[]
}

function ToolIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="w-3.5 h-3.5"
    >
      <path
        fillRule="evenodd"
        d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.312h5.245a.75.75 0 000-1.5H4.989l-.356-.356a5.5 5.5 0 017.93-6.131.75.75 0 11.778 1.282 4 4 0 00-5.063 5.814l6.974 6.974a.75.75 0 101.06-1.06l-6-6z"
        clipRule="evenodd"
      />
    </svg>
  )
}

export default function ToolCallTimeline({ calls }: ToolCallTimelineProps) {
  if (!calls || calls.length === 0) return null

  return (
    <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/40 p-3 space-y-3">
      <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
        Tool Calls
      </span>
      {calls.map((call, idx) => (
        <div key={`${call.tool_name}-${idx}`} className="relative pl-6">
          {/* Dot on timeline */}
          <span
            className="absolute left-0 top-1 w-4 h-4 rounded-full
                       bg-zinc-800 border-2 border-zinc-600
                       flex items-center justify-center"
          >
            <ToolIcon />
          </span>

          <div className="text-sm">
            <span className="text-zinc-200 font-mono text-xs">
              {call.tool_name}
            </span>
            {call.timestamp && (
              <span className="text-zinc-500 text-xs ml-2">
                {new Date(call.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>

          {call.parameters && Object.keys(call.parameters).length > 0 && (
            <pre className="mt-1 text-xs text-zinc-400 bg-zinc-900 rounded p-2 overflow-x-auto">
              {JSON.stringify(call.parameters, null, 1)}
            </pre>
          )}

          {call.result !== null && call.result !== undefined && (
            <div className="mt-1 text-xs text-emerald-400">
              <span className="text-zinc-500">→ </span>
              {typeof call.result === 'string'
                ? call.result
                : JSON.stringify(call.result).slice(0, 120)}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
