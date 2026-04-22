import pytest
from parser import parse_pdf, extract_jd_keywords

def test_extract_jd_keywords_finds_python():
    jd = "Requirements: Python, RAG experience, LLM API integration"
    result = extract_jd_keywords(jd)
    assert result["keywords_count"] > 0
    assert any("Python" in s or "python" in s.lower() for s in result["skills_mentioned"])

def test_extract_jd_keywords_empty():
    result = extract_jd_keywords("We are looking for a great team player.")
    assert result["raw_length"] > 0
    assert isinstance(result["keywords_count"], int)

def test_parse_pdf_invalid_raises():
    import pytest
    with pytest.raises(Exception):
        parse_pdf(b"not a pdf")
