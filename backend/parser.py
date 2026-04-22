import io
import re
from PyPDF2 import PdfReader

def parse_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            texts.append(text.strip())
    return "\n\n".join(texts)

def extract_jd_keywords(jd_text: str) -> dict:
    """Extract key requirements from JD text."""
    # Simple keyword extraction — look for skills, requirements sections
    skills = []
    lines = jd_text.split("\n")
    for line in lines:
        line = line.strip()
        if any(kw in line.lower() for kw in ["python", "rag", "agent", "llm", "langchain", "fastapi", "react", "sql", "docker", "kubernetes", "aws", "gpt", "embedding"]):
            skills.append(line[:100])
    return {
        "raw_length": len(jd_text),
        "skills_mentioned": skills[:20],
        "keywords_count": len(skills)
    }
