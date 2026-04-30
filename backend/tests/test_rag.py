import pytest
from chromadb import EmbeddingFunction, Documents, Embeddings
from rag import RAGSystem

MOCK_EMBEDDING = [0.1] * 384  # all-MiniLM-L6-v2 produces 384-dim vectors


class MockEmbeddingFunction(EmbeddingFunction):
    """Deterministic fake embedding — no torch, no network, no disk I/O."""

    def __call__(self, input: Documents) -> Embeddings:
        return [MOCK_EMBEDDING] * len(input)


def make_rag() -> RAGSystem:
    return RAGSystem(embed_fn=MockEmbeddingFunction())


def test_seed_and_retrieve():
    rag = make_rag()
    questions = [
        {"id": "q001", "topic": "RAG系统理解", "question": "什么是RAG?", "difficulty": "easy", "answer_guide": "RAG combines retrieval with generation"},
        {"id": "q002", "topic": "RAG系统理解", "question": "向量数据库如何工作?", "difficulty": "medium", "answer_guide": "Vector DB stores embeddings for similarity search"},
    ]
    rag.seed_question_bank(questions)
    results = rag.retrieve_questions("session1", "RAG系统理解", n_results=2)
    assert isinstance(results, list)
    assert all(isinstance(r, dict) for r in results)


def test_cleanup_session():
    rag = make_rag()
    rag.index_resume("test_session", "Python developer with 3 years experience\n\nWorked on RAG systems")
    rag.index_jd("test_session", "We need a Python developer experienced in RAG")
    # Verify collections exist
    names = [c.name for c in rag._chroma.list_collections()]
    assert "resume_test_session" in names
    assert "jd_test_session" in names
    # Cleanup
    rag.cleanup_session("test_session")
    names_after = [c.name for c in rag._chroma.list_collections()]
    assert "resume_test_session" not in names_after
    assert "jd_test_session" not in names_after


def test_parent_child_chunks_indexed():
    """Parent and child chunks are both stored with correct metadata."""
    rag = make_rag()
    resume = "Python developer with RAG experience\n\nSkills: Python, FastAPI, ChromaDB\n\nWorked at Acme Corp on NLP projects"
    rag.index_resume("s1", resume)
    col = rag._chroma.get_collection("resume_s1", embedding_function=rag._embed_fn)
    all_docs = col.get(include=["metadatas"])
    chunk_types = {m["chunk_type"] for m in all_docs["metadatas"]}
    assert "parent" in chunk_types
    assert "child" in chunk_types


def test_retrieve_resume_context():
    """retrieve_resume_context returns parent-level text chunks."""
    rag = make_rag()
    rag.index_resume("s2", "Python developer\n\nSkills: RAG, embeddings, vector search")
    results = rag.retrieve_resume_context("s2", "RAG experience", n=2)
    assert isinstance(results, list)
    for r in results:
        assert "text" in r
        assert "section" in r
