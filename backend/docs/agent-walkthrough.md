# Agent 决策循环说明

PrepSensei 的核心是一个基于 DeepSeek Function Calling 的面试官 Agent。

## 工作流程

1. **初始化** — 用户上传简历和 JD 后，Agent 调用 DeepSeek 生成 5 个个性化面试模块，每个模块有定制化的初始问题。

2. **面试循环** — 用户每次提交回答后，`agent.step()` 被调用：
   - Agent 首先调用 `retrieve_questions` 工具，从 ChromaDB 题库中检索当前模块相关题目
   - DeepSeek 基于检索结果和用户简历生成面试问题
   - 用户回答后，Agent 调用 `evaluate_and_route` 工具评估回答质量
   - **动态决策**：若回答不够深入且未超过 2 次追问上限，Agent 生成追问；否则进入下一模块

3. **工具调用可视化** — 每次工具调用都作为 SSE 事件推送到前端，用户可以看到 Agent 的"思考过程"（使用了哪个工具、传了什么参数、得到了什么结果）

4. **报告生成** — 5 个模块全部完成后，Agent 调用 `generate_report` 工具，生成包含各模块评分和改进建议的结构化报告

## 技术亮点

- **手写 Agent 循环**（~150 LOC）：不依赖 LangChain，展示对底层原理的掌握
- **Cursor-based SSE**：断线后可从上次位置恢复，不丢失任何事件
- **asyncio.Lock**：防止并发请求导致的状态竞争
