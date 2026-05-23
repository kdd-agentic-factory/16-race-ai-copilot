/** Mirrors backend ToolCallRecord schema. */
export interface ToolCallRecord {
  tool_name: string
  parameters: Record<string, unknown>
  result: unknown | null
  timestamp: string
}

/** Mirrors backend EvidenceItem schema. */
export interface EvidenceItem {
  id: string
  title: string
  url_or_path: string
  snippet: string
}

/** Mirrors backend EvidencePacket (flattened for the UI). */
export interface EvidencePacket {
  sources: EvidenceItem[]
  raw_data: string[]
  groundedness_score: number
}

/** Mirrors backend Recommendation schema. */
export interface Recommendation {
  action: string
  rationale: string
  parameters: Record<string, unknown>
}

/** Mirrors backend ChatRequest schema. */
export interface ChatRequest {
  conversation_id?: string | null
  session_id?: string | null
  message: string
  model?: string | null
  require_evidence?: boolean
  stream?: boolean
  context?: Record<string, unknown>
}

/** Mirrors backend ChatResponse schema. */
export interface ChatResponse {
  conversation_id: string
  message_id: string
  answer: string
  confidence: number
  evidence: EvidenceItem[]
  tool_calls: ToolCallRecord[]
  recommendations: Recommendation[]
  approval_required: boolean
  approver_role: string | null
  uncertainty: string | null
  next_actions: string[]
}

/** UI-level message combining user input and assistant response. */
export type MessageRole = 'user' | 'assistant'

export interface Message {
  id: string
  role: MessageRole
  content: string
  tool_calls?: ToolCallRecord[]
  evidence?: EvidenceItem[]
  recommendations?: Recommendation[]
  approval_required?: boolean
  approver_role?: string | null
  confidence?: number
  uncertainty?: string | null
  next_actions?: string[]
  conversation_id?: string
  message_id?: string
  created_at: string
}

/** Session-level metadata displayed in the sidebar. */
export interface SessionContext {
  circuit?: string
  session_type?: string
  session_id?: string
  driver?: string
  car_number?: string
}
