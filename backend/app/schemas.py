import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    daily_goal: int
    xp: int
    streak: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user: UserView


class GuestCreate(BaseModel):
    display_name: str = Field(default="Путешественник", min_length=1, max_length=80)


class TelegramAuth(BaseModel):
    telegram_id: int
    display_name: str = Field(default="Ученик", min_length=1, max_length=80)


class TelegramWebAppAuth(BaseModel):
    init_data: str = Field(min_length=1, max_length=8192)


class EntryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    word: str
    gloss: str
    definition: str
    detail_url: str
    part_of_speech: str | None
    labels: list[str]
    examples: list[str]


class SearchResponse(BaseModel):
    items: list[EntryView]
    total: int
    offset: int
    limit: int


class StudyOption(BaseModel):
    entry_id: int
    text: str


class StudyCard(BaseModel):
    entry: EntryView
    options: list[StudyOption]
    direction: str = "udmurt_to_russian"
    is_new: bool


class StudySession(BaseModel):
    cards: list[StudyCard]
    due_count: int
    new_count: int


class ReviewCreate(BaseModel):
    entry_id: int
    correct: bool
    confidence: int = Field(default=2, ge=1, le=3)
    response_ms: int | None = Field(default=None, ge=0, le=600_000)


class ReviewResult(BaseModel):
    grade: int
    due_at: datetime
    interval_days: float
    xp_earned: int
    streak: int


class StudyStats(BaseModel):
    learned: int
    due_today: int
    reviewed_today: int
    accuracy_30d: float
    xp: int
    streak: int
    daily_goal: int


class GrammarAnswer(BaseModel):
    exercise_id: str
    answer: str | list[str]


class GrammarAnswerResult(BaseModel):
    correct: bool
    expected: str | list[str]
    explanation: str
    completed: bool
    xp_earned: int
