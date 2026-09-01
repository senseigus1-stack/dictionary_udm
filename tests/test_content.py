from app.api.grammar import _normalized
from app.content import grammar_lessons, public_lesson


def test_grammar_course_has_unique_complete_exercises() -> None:
    lessons = grammar_lessons()
    assert len(lessons) == 10
    assert [lesson["order"] for lesson in lessons] == list(range(1, 11))
    exercise_ids = [exercise["id"] for lesson in lessons for exercise in lesson["exercises"]]
    assert len(exercise_ids) == len(set(exercise_ids))
    assert all(len(lesson["exercises"]) == 3 for lesson in lessons)


def test_public_lesson_does_not_leak_answers() -> None:
    lesson = public_lesson(grammar_lessons()[0])
    assert all("answer" not in exercise for exercise in lesson["exercises"])
    assert all("explanation" not in exercise for exercise in lesson["exercises"])


def test_grammar_assembly_joins_affixes_but_keeps_word_spaces() -> None:
    assert _normalized(["ӟеч", "кыл"]) == "ӟеч кыл"
    assert _normalized(["эш", "-е", "-лы"]) == "эшелы"
