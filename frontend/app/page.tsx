'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createSession, uploadResume, submitJD } from '@/lib/api'

export default function Home() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [jd, setJD] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleStart = async () => {
    if (!file || !jd.trim()) { setError('请上传简历并填写岗位描述'); return }
    if (file.size > 5 * 1024 * 1024) { setError('简历文件不能超过 5MB'); return }
    setLoading(true)
    setError('')
    try {
      const sessionId = await createSession()
      await uploadResume(sessionId, file)
      await submitJD(sessionId, jd)
      router.push(`/interview/${sessionId}`)
    } catch {
      setError('连接后端失败，请确认后端已启动 (uvicorn main:app)')
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">PrepSensei</h1>
          <p className="text-gray-500 text-lg">AI 个性化面试模拟 · 上传简历，开始练习</p>
          <p className="text-gray-400 text-sm mt-1">基于 RAG + DeepSeek Function Calling</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              上传简历 <span className="text-gray-400 font-normal">(PDF，最大 5MB)</span>
            </label>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
            />
            {file && (
              <p className="mt-1 text-xs text-green-600">
                ✓ {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              粘贴目标岗位 JD
            </label>
            <textarea
              value={jd}
              onChange={(e) => setJD(e.target.value)}
              placeholder="将职位描述粘贴到这里..."
              rows={8}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}

          <button
            onClick={handleStart}
            disabled={loading || !file || !jd.trim()}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-colors text-base"
          >
            {loading ? '准备面试中...' : '开始面试 →'}
          </button>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          PrepSensei · Powered by DeepSeek API
        </p>
      </div>
    </main>
  )
}
