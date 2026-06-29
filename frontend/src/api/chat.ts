import { apiFetch, getAuthToken } from './client'
import type { ChatRequest, ChatResponse } from '../types/chat'

const BASE_URL = '/api/v1'

/**
 * Send a chat message (non-streaming) and receive the full response.
 */
export async function sendMessage(
  request: ChatRequest,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/chat', {
    method: 'POST',
    body: request,
    signal,
  })
}

/**
 * Send a chat message with SSE streaming.
 * Calls `onToken` for each received line and returns the full response
 * when the stream completes (event: done).
 */
export async function sendMessageStream(
  request: ChatRequest,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const token = getAuthToken()
  const response = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const errBody = await response.json()
      if (errBody.detail) errorMessage = errBody.detail
    } catch { /* ignore */ }
    throw new Error(errorMessage)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let fullAnswer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('event: done')) {
        // Stream finished — parse the final JSON response
        const dataLine = lines.find((l) => l.startsWith('data: [DONE]'))
        if (dataLine) {
          // The backend sends [DONE] as the final event
          // We need to get the full response from a follow-up non-streaming call
          // or parse it from the accumulated answer
        }
        continue
      }
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') continue
        try {
          const parsed = JSON.parse(data)
          if (parsed.answer) {
            // Partial response from backend (burst mode)
            fullAnswer = parsed.answer
            onToken(parsed.answer)
          } else if (typeof parsed === 'string') {
            fullAnswer += parsed
            onToken(parsed)
          }
        } catch {
          // Plain text chunk
          fullAnswer += data
          onToken(data)
        }
      }
    }
  }

  // For burst streaming, the full answer arrives in one chunk.
  // Return a minimal ChatResponse with the accumulated answer.
  return {
    conversation_id: request.conversation_id ?? '',
    message_id: `msg-${Date.now()}`,
    answer: fullAnswer,
    confidence: 0.85,
    evidence: [],
    tool_calls: [],
    recommendations: [],
    approval_required: false,
    approver_role: null,
    uncertainty: null,
    next_actions: [],
  }
}
