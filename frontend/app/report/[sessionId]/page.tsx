'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'

export default function ReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const router = useRouter()
  const [report, setReport] = useState('')

  useEffect(() => {
    const stored = localStorage.getItem(`report_${sessionId}`)
    if (stored) setReport(stored)
  }, [sessionId])

  const handleDownload = () => {
    const blob = new Blob([report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `prepsensei_report_${String(sessionId).slice(0, 8)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <main className="min-h-screen max-w-3xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">面试评估报告</h1>
          <p className="text-sm text-gray-500 mt-1">PrepSensei · AI 个性化面试模拟</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
          >
            重新面试
          </button>
          <button
            onClick={handleDownload}
            disabled={!report}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:bg-indigo-300 transition-colors"
          >
            下载报告
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-8 prose prose-gray prose-sm max-w-none">
        {report ? (
          <ReactMarkdown>{report}</ReactMarkdown>
        ) : (
          <div className="text-center py-12 text-gray-400">
            <div className="animate-spin w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p>报告生成中，请稍候...</p>
          </div>
        )}
      </div>
    </main>
  )
}
