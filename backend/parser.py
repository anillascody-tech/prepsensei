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

def detect_section(text: str, doc_type: str = "resume") -> str:
    """Detect which section a text chunk belongs to."""
    t = text.lower()
    if doc_type == "resume":
        if any(k in t for k in ["教育", "学历", "university", "bachelor", "master", "degree", "college", "school", "gpa"]):
            return "education"
        if any(k in t for k in ["技能", "skill", "熟悉", "掌握", "proficient", "python", "java", "react", "docker", "kubernetes", "sql", "git"]):
            return "skills"
        if any(k in t for k in ["项目", "project", "github", "开发了", "实现了", "负责", "designed", "built", "implemented"]):
            return "projects"
        if any(k in t for k in ["工作", "实习", "intern", "experience", "employment", "company", "corp", "inc", "ltd", "年", "月 -", "present"]):
            return "experience"
        return "summary"
    else:  # jd
        if any(k in t for k in ["优先", "加分", "nice to have", "preferred", "bonus", "plus"]):
            return "nice_to_have"
        if any(k in t for k in ["要求", "必须", "需要", "requirement", "qualification", "must", "should have", "you will need"]):
            return "requirements"
        if any(k in t for k in ["职责", "负责", "工作内容", "responsibilities", "you will", "your role", "duties"]):
            return "responsibilities"
        return "overview"
