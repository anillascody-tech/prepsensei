import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PrepSensei — AI 面试模拟',
  description: 'AI-powered personalized interview simulation based on RAG + DeepSeek',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  )
}
