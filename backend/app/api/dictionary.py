from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.database import get_session
from app.models import DictionaryEntry
from app.schemas import EntryView, SearchResponse

router = APIRouter(prefix="/dictionary", tags=["dictionary"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/search", response_model=SearchResponse)
async def search_dictionary(
    _user: CurrentUser,
    session: Session,
    q: str = Query(default="", max_length=100),
    part_of_speech: str | None = Query(default=None, max_length=40),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> SearchResponse:
    filters = []
    if q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(DictionaryEntry.word.ilike(pattern), DictionaryEntry.gloss.ilike(pattern))
        )
    if part_of_speech:
        filters.append(DictionaryEntry.part_of_speech == part_of_speech)

    statement = select(DictionaryEntry).where(*filters)
    count_statement = select(func.count()).select_from(DictionaryEntry).where(*filters)
    total = await session.scalar(count_statement) or 0
    items = list(
        (
            await session.scalars(
                statement.order_by(DictionaryEntry.learning_rank, DictionaryEntry.word)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    return SearchResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{entry_id}", response_model=EntryView)
async def get_entry(entry_id: int, _user: CurrentUser, session: Session) -> DictionaryEntry:
    entry = await session.get(DictionaryEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Слово не найдено")
    return entry
