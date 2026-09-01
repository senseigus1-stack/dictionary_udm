from datetime import UTC, datetime, timedelta

from app.services.srs import grade_answer, schedule_review

NOW = datetime(2026, 9, 2, 12, tzinfo=UTC)


def test_wrong_answer_returns_in_seven_minutes() -> None:
    result = schedule_review(grade=0, interval_days=9, ease=2.5, repetitions=4, lapses=0, now=NOW)
    assert result.due_at == NOW + timedelta(minutes=7)
    assert result.repetitions == 0
    assert result.lapses == 1


def test_good_answers_build_stable_intervals() -> None:
    first = schedule_review(grade=2, interval_days=0, ease=2.5, repetitions=0, lapses=0, now=NOW)
    second = schedule_review(
        grade=2,
        interval_days=first.interval_days,
        ease=first.ease,
        repetitions=first.repetitions,
        lapses=first.lapses,
        now=first.due_at,
    )
    assert first.interval_days == 1
    assert second.interval_days == 3


def test_grade_uses_correctness_confidence_and_speed() -> None:
    assert grade_answer(False, 3, 1000) == 0
    assert grade_answer(True, 3, 9000) == 3
    assert grade_answer(True, 2, 15_000) == 2
    assert grade_answer(True, 3, 40_000) == 1
