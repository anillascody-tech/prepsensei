import asyncio
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class InterviewSession:
    id: str
    resume_text: str = ""
    jd_text: str = ""
    modules: list = field(default_factory=list)
    events_history: list = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    llm_call_count: int = 0

class SessionStore:
    def __init__(self):
        self._sessions: dict[str, InterviewSession] = {}

    def create(self) -> InterviewSession:
        session_id = str(uuid.uuid4())
        session = InterviewSession(id=session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[InterviewSession]:
        session = self._sessions.get(session_id)
        if session:
            session.last_active = datetime.utcnow()
        return session

    def delete(self, session_id: str):
        self._sessions.pop(session_id, None)

    def purge_expired(self, ttl_hours: int = 1):
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        expired = [sid for sid, s in self._sessions.items() if s.last_active < cutoff]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

session_store = SessionStore()
