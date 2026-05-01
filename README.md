# PrepSensei — AI 个性化面试模拟

> 上传简历 + JD，AI 自动生成 5 个个性化面试模块，逐轮提问、智能追问，面试结束输出结构化评分报告。

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-API-orange)](https://deepseek.com)

## 架构

```
前端 (Next.js / Vercel)
  简历上传 · JD 输入 · 面试对话 · 评分报告
        │ SSE + HTTP（直连后端，绕过 Vercel 代理避免 SSE 缓冲）
后端 (FastAPI / Render Docker)
  PDF 解析 → RAG 索引 → Agent 循环
  ├── retrieve_questions   BM25 + ChromaDB 混合检索，RRF 融合排序
  ├── evaluate_and_route   DeepSeek 评估回答，决策追问或进入下一模块
  └── generate_report      生成 Markdown 评分报告
  ChromaDB in-memory（适配 Render 免费层 ephemeral 磁盘）
  └── question_bank · resume_{sid} · jd_{sid}
```

## 技术亮点

**Agent**
- 手写 ~150 LOC 原生 Function Calling 循环，不依赖 LangChain，完整掌控工具调度与多轮消息拼接
- ReAct 范式：`evaluate_and_route` 自主决策追问（硬上限 2 次防死循环）或推进下一模块
- `ToolCallTrace` 组件实时渲染工具调用链路，CoT 过程前端透明可见

**RAG**
- 父子文本块分层索引：句子级 child 命中 → 返回段落级 parent，兼顾召回精度与上下文完整性
- 混合检索：BM25Okapi + ChromaDB 语义向量，RRF（k=60）融合排序
- CJK bigram 分词器，修复 `str.split()` 导致中文 BM25 评分近零的问题
- section 元数据过滤（skills / experience / requirements / responsibilities），定向召回

**工程**
- `asyncio.to_thread()` 将同步 embedding 移出事件循环，避免阻塞并发请求
- `SessionStore.on_delete()` 回调，会话过期自动释放 ChromaDB collection，消除内存泄漏
- Cursor-based SSE：事件按游标追加，断线重连不丢事件

## 技术栈

| | |
|---|---|
| LLM | DeepSeek API（chat） |
| Embedding | sentence-transformers `all-MiniLM-L6-v2`（本地，无需 API） |
| 向量库 | ChromaDB in-memory |
| 后端 | FastAPI · uvicorn · slowapi 限流 |
| 前端 | Next.js 14 · TypeScript · Tailwind CSS |
| 部署 | Render（Docker）+ Vercel |

## 本地运行

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env          # 填入 DEEPSEEK_API_KEY
uvicorn main:app --reload     # http://localhost:8000/docs

# 前端
cd frontend
npm install
# 确认 .env.local: NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm run dev                   # http://localhost:3000

# 测试
cd backend && pytest tests/ -v
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/session` | 创建会话 |
| POST | `/api/session/{id}/resume` | 上传 PDF 简历 |
| POST | `/api/session/{id}/jd` | 提交 JD 文本 |
| POST | `/api/session/{id}/start` | 生成模块并开始面试 |
| POST | `/api/session/{id}/answer` | 提交回答，触发 Agent |
| GET | `/api/interview/stream` | SSE 事件流（?session_id=&cursor=） |

## License

MIT
