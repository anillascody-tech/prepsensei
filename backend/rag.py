import asyncio
from typing import List
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings

from deepseek_client import DeepSeekClient, deepseek_client as _default_client


class DeepSeekEmbeddingFunction(EmbeddingFunction):
    """ChromaDB-compatible embedding function using DeepSeek API."""

    def __init__(self, client: DeepSeekClient = None):
        self._client = client or _default_client

    def __call__(self, input: Documents) -> Embeddings:
        """Synchronous wrapper — ChromaDB calls this synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context, use run_in_executor workaround
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._client.embed(list(input)))
                    return future.result()
            else:
                return loop.run_until_complete(self._client.embed(list(input)))
        except RuntimeError:
            return asyncio.run(self._client.embed(list(input)))


class RAGSystem:
    def __init__(self, client: DeepSeekClient = None):
        self._chroma = chromadb.Client()  # in-memory, NOT PersistentClient
        self._embed_fn = DeepSeekEmbeddingFunction(client)
        self._qb_collection = None

    def seed_question_bank(self, questions: list[dict]):
        """Load question bank into ChromaDB. Called on startup."""
        try:
            self._chroma.delete_collection("question_bank")
        except Exception:
            pass

        collection = self._chroma.create_collection(
            name="question_bank",
            embedding_function=self._embed_fn
        )

        if not questions:
            return

        ids = [q["id"] for q in questions]
        documents = [f"{q['topic']}: {q['question']}" for q in questions]
        metadatas = [{"topic": q["topic"], "difficulty": q.get("difficulty", "medium"),
                      "answer_guide": q.get("answer_guide", ""), "question": q["question"]}
                     for q in questions]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        self._qb_collection = collection

    def index_resume(self, session_id: str, resume_text: str):
        """Chunk and index resume text for a session."""
        try:
            self._chroma.delete_collection(f"resume_{session_id}")
        except Exception:
            pass

        collection = self._chroma.create_collection(
            name=f"resume_{session_id}",
            embedding_function=self._embed_fn
        )

        # Chunk by paragraphs
        paragraphs = [p.strip() for p in resume_text.split("\n\n") if len(p.strip()) > 20]
        if not paragraphs:
            paragraphs = [resume_text[:500]]

        ids = [f"resume_{session_id}_chunk_{i}" for i in range(len(paragraphs))]
        collection.add(ids=ids, documents=paragraphs)

    def index_jd(self, session_id: str, jd_text: str):
        """Index JD text for a session."""
        try:
            self._chroma.delete_collection(f"jd_{session_id}")
        except Exception:
            pass

        collection = self._chroma.create_collection(
            name=f"jd_{session_id}",
            embedding_function=self._embed_fn
        )

        chunks = [p.strip() for p in jd_text.split("\n\n") if len(p.strip()) > 10]
        if not chunks:
            chunks = [jd_text[:500]]

        ids = [f"jd_{session_id}_chunk_{i}" for i in range(len(chunks))]
        collection.add(ids=ids, documents=chunks)

    def retrieve_questions(self, session_id: str, topic: str, n_results: int = 5) -> list[dict]:
        """Retrieve relevant questions from question bank for a topic."""
        if self._qb_collection is None:
            # Try to get existing collection
            try:
                self._qb_collection = self._chroma.get_collection(
                    "question_bank", embedding_function=self._embed_fn
                )
            except Exception:
                return []

        try:
            results = self._qb_collection.query(
                query_texts=[topic],
                n_results=min(n_results, self._qb_collection.count()),
                where={"topic": topic} if topic else None
            )
        except Exception:
            # Fallback: query without topic filter
            try:
                results = self._qb_collection.query(
                    query_texts=[topic],
                    n_results=min(n_results, self._qb_collection.count())
                )
            except Exception:
                return []

        questions = []
        if results and results.get("metadatas"):
            for meta in results["metadatas"][0]:
                questions.append({
                    "topic": meta.get("topic", ""),
                    "question": meta.get("question", ""),
                    "difficulty": meta.get("difficulty", "medium"),
                    "answer_guide": meta.get("answer_guide", "")
                })
        return questions

    def cleanup_session(self, session_id: str):
        """Remove session-specific collections."""
        for name in [f"resume_{session_id}", f"jd_{session_id}"]:
            try:
                self._chroma.delete_collection(name)
            except Exception:
                pass

rag_system = RAGSystem()
