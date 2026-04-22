from pydantic import BaseModel
from typing import Optional, Any

class SessionCreateResponse(BaseModel):
    session_id: str

class ResumeUploadResponse(BaseModel):
    session_id: str
    text_length: int

class JDSubmitRequest(BaseModel):
    jd_text: str

class JDSubmitResponse(BaseModel):
    session_id: str
    keywords_extracted: int

class StartInterviewResponse(BaseModel):
    session_id: str
    modules: list[dict]

class AnswerRequest(BaseModel):
    answer: str

class AnswerResponse(BaseModel):
    events_added: int

class SSEEvent(BaseModel):
    type: str  # "assistant_text" | "tool_call" | "tool_result" | "module_complete" | "interview_complete"
    content: Optional[str] = None
    data: Optional[dict] = None
    cursor: int  # index of this event in events_history
