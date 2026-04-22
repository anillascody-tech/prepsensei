import asyncio
import json
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from schemas import (
    SessionCreateResponse, ResumeUploadResponse,
    JDSubmitRequest, JDSubmitResponse,
    StartInterviewResponse, AnswerRequest, AnswerResponse,
)
from session_store import session_store
from parser import parse_pdf, extract_jd_keywords

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/api/session", response_model=SessionCreateResponse)
async def create_session(request: Request):
    session = session_store.create()
    return SessionCreateResponse(session_id=session.id)

@router.post("/api/session/{session_id}/resume", response_model=ResumeUploadResponse)
async def upload_resume(session_id: str, file: UploadFile = File(...)):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    async with session.lock:
        session.resume_text = parse_pdf(content)

    return ResumeUploadResponse(session_id=session_id, text_length=len(session.resume_text))

@router.post("/api/session/{session_id}/jd", response_model=JDSubmitResponse)
async def submit_jd(session_id: str, body: JDSubmitRequest):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    keywords = extract_jd_keywords(body.jd_text)
    async with session.lock:
        session.jd_text = body.jd_text

    return JDSubmitResponse(session_id=session_id, keywords_extracted=keywords["keywords_count"])

@router.post("/api/session/{session_id}/start", response_model=StartInterviewResponse)
@limiter.limit("10/hour")
async def start_interview(session_id: str, request: Request):
    from agent import InterviewAgent
    from rag import rag_system
    from deepseek_client import deepseek_client

    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.resume_text or not session.jd_text:
        raise HTTPException(status_code=400, detail="Resume and JD required before starting")

    agent = InterviewAgent(session_id, deepseek_client, rag_system, session_store)
    modules = await agent.generate_modules(session.resume_text, session.jd_text)
    async with session.lock:
        session.modules = modules
        if modules:
            first_q = modules[0].get("initial_question", "请开始自我介绍。")
            session.events_history.append({"type": "assistant_text", "content": first_q})

    return StartInterviewResponse(session_id=session_id, modules=modules)


@router.post("/api/session/{session_id}/answer", response_model=AnswerResponse)
async def submit_answer(session_id: str, body: AnswerRequest):
    from agent import InterviewAgent, LLMCallLimitExceeded
    from rag import rag_system
    from deepseek_client import deepseek_client

    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        agent = InterviewAgent(session_id, deepseek_client, rag_system, session_store)
        new_events = await agent.step(session_id, body.answer)
        return AnswerResponse(events_added=len(new_events))
    except LLMCallLimitExceeded:
        raise HTTPException(status_code=429, detail="Session LLM call limit exceeded")


@router.get("/api/interview/stream")
async def stream_events(session_id: str, cursor: int = 0):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        current_cursor = cursor
        max_polls = 3000  # ~5 min at 0.1s
        polls = 0
        while polls < max_polls:
            events = session.events_history
            if current_cursor < len(events):
                for i in range(current_cursor, len(events)):
                    payload = {**events[i], "cursor": i}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                current_cursor = len(events)
                if any(e.get("type") == "interview_complete" for e in events):
                    break
            await asyncio.sleep(0.1)
            polls += 1

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}
