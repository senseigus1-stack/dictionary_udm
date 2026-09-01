import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).parent / "content"


@lru_cache
def grammar_lessons() -> list[dict[str, Any]]:
    return json.loads((CONTENT_DIR / "grammar_lessons.json").read_text(encoding="utf-8"))


@lru_cache
def curated_words() -> dict[str, int]:
    words = json.loads((CONTENT_DIR / "common_words.json").read_text(encoding="utf-8"))
    return {word: position for position, word in enumerate(words)}


def public_lesson(lesson: dict[str, Any]) -> dict[str, Any]:
    result = dict(lesson)
    result["exercises"] = [
        {key: value for key, value in exercise.items() if key not in {"answer", "explanation"}}
        for exercise in lesson["exercises"]
    ]
    return result
