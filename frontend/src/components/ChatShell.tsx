import { useChatStore } from '../stores/useChatStore'
import MessageList from './MessageList'
import ChatInput from './ChatInput'
import SessionContextPanel from './SessionContextPanel'
import ModelSelector from './ModelSelector'
import EvidenceDrawer from './EvidenceDrawer'
import ApprovalModal from './ApprovalModal'

export default function ChatShell() {
  const clearMessages = useChatStore((s) => s.clearMessages)
  const messages = useChatStore((s) => s.messages)

  // Get the latest assistant message's evidence for the drawer
  const lastAssistantMsg = [...messages]
    .reverse()
    .find((m) => m.role === 'assistant')
  const latestEvidence = lastAssistantMsg?.evidence ?? []
  const latestGroundedness = lastAssistantMsg?.confidence

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* ─── Left Sidebar ───────────────────────────────────── */}
      <aside className="hidden md:flex md:w-72 flex-col border-r border-zinc-800 bg-zinc-900/50">
        {/* Brand */}
        <div className="px-4 py-5 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <div
              className="flex items-center justify-center w-8 h-8 rounded-lg
                          bg-red-600 shadow-lg shadow-red-600/20"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5 text-white"
              >
                <path
                  fillRule="evenodd"
                  d="M10.339 2.237a.531.531 0 00-.678 0 11.947 11.947 0 01-7.078 2.75.5.5 0 00-.479.578 12.047 12.047 0 008.916 10.424.531.531 0 00.56-.11 12.047 12.047 0 008.916-10.425.5.5 0 00-.479-.578 11.947 11.947 0 01-7.078-2.75z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-bold text-zinc-100 leading-tight">
                Race Copilot
              </h1>
              <p className="text-[10px] text-zinc-500">AI Engineering Assistant</p>
            </div>
          </div>
        </div>

        {/* Session context & model */}
        <SessionContextPanel />
        <ModelSelector />

        {/* Spacer + Clear button */}
        <div className="flex-1" />
        <div className="px-4 py-3 border-t border-zinc-800">
          <button
            onClick={clearMessages}
            className="w-full text-xs text-zinc-500 hover:text-zinc-300
                       transition-colors py-1.5 rounded-lg
                       hover:bg-zinc-800/50"
          >
            Clear conversation
          </button>
        </div>
      </aside>

      {/* ─── Main Chat Area ─────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-red-600 flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-4 h-4 text-white"
              >
                <path
                  fillRule="evenodd"
                  d="M10.339 2.237a.531.531 0 00-.678 0 11.947 11.947 0 01-7.078 2.75.5.5 0 00-.479.578 12.047 12.047 0 008.916 10.424.531.531 0 00.56-.11 12.047 12.047 0 008.916-10.425.5.5 0 00-.479-.578 11.947 11.947 0 01-7.078-2.75z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold">Race Copilot</span>
          </div>
          <button
            onClick={clearMessages}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Clear
          </button>
        </div>

        <MessageList />
        <ChatInput />
      </div>

      {/* ─── Evidence Drawer (slide-over) ───────────────────── */}
      <EvidenceDrawer
        evidence={latestEvidence}
        groundednessScore={latestGroundedness}
      />

      {/* ─── Approval Modal ─────────────────────────────────── */}
      <ApprovalModal />
    </div>
  )
}
