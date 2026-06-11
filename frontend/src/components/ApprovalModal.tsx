import { useChatStore } from '../stores/useChatStore'

export default function ApprovalModal() {
  const isOpen = useChatStore((s) => s.approvalModalOpen)
  const pendingResponse = useChatStore((s) => s.pendingResponse)
  const approveAction = useChatStore((s) => s.approveAction)
  const rejectAction = useChatStore((s) => s.rejectAction)

  if (!isOpen || !pendingResponse) return null

  const toolCalls = pendingResponse.tool_calls ?? []
  const recommendations = pendingResponse.recommendations ?? []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={rejectAction}
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="approval-modal-title"
        className="relative bg-zinc-900 border border-zinc-700 rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-6 pt-5 pb-4 border-b border-zinc-800">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-full
                        bg-yellow-500/10 border border-yellow-500/30 shrink-0"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-5 h-5 text-yellow-400"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div>
            <h2
              id="approval-modal-title"
              className="text-lg font-semibold text-zinc-100"
            >
              Crew Chief Approval Required
            </h2>
            <p className="text-sm text-zinc-400">
              {pendingResponse.approver_role ?? 'Crew Chief'} must approve this
              action before execution.
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Tool calls to approve */}
          {toolCalls.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                Proposed Actions
              </h3>
              <div className="space-y-2">
                {toolCalls.map((tc, idx) => (
                  <div
                    key={idx}
                    className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/50"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-red-400">
                        {tc.tool_name}
                      </span>
                    </div>
                    {tc.parameters &&
                      Object.keys(tc.parameters).length > 0 && (
                        <pre className="mt-1 text-xs text-zinc-400 overflow-x-auto">
                          {JSON.stringify(tc.parameters, null, 2)}
                        </pre>
                      )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                Recommendations
              </h3>
              <div className="space-y-2">
                {recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/50"
                  >
                    <p className="text-sm font-medium text-zinc-200">
                      {rec.action}
                    </p>
                    <p className="text-xs text-zinc-400 mt-1">
                      {rec.rationale}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Answer preview */}
          <div>
            <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
              Response Preview
            </h3>
            <p className="text-sm text-zinc-300 leading-relaxed line-clamp-4">
              {pendingResponse.answer}
            </p>
          </div>
        </div>

        {/* Footer / Actions */}
        <div className="px-6 py-4 border-t border-zinc-800 flex gap-3">
          <button
            onClick={rejectAction}
            className="flex-1 px-4 py-2.5 rounded-xl border border-zinc-700
                       text-sm font-medium text-zinc-300
                       hover:bg-zinc-800 hover:text-zinc-100
                       transition-colors"
          >
            Reject
          </button>
          <button
            onClick={approveAction}
            className="flex-1 px-4 py-2.5 rounded-xl bg-emerald-600
                       text-sm font-medium text-white
                       hover:bg-emerald-500
                       transition-colors"
          >
            Approve & Execute
          </button>
        </div>
      </div>
    </div>
  )
}
