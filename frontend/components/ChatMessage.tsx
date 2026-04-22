interface ChatMessageProps {
  role: 'assistant' | 'user'
  content: string
}

export default function ChatMessage({ role, content }: ChatMessageProps) {
  const isAssistant = role === 'assistant'
  return (
    <div className={`flex ${isAssistant ? 'justify-start' : 'justify-end'} mb-4`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isAssistant
            ? 'bg-white border border-gray-200 text-gray-800 shadow-sm'
            : 'bg-indigo-600 text-white'
        }`}
      >
        {content}
      </div>
    </div>
  )
}
