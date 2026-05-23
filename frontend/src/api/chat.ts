import { apiFetch } from './client'
import type { ChatRequest, ChatResponse } from '../types/chat'

/**
 * Send a chat message to the backend and receive the full response.
 *
 * The backend runs the Intent → Plan → Evidence → Compose pipeline and
 * returns a structured ChatResponse with answer, evidence, tool traces,
 * and governance metadata.
 *
 * @param request  The chat request payload.
 * @param signal   Optional AbortSignal to cancel the request.
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
