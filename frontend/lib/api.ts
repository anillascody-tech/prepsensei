const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function createSession(): Promise<string> {
  const res = await fetch(`${BACKEND_URL}/api/session`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to create session')
  const data = await res.json()
  return data.session_id
}

export async function uploadResume(sessionId: string, file: File): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BACKEND_URL}/api/session/${sessionId}/resume`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Failed to upload resume')
}

export async function submitJD(sessionId: string, jdText: string): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/session/${sessionId}/jd`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_text: jdText }),
  })
  if (!res.ok) throw new Error('Failed to submit JD')
}

export async function startInterview(
  sessionId: string
): Promise<{ modules: Array<{ topic: string; initial_question: string; description: string }> }> {
  const res = await fetch(`${BACKEND_URL}/api/session/${sessionId}/start`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to start interview')
  return res.json()
}

export async function submitAnswer(
  sessionId: string,
  answer: string
): Promise<{ events_added: number }> {
  const res = await fetch(`${BACKEND_URL}/api/session/${sessionId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answer }),
  })
  if (!res.ok) throw new Error('Failed to submit answer')
  return res.json()
}
