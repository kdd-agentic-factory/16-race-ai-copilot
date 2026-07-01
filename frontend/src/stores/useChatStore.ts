import { create } from 'zustand'
import type {
  Message,
  ChatRequest,
  ChatResponse,
  SessionContext,
} from '../types/chat'
import { sendMessageStream } from '../api/chat'

let messageCounter = 0
function nextId(): string {
  messageCounter += 1
  return `msg-${Date.now()}-${messageCounter}`
}

function now(): string {
  return new Date().toISOString()
}

// ─── State shape ─────────────────────────────────────────────────

export interface ChatState {
  // Conversation
  messages: Message[]
  conversationId: string | null
  sessionId: string

  // UI state
  isLoading: boolean
  error: string | null
  streamingContent: string | null

  // Panels
  evidenceDrawerOpen: boolean
  approvalModalOpen: boolean
  pendingResponse: ChatResponse | null

  // Settings
  model: string
  sessionContext: SessionContext

  // Actions
  sendMessage: (content: string) => Promise<void>
  addMessage: (msg: Omit<Message, 'id' | 'created_at'>) => string
  clearMessages: () => void
  setModel: (model: string) => void
  setSessionContext: (ctx: Partial<SessionContext>) => void
  toggleEvidenceDrawer: () => void
  approveAction: () => void
  rejectAction: () => void
}

// ─── Defaults ────────────────────────────────────────────────────

const DEFAULT_SESSION_ID = `session-${Date.now()}`
const DEFAULT_MODEL = 'qwen2.5:7b'

// ─── Store ───────────────────────────────────────────────────────

export const useChatStore = create<ChatState>((set, get) => ({
  // ── Initial state ────────────────────────────────────────────
  messages: [],
  conversationId: null,
  sessionId: DEFAULT_SESSION_ID,
  isLoading: false,
  error: null,
  streamingContent: null,
  evidenceDrawerOpen: false,
  approvalModalOpen: false,
  pendingResponse: null,
  model: DEFAULT_MODEL,
  sessionContext: {
    circuit: 'Jerez',
    session_type: 'Practice',
    session_id: DEFAULT_SESSION_ID,
  },

  // ── Actions ──────────────────────────────────────────────────

  addMessage: (msg) => {
    const id = nextId()
    const message: Message = { ...msg, id, created_at: now() }
    set((s) => ({ messages: [...s.messages, message] }))
    return id
  },

  sendMessage: async (content: string) => {
    const { conversationId, sessionId, model, addMessage } = get()

    // Guard: prevent duplicate sends
    if (get().isLoading) return

    // 1. Add user message
    addMessage({ role: 'user', content })

    // 2. Set loading state
    set({ isLoading: true, error: null, streamingContent: '' })

    try {
      const payload: ChatRequest = {
        conversation_id: conversationId,
        session_id: sessionId,
        message: content,
        model,
        require_evidence: true,
        stream: true,
        context: {},
      }

      // Use streaming endpoint — onToken populates streamingContent
      const response = await sendMessageStream(payload, (token) => {
        set((s) => ({
          streamingContent: (s.streamingContent ?? '') + token,
        }))
      })

      // 3. Store conversation ID for follow-up
      if (!conversationId && response.conversation_id) {
        set({ conversationId: response.conversation_id })
      }

      // 4. Add assistant message
      addMessage({
        role: 'assistant',
        content: response.answer,
        tool_calls: response.tool_calls,
        evidence: response.evidence,
        recommendations: response.recommendations,
        approval_required: response.approval_required,
        approver_role: response.approver_role,
        confidence: response.confidence,
        uncertainty: response.uncertainty,
        next_actions: response.next_actions,
        conversation_id: response.conversation_id,
        message_id: response.message_id,
      })

      // 5. Handle pending approval
      if (response.approval_required) {
        set({
          approvalModalOpen: true,
          pendingResponse: response,
        })
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred'
      set({ error: message })
    } finally {
      set({ isLoading: false, streamingContent: null })
    }
  },

  clearMessages: () =>
    set({
      messages: [],
      conversationId: null,
      error: null,
      streamingContent: null,
    }),

  setModel: (model: string) => set({ model }),

  setSessionContext: (ctx: Partial<SessionContext>) =>
    set((s) => ({ sessionContext: { ...s.sessionContext, ...ctx } })),

  toggleEvidenceDrawer: () =>
    set((s) => ({ evidenceDrawerOpen: !s.evidenceDrawerOpen })),

  approveAction: async () => {
    const { pendingResponse, conversationId, sessionId, model, addMessage } = get()
    if (!pendingResponse) return

    set({ approvalModalOpen: false })

    // Re-send the original request with approval granted
    set({ isLoading: true, error: null, streamingContent: '' })

    try {
      // Find the last user message to get the original content
      const messages = get().messages
      const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user')
      if (!lastUserMsg) throw new Error('No user message found to re-send')

      const payload: ChatRequest = {
        conversation_id: conversationId,
        session_id: sessionId,
        message: lastUserMsg.content,
        model,
        require_evidence: true,
        stream: true,
        approval_granted: true,
        context: {},
      }

      const response = await sendMessageStream(payload, (token) => {
        set((s) => ({
          streamingContent: (s.streamingContent ?? '') + token,
        }))
      })

      addMessage({
        role: 'assistant',
        content: response.answer,
        tool_calls: response.tool_calls,
        evidence: response.evidence,
        recommendations: response.recommendations,
        approval_required: false,
        confidence: response.confidence,
        uncertainty: response.uncertainty,
        next_actions: response.next_actions,
        conversation_id: response.conversation_id,
        message_id: response.message_id,
      })
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to execute approved action'
      set({ error: message })
    } finally {
      set({ isLoading: false, streamingContent: null, pendingResponse: null })
    }
  },

  rejectAction: () => {
    const { addMessage } = get()
    // Add a system message explaining the rejection
    addMessage({
      role: 'assistant',
      content: 'Action rejected by crew chief. The request was not executed. No changes were made to the car setup.',
    })
    set({ approvalModalOpen: false, pendingResponse: null })
  },
}))
