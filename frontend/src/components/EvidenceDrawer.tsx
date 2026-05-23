import { useChatStore } from '../stores/useChatStore'
import type { EvidenceItem } from '../types/chat'

interface EvidenceDrawerProps {
  evidence: EvidenceItem[]
  groundednessScore?: number
}

export default function EvidenceDrawer({
  evidence,
  groundednessScore,
}: EvidenceDrawerProps) {
  const isOpen = useChatStore((s) => s.evidenceDrawerOpen)
  const toggle = useChatStore((s) => s.toggleEvidenceDrawer)

  const scoreColor =
    groundednessScore !== undefined
      ? groundednessScore >= 0.8
        ? 'text-emerald-400'
        : groundednessScore >= 0.5
          ? 'text-yellow-400'
          : 'text-red-400'
      : 'text-zinc-500'

  return (
    <>
      {/* Overlay when open on mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={toggle}
        />
      )}

      {/* Slide-over panel */}
      <aside
        className={`
          fixed top-0 right-0 h-full w-80 max-w-[85vw] z-40
          bg-zinc-900 border-l border-zinc-800
          transform transition-transform duration-200 ease-in-out
          flex flex-col
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-100">Evidence</h2>
          <button
            onClick={toggle}
            className="text-zinc-400 hover:text-zinc-200 transition-colors"
            aria-label="Close evidence drawer"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-5 h-5"
            >
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>

        {/* Groundedness score */}
        {groundednessScore !== undefined && (
          <div className="px-4 py-3 border-b border-zinc-800">
            <span className="text-xs text-zinc-500 uppercase tracking-wider">
              Groundedness Score
            </span>
            <div className="mt-1 flex items-center gap-2">
              <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    groundednessScore >= 0.8
                      ? 'bg-emerald-500'
                      : groundednessScore >= 0.5
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                  }`}
                  style={{ width: `${groundednessScore * 100}%` }}
                />
              </div>
              <span className={`text-sm font-mono ${scoreColor}`}>
                {(groundednessScore * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {/* Evidence list */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {evidence.length === 0 ? (
            <p className="text-sm text-zinc-500 italic">
              No evidence sources cited for this response.
            </p>
          ) : (
            evidence.map((item) => (
              <div
                key={item.id}
                className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/50"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-medium text-zinc-200 leading-tight">
                    {item.title}
                  </h3>
                  <span className="text-[10px] text-zinc-500 font-mono shrink-0 mt-0.5">
                    {item.id}
                  </span>
                </div>
                <p className="mt-2 text-xs text-zinc-400 leading-relaxed line-clamp-3">
                  {item.snippet}
                </p>
                <a
                  href={item.url_or_path}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-xs text-red-500 hover:text-red-400 transition-colors"
                >
                  View source →
                </a>
              </div>
            ))
          )}
        </div>

        {/* Toggle button when closed — floating on the edge */}
      </aside>

      {/* Floating open button when drawer is closed */}
      {!isOpen && evidence.length > 0 && (
        <button
          onClick={toggle}
          className="fixed top-4 right-4 z-20 bg-zinc-900 border border-zinc-700
                     rounded-lg px-3 py-2 text-xs text-zinc-400
                     hover:text-zinc-200 hover:border-zinc-500 transition-colors
                     shadow-lg"
        >
          Evidence ({evidence.length})
        </button>
      )}
    </>
  )
}
