'use client'
import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { startInterview, submitAnswer } from '@/lib/api'
import { createSSEStream, SSEEvent } from '@/lib/sseClient'
import ChatMessage from '@/components/ChatMessage'
import ToolCallTrace from '@/components/ToolCallTrace'

interface Message {
  id: number
  role: 'assistant' | 'user'
  content?: string
  toolCall?: { tool_name: string; args: Record<string, unknown>; result?: string }
}

export default function InterviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const router = useRouter()
  const [modules, setModules] = useState<Array<{ topic: string }>>([])
  const [currentModule, setCurrentModule] = useState(0)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [started, setStarted] = useState(false)
  const msgIdRef = useRef(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sseStarted = useRef(false)
  const sseCleanup = useRef<(() => void) | null>(null)

  const handleSSEEvent = (event: SSEEvent) => {
    if (event.type === 'assistant_text' && event.content) {
      setMessages(prev => [...prev, { id: msgIdRef.current++, role: 'assistant', content: event.content }])
    } else if (event.type === 'tool_call' && event.data) {
      setMessages(prev => [...prev, {
        id: msgIdRef.current++,
        role: 'assistant',
        toolCall: event.data as Message['toolCall'],
      }])
    } else if (event.type === 'tool_result' && event.data) {
      const d = event.data as Record<string, unknown>
      setMessages(prev => {
        const copy = [...prev]
        for (let i = copy.length - 1; i >= 0; i--) {
          if (copy[i].toolCall?.tool_name === d.tool_name) {
            copy[i] = { ...copy[i], toolCall: { ...copy[i].toolCall!, result: String(d.result ?? '') } }
            break
          }
        }
        return copy
      })
    } else if (event.type === 'module_complete' && event.data?.module_index !== undefined) {
      setCurrentModule(Number(event.data.module_index) + 1)
    } else if (event.type === 'interview_complete') {
      if (event.content) localStorage.setItem(`report_${sessionId}`, event.content)
      sseCleanup.current?.()
      router.push(`/report/${sessionId}`)
    }
  }

  useEffect(() => {
    if (!sessionId) return
    startInterview(sessionId)
      .then((data) => {
        setModules(data.modules)
        setStarted(true)
        if (!sseStarted.current) {
          sseStarted.current = true
          sseCleanup.current = createSSEStream(sessionId, handleSSEEvent)
        }
      })
      .catch(console.error)
    return () => { sseCleanup.current?.() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading || !started) return
    const answer = input.trim()
    setInput('')
    setLoading(true)
    setMessages(prev => [...prev, { id: msgIdRef.current++, role: 'user', content: answer }])
    try {
      await submitAnswer(sessionId, answer)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex flex-col max-w-3xl mx-auto">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div>
          <h1 className="font-semibold text-gray-900">PrepSensei 面试</h1>
          {modules.length > 0 && (
            <p className="text-sm text-gray-500">
              模块 {Math.min(currentModule + 1, modules.length)}/{modules.length}
              {modules[currentModule] && ` · ${(modules[currentModule] as { topic: string }).topic}`}
            </p>
          )}
        </div>
        <div className="flex gap-1.5">
          {modules.map((_, i) => (
            <div
              key={i}
              className={`w-8 h-1.5 rounded-full transition-colors ${
                i < currentModule ? 'bg-green-500' : i === currentModule ? 'bg-indigo-600' : 'bg-gray-200'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {!started && (
          <div className="text-center text-gray-400 mt-20">
            <div className="animate-spin w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p>正在生成个性化面试模块...</p>
          </div>
        )}
        {messages.map((msg) =>
          msg.toolCall ? (
            <ToolCallTrace key={msg.id} toolCall={msg.toolCall} />
          ) : (
            <ChatMessage key={msg.id} role={msg.role} content={msg.content || ''} />
          )
        )}
        {loading && (
          <div className="flex justify-start mb-4">
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4 sticky bottom-0">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
            }}
            placeholder={started ? '输入你的回答... (Enter 发送，Shift+Enter 换行)' : '正在初始化...'}
            rows={3}
            disabled={!started || loading}
            className="flex-1 border border-gray-300 rounded-xl px-4 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-400"
          />
          <button
            onClick={handleSend}
            disabled={!started || loading || !input.trim()}
            className="px-5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors self-end py-2"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}
