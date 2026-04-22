# PrepSensei — AI 个性化面试模拟 Agent

> 基于 RAG + DeepSeek Function Calling 构建的 AI 面试官，上传简历和 JD，体验真实的 AI 工程师面试

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-API-orange)](https://deepseek.com)

## 项目亮点

- **三路 RAG 知识融合** — 简历解析 + JD 要求提取 + 行业题库，生成个性化面试问题
- **DeepSeek Function Calling Agent** — 手写 Agent 循环（~150 LOC），动态决策是否追问
- **Agent 思考过程可视化** — 每次工具调用实时展示在前端（ToolCallTrace 组件）
- **Cursor-based SSE 流式输出** — 断线自动重连，光标续传，不丢失任何事件
- **云端部署** — Render（后端）+ Vercel（前端），简历直接附在线 Demo 链接

## 架构

```
┌─────────────────────────────────────┐
│         前端 (Next.js + Vercel)      │
│  简历上传 | JD输入 | 面试对话 | 报告  │
└──────────────┬──────────────────────┘
               │ SSE / HTTP (直连后端，不经 Vercel 代理)
┌──────────────▼──────────────────────┐
│       后端 (FastAPI + Render)        │
│                                     │
│  PDF解析 → RAG索引 → Agent循环       │
│                                     │
│  Tools (Function Calling):          │
│  ├─ retrieve_questions (ChromaDB)   │
│  ├─ evaluate_and_route (DeepSeek)   │
│  └─ generate_report                 │
│                                     │
│  ChromaDB (in-memory)               │
│  ├─ resume_{session_id}            │
│  ├─ jd_{session_id}               │
│  └─ question_bank (80+ 题)          │
└──────────────────────────────────────┘
```

## 面试流程

1. 上传 PDF 简历 + 粘贴目标 JD
2. 系统基于简历+JD 生成 5 个个性化面试模块
3. Agent 主持每个模块的面试（RAG 检索相关题目）
4. 每模块最多追问 2 次（Agent 自主决策）
5. 全部完成后生成结构化评分报告

## 技术栈

| 层 | 技术 |
|----|------|
| LLM | DeepSeek API（chat + embeddings） |
| 后端框架 | FastAPI + uvicorn |
| 向量库 | ChromaDB in-memory（适配 Render 免费层） |
| PDF 解析 | PyPDF2 |
| 限流 | slowapi + ProxyHeadersMiddleware |
| 前端 | Next.js 14 + TypeScript + Tailwind CSS |
| 部署 | Render（后端 Docker）+ Vercel（前端） |

## 本地开发

### 前提条件

- Python 3.11+
- Node.js 18+
- DeepSeek API Key（[申请地址](https://platform.deepseek.com)）

### 后端

```bash
cd prepsensei/backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

uvicorn main:app --reload
# API 文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/healthz
```

### 前端

```bash
cd prepsensei/frontend
npm install
cp .env.local.example .env.local
# 确认 NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

npm run dev
# http://localhost:3000
```

### 运行测试

```bash
cd prepsensei/backend
pytest tests/ -v

# 验证题库质量
python scripts/validate_question_bank.py
```

## 部署

### 后端 → Render

1. 将代码推送到 GitHub
2. Render Dashboard → New → Web Service → Connect repo
3. **Settings**:
   - Root Directory: `prepsensei`
   - Docker → Dockerfile Path: `./backend/Dockerfile`
4. **Environment Variables**:
   - `DEEPSEEK_API_KEY`: 你的 API Key
   - `VERCEL_URL`: 前端部署后的 Vercel URL
   - `MAX_LLM_CALLS_PER_SESSION`: `50`

或使用 `render.yaml` 一键配置：
```bash
# 在 Render Dashboard 中选择 "Blueprint" 导入 render.yaml
```

### 前端 → Vercel

1. Vercel Dashboard → Import Git Repository
2. **Framework**: Next.js
3. **Root Directory**: `prepsensei/frontend`
4. **Environment Variables**:
   - `NEXT_PUBLIC_BACKEND_URL`: `https://your-app.onrender.com`

> **重要**: EventSource 直连后端 URL，不通过 Vercel `/api/` 路由代理
> （Vercel 会缓冲 SSE 导致流式输出失效）

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/session` | 创建面试会话，返回 session_id |
| POST | `/api/session/{id}/resume` | 上传 PDF 简历（multipart/form-data） |
| POST | `/api/session/{id}/jd` | 提交岗位 JD 文本 |
| POST | `/api/session/{id}/start` | 生成面试模块并开始面试 |
| POST | `/api/session/{id}/answer` | 提交用户回答，触发 Agent 步骤 |
| GET | `/api/interview/stream` | SSE 流式获取事件（?session_id=&cursor=） |
| GET | `/healthz` | 健康检查 |

## 项目结构

```
prepsensei/
├── backend/
│   ├── main.py              # FastAPI 应用入口 + lifespan
│   ├── routes.py            # API 路由（含 SSE endpoint）
│   ├── agent.py             # 面试官 Agent 核心循环
│   ├── tools.py             # Function Calling 工具定义
│   ├── rag.py               # RAG 系统（ChromaDB in-memory）
│   ├── evaluator.py         # 评分与报告格式化
│   ├── session_store.py     # 会话状态 + asyncio.Lock + 定时清理
│   ├── deepseek_client.py   # DeepSeek API 封装
│   ├── parser.py            # PDF 解析 + JD 关键词提取
│   ├── schemas.py           # Pydantic 数据模型
│   ├── data/
│   │   └── question_bank.json   # 面试题库（80+ 题，5 个主题）
│   ├── tests/
│   │   ├── test_parser.py
│   │   ├── test_rag.py
│   │   └── test_agent_loop.py
│   ├── docs/
│   │   └── agent-walkthrough.md
│   ├── scripts/
│   │   └── validate_question_bank.py
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                      # 首页（上传简历 + JD）
│   │   ├── interview/[sessionId]/page.tsx # 面试对话页
│   │   └── report/[sessionId]/page.tsx   # 评分报告页
│   ├── components/
│   │   ├── ChatMessage.tsx               # 对话气泡组件
│   │   └── ToolCallTrace.tsx             # Agent 工具调用可视化
│   ├── lib/
│   │   ├── api.ts                        # 后端 API 调用封装
│   │   └── sseClient.ts                  # Cursor-based SSE 客户端
│   ├── vercel.json
│   └── package.json
├── render.yaml              # Render 部署配置
└── README.md
```

## 关键技术决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 向量库 | ChromaDB in-memory | Render 免费层磁盘为 ephemeral，PersistentClient 重启数据丢失 |
| Embedding | DeepSeek embeddings API | sentence-transformers 模型 ~470MB，超出 Render 512MB RAM |
| SSE | Cursor-based 事件列表 | asyncio.Queue 断线重连后丢失未消费事件 |
| 限流 | ProxyHeadersMiddleware 优先 | 必须在 CORSMiddleware 前添加，否则读取 Render 内部 IP |
| Agent | 手写循环（不用 LangChain） | 展示对 Function Calling 底层原理的掌握 |

## 简历亮点写法

```
PrepSensei — AI 个性化面试模拟 Agent                    [GitHub] [Demo]
• 基于 RAG + DeepSeek function calling 构建多轮面试对话 Agent
• 三路知识融合：简历解析 + JD 要求提取 + 行业题库 RAG 检索
• Agent 自主决策追问逻辑：分析用户回答后选择深挖或推进（ReAct 框架落地）
• Cursor-based SSE 流式输出，断线自动重连；asyncio.Lock 防并发竞态
• 云端部署（Render + Vercel），支持简历直接附链接在线体验
```

## License

MIT
