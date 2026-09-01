from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Schedule:
    grade: int
    due_at: datetime
    interval_days: float
    ease: float
    repetitions: int
    lapses: int


def grade_answer(correct: bool, confidence: int, response_ms: int | None = None) -> int:
    if not correct:
        return 0
    if confidence >= 3 and (response_ms is None or response_ms < 12_000):
        return 3
    if confidence <= 1 or (response_ms is not None and response_ms > 35_000):
        return 1
    return 2


def schedule_review(
    *,
    grade: int,
    interval_days: float,
    ease: float,
    repetitions: int,
    lapses: int,
    now: datetime | None = None,
) -> Schedule:
    now = now or datetime.now(UTC)
    ease = max(1.3, min(3.0, ease))

    if grade == 0:
        return Schedule(0, now + timedelta(minutes=7), 0.0, max(1.3, ease - 0.2), 0, lapses + 1)

    repetitions += 1
    if grade == 1:
        next_interval = max(1.0, interval_days * 1.2)
        ease = max(1.3, ease - 0.05)
    elif grade == 2:
        if repetitions == 1:
            next_interval = 1.0
        elif repetitions == 2:
            next_interval = 3.0
        else:
            next_interval = max(3.0, interval_days * ease)
    else:
        if repetitions == 1:
            next_interval = 4.0
        else:
            next_interval = max(4.0, interval_days * ease * 1.3)
        ease = min(3.0, ease + 0.05)

    next_interval = round(min(next_interval, 365.0), 2)
    return Schedule(
        grade,
        now + timedelta(days=next_interval),
        next_interval,
        ease,
        repetitions,
        lapses,
    )
