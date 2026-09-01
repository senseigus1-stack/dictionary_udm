import random
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.database import get_session
from app.models import DictionaryEntry, ReviewLog, UserCard
from app.schemas import (
    EntryView,
    ReviewCreate,
    ReviewResult,
    StudyCard,
    StudyOption,
    StudySession,
    StudyStats,
)
from app.services.srs import grade_answer, schedule_review

router = APIRouter(prefix="/learn", tags=["learning"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def _options_for(session: AsyncSession, entry: DictionaryEntry) -> list[StudyOption]:
    filters = [DictionaryEntry.id != entry.id, DictionaryEntry.gloss != ""]
    if entry.part_of_speech:
        filters.append(DictionaryEntry.part_of_speech == entry.part_of_speech)
    candidates = list(
        (
            await session.scalars(
                select(DictionaryEntry)
                .where(*filters)
                .order_by(func.abs(DictionaryEntry.id - entry.id))
                .limit(8)
            )
        ).all()
    )
    random.SystemRandom().shuffle(candidates)
    options = [StudyOption(entry_id=entry.id, text=entry.gloss)]
    seen = {entry.gloss.casefold()}
    for candidate in candidates:
        if candidate.gloss.casefold() not in seen:
            options.append(StudyOption(entry_id=candidate.id, text=candidate.gloss))
            seen.add(candidate.gloss.casefold())
        if len(options) == 4:
            break
    random.SystemRandom().shuffle(options)
    return options


@router.get("/session", response_model=StudySession)
async def create_study_session(
    user: CurrentUser,
    session: Session,
    limit: int = Query(default=10, ge=1, le=30),
) -> StudySession:
    now = datetime.now(UTC)
    due_statement = (
        select(UserCard, DictionaryEntry)
        .join(DictionaryEntry, DictionaryEntry.id == UserCard.entry_id)
        .where(UserCard.user_id == user.id, UserCard.due_at <= now)
        .order_by(UserCard.due_at)
        .limit(limit)
    )
    due_rows = list((await session.execute(due_statement)).all())
    entries: list[tuple[DictionaryEntry, bool]] = [(row[1], False) for row in due_rows]

    remaining = limit - len(entries)
    if remaining:
        studied_ids = select(UserCard.entry_id).where(UserCard.user_id == user.id)
        new_entries = list(
            (
                await session.scalars(
                    select(DictionaryEntry)
                    .where(DictionaryEntry.gloss != "", DictionaryEntry.id.not_in(studied_ids))
                    .order_by(DictionaryEntry.learning_rank, DictionaryEntry.id)
                    .limit(remaining)
                )
            ).all()
        )
        entries.extend((entry, True) for entry in new_entries)

    cards = [
        StudyCard(
            entry=EntryView.model_validate(entry),
            options=await _options_for(session, entry),
            is_new=is_new,
        )
        for entry, is_new in entries
    ]
    due_count = (
        await session.scalar(
            select(func.count())
            .select_from(UserCard)
            .where(UserCard.user_id == user.id, UserCard.due_at <= now)
        )
        or 0
    )
    return StudySession(
        cards=cards,
        due_count=due_count,
        new_count=sum(1 for _entry, is_new in entries if is_new),
    )


@router.post("/review", response_model=ReviewResult)
async def review_card(payload: ReviewCreate, user: CurrentUser, session: Session) -> ReviewResult:
    entry = await session.get(DictionaryEntry, payload.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Слово не найдено")
    card = await session.get(UserCard, (user.id, payload.entry_id))
    if card is None:
        card = UserCard(user_id=user.id, entry_id=payload.entry_id)
        session.add(card)

    now = datetime.now(UTC)
    grade = grade_answer(payload.correct, payload.confidence, payload.response_ms)
    schedule = schedule_review(
        grade=grade,
        interval_days=card.interval_days,
        ease=card.ease,
        repetitions=card.repetitions,
        lapses=card.lapses,
        now=now,
    )
    card.due_at = schedule.due_at
    card.interval_days = schedule.interval_days
    card.ease = schedule.ease
    card.repetitions = schedule.repetitions
    card.lapses = schedule.lapses
    card.last_grade = grade
    card.last_reviewed_at = now

    xp = (2, 7, 10, 14)[grade]
    today = now.date()
    if user.last_study_date != today:
        user.streak = user.streak + 1 if user.last_study_date == today - timedelta(days=1) else 1
        user.last_study_date = today
    user.xp += xp
    session.add(
        ReviewLog(
            user_id=user.id,
            entry_id=payload.entry_id,
            grade=grade,
            correct=payload.correct,
            response_ms=payload.response_ms,
        )
    )
    await session.commit()
    return ReviewResult(
        grade=grade,
        due_at=schedule.due_at,
        interval_days=schedule.interval_days,
        xp_earned=xp,
        streak=user.streak,
    )


@router.get("/stats", response_model=StudyStats)
async def study_stats(user: CurrentUser, session: Session) -> StudyStats:
    now = datetime.now(UTC)
    start_today = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)
    start_30d = now - timedelta(days=30)
    learned = (
        await session.scalar(
            select(func.count())
            .select_from(UserCard)
            .where(UserCard.user_id == user.id, UserCard.repetitions > 0)
        )
        or 0
    )
    due = (
        await session.scalar(
            select(func.count())
            .select_from(UserCard)
            .where(UserCard.user_id == user.id, UserCard.due_at <= now)
        )
        or 0
    )
    reviewed = (
        await session.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= start_today)
        )
        or 0
    )
    accuracy = await session.scalar(
        select(func.avg(cast(ReviewLog.correct, Integer))).where(
            and_(ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= start_30d)
        )
    )
    return StudyStats(
        learned=learned,
        due_today=due,
        reviewed_today=reviewed,
        accuracy_30d=round(float(accuracy or 0) * 100, 1),
        xp=user.xp,
        streak=user.streak,
        daily_goal=user.daily_goal,
    )
