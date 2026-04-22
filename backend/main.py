import asyncio
import json
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from routes import router
from session_store import session_store

limiter = Limiter(key_func=get_remote_address)

async def purge_loop():
    while True:
        await asyncio.sleep(600)  # 10 minutes
        purged = session_store.purge_expired()
        if purged:
            print(f"[purge] Removed {purged} expired sessions")

_purge_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _purge_task
    # Seed question bank (will be called after RAG module exists)
    try:
        from rag import rag_system
        qb_path = os.path.join(os.path.dirname(__file__), "data", "question_bank.json")
        if os.path.exists(qb_path):
            with open(qb_path, "r", encoding="utf-8") as f:
                questions = json.load(f)
            rag_system.seed_question_bank(questions)
            print(f"[startup] Seeded {len(questions)} questions into ChromaDB")
    except ImportError:
        print("[startup] RAG module not yet available, skipping seed")

    _purge_task = asyncio.create_task(purge_loop())
    print("[startup] Background purge task started")

    yield

    if _purge_task:
        _purge_task.cancel()
        try:
            await _purge_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="PrepSensei API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# IMPORTANT: ProxyHeadersMiddleware MUST be added BEFORE CORSMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

VERCEL_URL = os.environ.get("VERCEL_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[VERCEL_URL, "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
