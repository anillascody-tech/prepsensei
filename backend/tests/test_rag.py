import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import chromadb
from rag import RAGSystem, DeepSeekEmbeddingFunction
from deepseek_client import DeepSeekClient

MOCK_EMBEDDING = [0.1] * 1536  # fake 1536-dim vector


def _mock_embed_call(self, input):
    """Properly-typed replacement for DeepSeekEmbeddingFunction.__call__.

    patch.object with return_value= creates a MagicMock(*args,**kwargs) which
    fails ChromaDB's signature validation. This function has the correct
    signature (self, input) so ChromaDB accepts it.
    """
    return [MOCK_EMBEDDING] * len(input)


def make_mock_client():
    client = MagicMock(spec=DeepSeekClient)
    client.embed = AsyncMock(return_value=[MOCK_EMBEDDING])
    return client


def test_seed_and_retrieve():
    mock_client = make_mock_client()
    with patch.object(DeepSeekEmbeddingFunction, '__call__', _mock_embed_call):
        rag = RAGSystem(mock_client)
        questions = [
            {"id": "q001", "topic": "RAG系统理解", "question": "什么是RAG?", "difficulty": "easy", "answer_guide": "RAG combines retrieval with generation"},
            {"id": "q002", "topic": "RAG系统理解", "question": "向量数据库如何工作?", "difficulty": "medium", "answer_guide": "Vector DB stores embeddings for similarity search"},
        ]
        rag.seed_question_bank(questions)
        results = rag.retrieve_questions("session1", "RAG系统理解", n_results=2)
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)


def test_cleanup_session():
    with patch.object(DeepSeekEmbeddingFunction, '__call__', _mock_embed_call):
        mock_client = make_mock_client()
        rag = RAGSystem(mock_client)
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
    with patch.object(DeepSeekEmbeddingFunction, '__call__', _mock_embed_call):
        mock_client = make_mock_client()
        rag = RAGSystem(mock_client)
        resume = "Python developer with RAG experience\n\nSkills: Python, FastAPI, ChromaDB\n\nWorked at Acme Corp on NLP projects"
        rag.index_resume("s1", resume)
        col = rag._chroma.get_collection("resume_s1", embedding_function=rag._embed_fn)
        all_docs = col.get(include=["metadatas"])
        chunk_types = {m["chunk_type"] for m in all_docs["metadatas"]}
        assert "parent" in chunk_types
        assert "child" in chunk_types


def test_retrieve_resume_context():
    """retrieve_resume_context returns parent-level text chunks."""
    with patch.object(DeepSeekEmbeddingFunction, '__call__', _mock_embed_call):
        mock_client = make_mock_client()
        rag = RAGSystem(mock_client)
        rag.index_resume("s2", "Python developer\n\nSkills: RAG, embeddings, vector search")
        results = rag.retrieve_resume_context("s2", "RAG experience", n=2)
        assert isinstance(results, list)
        for r in results:
            assert "text" in r
            assert "section" in r
