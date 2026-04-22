export interface SSEEvent {
  type: string
  content?: string
  data?: Record<string, unknown>
  cursor: number
}

/**
 * Cursor-based SSE client.
 * IMPORTANT: Connects DIRECTLY to the backend URL — never through Next.js /api/ proxy.
 * Vercel buffers SSE through API routes, breaking streaming.
 * On reconnect, resumes from the last cursor position so no events are lost.
 */
export function createSSEStream(
  sessionId: string,
  onEvent: (event: SSEEvent) => void,
  onError?: (err: Event) => void
): () => void {
  let cursor = 0
  let es: EventSource | null = null
  let closed = false

  const connect = () => {
    if (closed) return
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    const url = `${backendUrl}/api/interview/stream?session_id=${sessionId}&cursor=${cursor}`
    es = new EventSource(url)

    es.onmessage = (e) => {
      try {
        const data: SSEEvent = JSON.parse(e.data)
        cursor = data.cursor + 1
        onEvent(data)
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = (err) => {
      es?.close()
      if (onError) onError(err)
      if (!closed) setTimeout(connect, 2000) // auto-reconnect, cursor preserved
    }
  }

  connect()
  return () => {
    closed = true
    es?.close()
  }
}
