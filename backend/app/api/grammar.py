import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.content import grammar_lessons, public_lesson
from app.database import get_session
from app.models import GrammarProgress
from app.schemas import GrammarAnswer, GrammarAnswerResult

router = APIRouter(prefix="/grammar", tags=["grammar"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _normalized(value: str | list[str]) -> str:
    if isinstance(value, list):
        assembled = ""
        for token in value:
            if not assembled:
                assembled = token
            elif token.startswith("-"):
                assembled += token[1:]
            else:
                assembled += " " + token
        text = assembled
    else:
        text = value
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _find_lesson(slug: str) -> dict[str, Any]:
    lesson = next((item for item in grammar_lessons() if item["slug"] == slug), None)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Урок не найден")
    return lesson


@router.get("/lessons")
async def list_lessons(user: CurrentUser, session: Session) -> list[dict[str, Any]]:
    progress_rows = list(
        (
            await session.scalars(select(GrammarProgress).where(GrammarProgress.user_id == user.id))
        ).all()
    )
    progress = {row.lesson_slug: row for row in progress_rows}
    result = []
    for lesson in grammar_lessons():
        item = public_lesson(lesson)
        row = progress.get(lesson["slug"])
        item["progress"] = {
            "completed": bool(row and row.completed),
            "solved": len(row.solved_exercises) if row else 0,
            "total": len(lesson["exercises"]),
        }
        result.append(item)
    return result


@router.get("/lessons/{slug}")
async def get_lesson(slug: str, _user: CurrentUser) -> dict[str, Any]:
    return public_lesson(_find_lesson(slug))


@router.post("/lessons/{slug}/answer", response_model=GrammarAnswerResult)
async def answer_exercise(
    slug: str,
    payload: GrammarAnswer,
    user: CurrentUser,
    session: Session,
) -> GrammarAnswerResult:
    lesson = _find_lesson(slug)
    exercise = next(
        (item for item in lesson["exercises"] if item["id"] == payload.exercise_id), None
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    correct = _normalized(payload.answer) == _normalized(exercise["answer"])

    progress = await session.scalar(
        select(GrammarProgress).where(
            GrammarProgress.user_id == user.id,
            GrammarProgress.lesson_slug == slug,
        )
    )
    if progress is None:
        progress = GrammarProgress(user_id=user.id, lesson_slug=slug)
        session.add(progress)
    progress.attempts += 1
    progress.last_exercise_id = payload.exercise_id
    solved = list(progress.solved_exercises or [])
    first_solution = correct and payload.exercise_id not in solved
    if first_solution:
        solved.append(payload.exercise_id)
        progress.solved_exercises = solved
        progress.correct_answers = len(solved)
    was_completed = progress.completed
    progress.completed = len(solved) == len(lesson["exercises"])

    xp = 12 if first_solution else 0
    if progress.completed and not was_completed:
        xp += 35
    user.xp += xp
    await session.commit()
    return GrammarAnswerResult(
        correct=correct,
        expected=exercise["answer"],
        explanation=exercise["explanation"],
        completed=progress.completed,
        xp_earned=xp,
    )
