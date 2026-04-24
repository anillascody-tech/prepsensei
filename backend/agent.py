import asyncio
import json
import os
from typing import TYPE_CHECKING

from tools import TOOLS_SCHEMA
from evaluator import score_answer, format_report

if TYPE_CHECKING:
    from deepseek_client import DeepSeekClient
    from rag import RAGSystem
    from session_store import SessionStore

MAX_LLM_CALLS = int(os.environ.get("MAX_LLM_CALLS_PER_SESSION", "50"))


class LLMCallLimitExceeded(Exception):
    pass


class InterviewAgent:
    def __init__(self, session_id: str, deepseek_client, rag_system, session_store):
        self.session_id = session_id
        self.client = deepseek_client
        self.rag = rag_system
        self.store = session_store

    async def generate_modules(self, resume_text: str, jd_text: str) -> list[dict]:
        """Generate 5 personalized interview modules based on resume + JD."""
        prompt = f"""你是一位专业的 AI 工程师面试官。请根据以下候选人简历和岗位描述，生成 5 个面试模块。

简历内容:
{resume_text[:2000]}

岗位描述:
{jd_text[:1500]}

请生成 JSON 格式的 5 个面试模块，每个模块包含：
- topic: 模块主题（从以下选择或调整：自我介绍与项目经历、RAG系统理解、Agent与工具调用、场景设计题、岗位匹配度）
- initial_question: 该模块的第一个问题（根据简历和JD个性化定制）
- description: 模块简短描述

只返回 JSON 数组，不要其他内容。格式：
[{{"topic": "...", "initial_question": "...", "description": "..."}}]"""

        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content
        # Parse JSON from response
        try:
            # Find JSON array in response
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                modules = json.loads(content[start:end])
            else:
                modules = json.loads(content)
        except Exception:
            # Fallback to default modules
            modules = [
                {"topic": "自我介绍与项目经历", "initial_question": "请介绍一下你自己和你最近做的项目。", "description": "了解候选人背景"},
                {"topic": "RAG系统理解", "initial_question": "你了解 RAG 技术吗？请介绍一下。", "description": "技术深度考察"},
                {"topic": "Agent与工具调用", "initial_question": "请解释一下 AI Agent 的工作原理。", "description": "Agent 架构理解"},
                {"topic": "场景设计题", "initial_question": "如果让你设计一个企业知识库问答系统，你会怎么做？", "description": "系统设计能力"},
                {"topic": "岗位匹配度", "initial_question": "你为什么想做 AI 应用工程师？", "description": "匹配度评估"},
            ]

        return modules[:5]  # Ensure exactly 5 modules

    async def _dispatch_tool(self, tool_name: str, tool_args: dict) -> str:
        """Dispatch a tool call and return the result as string."""
        session = self.store.get(self.session_id)

        if tool_name == "retrieve_questions":
            topic = tool_args.get("topic", "")
            n_results = tool_args.get("n_results", 5)
            questions = self.rag.retrieve_questions(self.session_id, topic, n_results)
            resume_ctx = self.rag.retrieve_resume_context(self.session_id, topic, n=2)
            jd_ctx = self.rag.retrieve_jd_context(self.session_id, topic, n=2)
            result = {
                "questions": questions,
                "resume_context": [{"section": r["section"], "text": r["text"]} for r in resume_ctx],
                "jd_context": [{"section": r["section"], "text": r["text"]} for r in jd_ctx],
            }
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "evaluate_and_route":
            answer = tool_args.get("answer", "")
            question = tool_args.get("question", "")
            followup_count = tool_args.get("followup_count", 0)
            max_followups = tool_args.get("max_followups", 2)

            # If already at max followups, force next_module
            if followup_count >= max_followups:
                return json.dumps({
                    "action": "next_module",
                    "followup_question": None,
                    "reason": "已达到最大追问次数，进入下一模块"
                }, ensure_ascii=False)

            # Use DeepSeek to evaluate
            eval_prompt = f"""评估以下面试回答，决定是否需要追问。

问题：{question}
回答：{answer}
已追问次数：{followup_count}/{max_followups}

如果回答不够深入或有重要点未覆盖，且未达到追问上限，返回 followup。
否则返回 next_module。

只返回 JSON：{{"action": "followup"/"next_module", "followup_question": "追问问题或null", "reason": "理由"}}"""

            eval_response = await self.client.chat_completion(
                messages=[{"role": "user", "content": eval_prompt}]
            )

            content = eval_response.choices[0].message.content
            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                result = json.loads(content[start:end])
                return json.dumps(result, ensure_ascii=False)
            except Exception:
                return json.dumps({
                    "action": "next_module",
                    "followup_question": None,
                    "reason": "评估完成"
                }, ensure_ascii=False)

        elif tool_name == "generate_report":
            modules_data = tool_args.get("modules_data", [])
            # Score each module
            for module in modules_data:
                answers = module.get("answers", [])
                questions = module.get("questions", [])
                if answers and questions:
                    score_data = score_answer(
                        questions[0] if questions else "",
                        " ".join(answers),
                        module.get("topic", "")
                    )
                    module.update(score_data)

            report = format_report(modules_data)
            return report

        return f"Unknown tool: {tool_name}"

    async def step(self, session_id: str, user_answer: str) -> list[dict]:
        """
        Core agent loop iteration.
        - Acquires session lock
        - Appends user answer to events_history
        - Calls DeepSeek with function calling
        - Dispatches tool calls
        - Loops until no more tool_calls
        - Returns new SSEEvent dicts
        """
        session = self.store.get(session_id)
        if not session:
            return []

        new_events = []

        async with session.lock:
            # Check LLM call limit
            if session.llm_call_count >= MAX_LLM_CALLS:
                raise LLMCallLimitExceeded(f"Session {session_id} exceeded {MAX_LLM_CALLS} LLM calls")

            # Append user event
            user_event = {"type": "user_answer", "content": user_answer}
            session.events_history.append(user_event)
            new_events.append(user_event)

            # Build message history for the agent
            # Reconstruct conversation from events_history
            messages = [
                {
                    "role": "system",
                    "content": """你是 PrepSensei，一个专业的 AI 面试模拟官。
你的职责：主持面试，使用工具检索合适题目、评估回答、决定追问或进入下一模块。
面试共 5 个模块，每模块最多追问 2 次。
请用中文进行面试，保持专业友好的语气。
使用 retrieve_questions 工具获取相关题目，使用 evaluate_and_route 决定是否追问，全部模块完成后使用 generate_report 生成报告。"""
                }
            ]

            # Add conversation history from events
            for event in session.events_history[:-1]:  # exclude the just-added user event
                if event["type"] == "user_answer":
                    messages.append({"role": "user", "content": event["content"]})
                elif event["type"] == "assistant_text":
                    messages.append({"role": "assistant", "content": event["content"]})

            # Add current user message
            messages.append({"role": "user", "content": user_answer})

            # Agent loop — run until no more tool calls
            loop_count = 0
            max_loop = 10  # safety limit per step

            while loop_count < max_loop:
                session.llm_call_count += 1
                if session.llm_call_count > MAX_LLM_CALLS:
                    raise LLMCallLimitExceeded(f"Exceeded {MAX_LLM_CALLS} LLM calls")

                response = await self.client.chat_completion(
                    messages=messages,
                    tools=TOOLS_SCHEMA
                )

                response_msg = response.choices[0].message

                # IMPORTANT: Handle content FIRST, then tool_calls
                if response_msg.content:
                    text_event = {"type": "assistant_text", "content": response_msg.content}
                    session.events_history.append(text_event)
                    new_events.append(text_event)
                    messages.append({"role": "assistant", "content": response_msg.content})

                if not response_msg.tool_calls:
                    break  # No more tool calls — done

                # Dispatch tool calls IN ORDER
                tool_results_for_messages = []
                for tc in response_msg.tool_calls:
                    tool_name = tc.function.name
                    tool_args = json.loads(tc.function.arguments)

                    # Emit tool_call event (visible in frontend ToolCallTrace)
                    call_event = {
                        "type": "tool_call",
                        "data": {
                            "tool_name": tool_name,
                            "args": tool_args,
                            "tool_call_id": tc.id
                        }
                    }
                    session.events_history.append(call_event)
                    new_events.append(call_event)

                    # Execute tool
                    result = await self._dispatch_tool(tool_name, tool_args)

                    # Emit tool_result event
                    result_event = {
                        "type": "tool_result",
                        "data": {
                            "tool_name": tool_name,
                            "tool_call_id": tc.id,
                            "result": result[:500]  # truncate for SSE
                        }
                    }
                    session.events_history.append(result_event)
                    new_events.append(result_event)

                    # If generate_report was called, emit interview_complete
                    if tool_name == "generate_report":
                        complete_event = {
                            "type": "interview_complete",
                            "content": result
                        }
                        session.events_history.append(complete_event)
                        new_events.append(complete_event)

                    tool_results_for_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                    })

                # Add assistant message with tool_calls to history
                messages.append({
                    "role": "assistant",
                    "content": response_msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in response_msg.tool_calls
                    ]
                })

                # Add tool results to messages
                messages.extend(tool_results_for_messages)
                loop_count += 1

        return new_events
