import json

def score_answer(question: str, answer: str, topic: str) -> dict:
    """
    Heuristic scoring for an answer.
    Returns {score: 1-10, strengths: [], weaknesses: [], suggestion: str}
    Note: In production, this is called by the agent via DeepSeek API.
    This is a fallback heuristic implementation.
    """
    word_count = len(answer.split())

    score = 5  # baseline
    strengths = []
    weaknesses = []

    if word_count > 100:
        score += 1
        strengths.append("回答详尽，有深度")
    elif word_count < 20:
        score -= 2
        weaknesses.append("回答过于简短，缺乏细节")

    technical_keywords = ["RAG", "向量", "embedding", "Agent", "LLM", "API", "Python", "FastAPI", "检索", "生成"]
    matched = [kw for kw in technical_keywords if kw.lower() in answer.lower()]
    if matched:
        score += min(len(matched), 2)
        strengths.append(f"涉及关键技术点: {', '.join(matched[:3])}")
    else:
        weaknesses.append("缺少具体技术细节")

    score = max(1, min(10, score))

    suggestion = "建议在回答中加入更多具体的技术细节和实际经验。" if score < 7 else "回答整体不错，可以进一步补充实际项目案例。"

    return {
        "score": score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestion": suggestion
    }


def format_report(module_scores: list[dict]) -> str:
    """Format the final evaluation report as markdown."""
    lines = ["# PrepSensei 面试评估报告\n"]

    total_score = 0
    count = 0

    for i, module in enumerate(module_scores):
        topic = module.get("topic", f"模块 {i+1}")
        score = module.get("score", 0)
        total_score += score
        count += 1

        lines.append(f"## 模块 {i+1}: {topic}")
        lines.append(f"**得分**: {score}/10\n")

        if module.get("strengths"):
            lines.append("**优势**:")
            for s in module["strengths"]:
                lines.append(f"- {s}")

        if module.get("weaknesses"):
            lines.append("\n**待改进**:")
            for w in module["weaknesses"]:
                lines.append(f"- {w}")

        if module.get("suggestion"):
            lines.append(f"\n**建议**: {module['suggestion']}")

        lines.append("")

    if count > 0:
        avg_score = total_score / count
        lines.append("---")
        lines.append(f"\n## 综合评估")
        lines.append(f"**总体得分**: {avg_score:.1f}/10\n")

        if avg_score >= 8:
            lines.append("**整体表现**: 优秀 🌟 — 技术基础扎实，表达清晰，有较强的实战能力。")
        elif avg_score >= 6:
            lines.append("**整体表现**: 良好 ✓ — 基础知识掌握较好，建议在深度和广度上继续提升。")
        else:
            lines.append("**整体表现**: 需要提升 📚 — 建议系统学习相关技术，多做项目实践。")

        lines.append("\n**学习建议**:")
        lines.append("- 深入学习 all-in-rag 课程，掌握 RAG 系统核心概念")
        lines.append("- 完成 hello-agents 课程，理解 Agent 架构设计")
        lines.append("- 多做实践项目，积累面试经验")

    return "\n".join(lines)
