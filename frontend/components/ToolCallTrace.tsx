'use client'
import { useState } from 'react'

interface ToolCall {
  tool_name: string
  args: Record<string, unknown>
  result?: string
}

export default function ToolCallTrace({ toolCall }: { toolCall: ToolCall }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="my-2 border border-amber-200 rounded-lg bg-amber-50 text-xs font-mono overflow-hidden">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left text-amber-700 hover:bg-amber-100 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <span>⚡</span>
        <span className="font-semibold">Agent 调用: {toolCall.tool_name}</span>
        <span className="ml-auto text-amber-400">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-amber-200">
          <div className="mt-2">
            <div className="text-amber-600 mb-1">参数:</div>
            <pre className="bg-white border border-amber-100 rounded p-2 overflow-x-auto">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>
          {toolCall.result && (
            <div>
              <div className="text-amber-600 mb-1">结果:</div>
              <pre className="bg-white border border-amber-100 rounded p-2 overflow-x-auto max-h-32">
                {toolCall.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
