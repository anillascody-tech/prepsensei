import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import chromadb
from rag import RAGSystem, DeepSeekEmbeddingFunction
from deepseek_client import DeepSeekClient

MOCK_EMBEDDING = [0.1] * 1536  # fake 1536-dim vector

def make_mock_client():
    client = MagicMock(spec=DeepSeekClient)
    client.embed = AsyncMock(return_value=[MOCK_EMBEDDING])
    return client

def test_seed_and_retrieve():
    mock_client = make_mock_client()
    # Patch the embedding function to return deterministic vectors
    with patch.object(DeepSeekEmbeddingFunction, '__call__', return_value=[MOCK_EMBEDDING]):
        rag = RAGSystem(mock_client)
        questions = [
            {"id": "q001", "topic": "RAG系统理解", "question": "什么是RAG?", "difficulty": "easy", "answer_guide": "RAG combines retrieval with generation"},
            {"id": "q002", "topic": "RAG系统理解", "question": "向量数据库如何工作?", "difficulty": "medium", "answer_guide": "Vector DB stores embeddings for similarity search"},
        ]
        rag.seed_question_bank(questions)
        # Should not raise
        results = rag.retrieve_questions("session1", "RAG系统理解", n_results=2)
        assert isinstance(results, list)

def test_cleanup_session():
    with patch.object(DeepSeekEmbeddingFunction, '__call__', return_value=[MOCK_EMBEDDING]):
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
