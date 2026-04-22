import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

@pytest.fixture
def mock_session():
    from session_store import InterviewSession
    session = InterviewSession(id="test_session_001")
    return session

@pytest.fixture
def mock_store(mock_session):
    store = MagicMock()
    store.get.return_value = mock_session
    return store

@pytest.fixture
def mock_rag():
    rag = MagicMock()
    rag.retrieve_questions.return_value = [
        {"topic": "RAG系统理解", "question": "什么是RAG?", "difficulty": "easy", "answer_guide": "..."}
    ]
    return rag

@pytest.fixture
def mock_deepseek():
    client = MagicMock()
    # Default: return text response, no tool calls
    msg = MagicMock()
    msg.content = "好的，请介绍一下你的项目经历。"
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    client.chat_completion = AsyncMock(return_value=response)
    return client

@pytest.mark.asyncio
async def test_step_appends_user_event(mock_deepseek, mock_rag, mock_store, mock_session):
    from agent import InterviewAgent
    agent = InterviewAgent("test_session_001", mock_deepseek, mock_rag, mock_store)
    events = await agent.step("test_session_001", "我做过一个RAG项目")

    assert any(e["type"] == "user_answer" for e in events)
    assert any(e["type"] == "assistant_text" for e in events)

@pytest.mark.asyncio
async def test_step_dispatches_tool_call(mock_rag, mock_store, mock_session):
    from agent import InterviewAgent
    from deepseek_client import DeepSeekClient

    client = MagicMock()

    # First call: return tool_call
    tool_call = MagicMock()
    tool_call.id = "call_001"
    tool_call.function.name = "retrieve_questions"
    tool_call.function.arguments = json.dumps({"topic": "RAG系统理解", "session_id": "test_session_001"})

    msg1 = MagicMock()
    msg1.content = None
    msg1.tool_calls = [tool_call]
    resp1 = MagicMock()
    resp1.choices = [MagicMock(message=msg1)]

    # Second call: return text (no more tool calls)
    msg2 = MagicMock()
    msg2.content = "根据题库，我来问你第一个问题..."
    msg2.tool_calls = None
    resp2 = MagicMock()
    resp2.choices = [MagicMock(message=msg2)]

    client.chat_completion = AsyncMock(side_effect=[resp1, resp2])

    agent = InterviewAgent("test_session_001", client, mock_rag, mock_store)
    events = await agent.step("test_session_001", "开始面试")

    assert any(e["type"] == "tool_call" for e in events)
    assert any(e["type"] == "tool_result" for e in events)

@pytest.mark.asyncio
async def test_llm_call_limit_exceeded(mock_deepseek, mock_rag, mock_store, mock_session):
    from agent import InterviewAgent, LLMCallLimitExceeded

    mock_session.llm_call_count = 49  # One call will push it over 50

    # Make DeepSeek always return tool calls to trigger loop
    tool_call = MagicMock()
    tool_call.id = "call_x"
    tool_call.function.name = "retrieve_questions"
    tool_call.function.arguments = json.dumps({"topic": "test", "session_id": "test_session_001"})
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tool_call]
    resp = MagicMock()
    resp.choices = [MagicMock(message=msg)]
    mock_deepseek.chat_completion = AsyncMock(return_value=resp)

    agent = InterviewAgent("test_session_001", mock_deepseek, mock_rag, mock_store)

    with pytest.raises(LLMCallLimitExceeded):
        await agent.step("test_session_001", "test")

@pytest.mark.asyncio
async def test_generate_modules_returns_five(mock_store):
    from agent import InterviewAgent

    client = MagicMock()
    msg = MagicMock()
    msg.content = json.dumps([
        {"topic": "自我介绍", "initial_question": "Q1", "description": "D1"},
        {"topic": "RAG", "initial_question": "Q2", "description": "D2"},
        {"topic": "Agent", "initial_question": "Q3", "description": "D3"},
        {"topic": "场景设计", "initial_question": "Q4", "description": "D4"},
        {"topic": "岗位匹配", "initial_question": "Q5", "description": "D5"},
    ])
    msg.tool_calls = None
    resp = MagicMock()
    resp.choices = [MagicMock(message=msg)]
    client.chat_completion = AsyncMock(return_value=resp)

    rag = MagicMock()
    agent = InterviewAgent("s1", client, rag, mock_store)
    modules = await agent.generate_modules("Resume text here", "JD text here")

    assert len(modules) == 5
    assert all("topic" in m and "initial_question" in m for m in modules)
