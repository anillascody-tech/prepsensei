#!/usr/bin/env python3
"""Validates question_bank.json meets quality requirements."""
import json
import sys
from pathlib import Path
from collections import Counter


def main():
    qb_path = Path(__file__).parent.parent / "data" / "question_bank.json"
    if not qb_path.exists():
        print(f"ERROR: {qb_path} not found")
        sys.exit(1)

    with open(qb_path, encoding="utf-8") as f:
        questions = json.load(f)

    errors = []
    required_fields = {"id", "topic", "question", "difficulty", "answer_guide"}
    required_topics = {
        "自我介绍与项目经历", "RAG系统理解", "Agent与工具调用", "场景设计题", "岗位匹配度"
    }
    valid_difficulties = {"easy", "medium", "hard"}

    topic_counts = Counter()
    ids_seen = set()

    for i, q in enumerate(questions):
        missing = required_fields - set(q.keys())
        if missing:
            errors.append(f"Q[{i}] missing fields: {missing}")
            continue

        if q["id"] in ids_seen:
            errors.append(f"Q[{i}] duplicate id: {q['id']}")
        ids_seen.add(q["id"])

        if q["difficulty"] not in valid_difficulties:
            errors.append(f"Q[{i}] invalid difficulty '{q['difficulty']}': {q['id']}")

        guide = q.get("answer_guide", "")
        # CJK chars count as ~2 English words; use len() for Chinese content
        if len(guide) < 30:
            errors.append(f"Q[{i}] answer_guide too short ({len(guide)} chars): {q['id']}")

        topic_counts[q["topic"]] += 1

    if len(questions) < 80:
        errors.append(f"Total questions {len(questions)} < 80 required")

    for topic in required_topics:
        count = topic_counts.get(topic, 0)
        if count < 10:
            errors.append(f"Topic '{topic}': {count} questions, need ≥10")

    print(f"\n=== Question Bank Validation ===")
    print(f"Total questions: {len(questions)}")
    print(f"\nPer-topic counts:")
    for topic, count in sorted(topic_counts.items()):
        status = "✓" if count >= 10 else "✗"
        print(f"  {status} {topic}: {count}")

    if errors:
        print(f"\n✗ FAILED ({len(errors)} error(s)):")
        for e in errors[:15]:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"\n✓ PASSED — all quality checks passed")


if __name__ == "__main__":
    main()
