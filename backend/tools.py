from typing import Any

# OpenAI-compatible tool schemas for DeepSeek function calling
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_questions",
            "description": "从题库中检索与当前面试模块相关的问题，用于生成有针对性的面试问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "面试模块主题，如'RAG系统理解'、'Agent与工具调用'等"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "当前会话ID"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "需要检索的问题数量，默认5",
                        "default": 5
                    }
                },
                "required": ["topic", "session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_and_route",
            "description": "评估用户的回答质量，决定是追问还是进入下一个面试模块",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "用户的回答内容"
                    },
                    "question": {
                        "type": "string",
                        "description": "刚才提问的问题"
                    },
                    "followup_count": {
                        "type": "integer",
                        "description": "当前模块已追问次数"
                    },
                    "max_followups": {
                        "type": "integer",
                        "description": "最大追问次数限制",
                        "default": 2
                    }
                },
                "required": ["answer", "question", "followup_count"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "所有面试模块结束后，生成完整的结构化评估报告",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "当前会话ID"
                    },
                    "modules_data": {
                        "type": "array",
                        "description": "每个面试模块的问答记录和评分数据",
                        "items": {
                            "type": "object",
                            "properties": {
                                "topic": {"type": "string"},
                                "questions": {"type": "array"},
                                "answers": {"type": "array"},
                                "score": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["session_id", "modules_data"]
            }
        }
    }
]

def get_tool_names() -> list[str]:
    return [t["function"]["name"] for t in TOOLS_SCHEMA]
