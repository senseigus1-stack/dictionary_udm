import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class AppState(Base):
    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80), default="Путешественник")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    daily_goal: Mapped[int] = mapped_column(Integer, default=10)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_study_date: Mapped[date | None] = mapped_column(Date)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    cards: Mapped[list["UserCard"]] = relationship(back_populates="user")


class DictionaryEntry(Base):
    __tablename__ = "dictionary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(180), index=True)
    definition: Mapped[str] = mapped_column(Text)
    detail_url: Mapped[str] = mapped_column(String(255), default="")
    part_of_speech: Mapped[str | None] = mapped_column(String(40), index=True)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    gloss: Mapped[str] = mapped_column(Text, default="")
    examples: Mapped[list[str]] = mapped_column(JSON, default=list)
    learning_rank: Mapped[float] = mapped_column(Float, default=1000)

    __table_args__ = (
        Index("ix_dictionary_word_lower", func.lower(word)),
        Index("ix_dictionary_learning_pool", learning_rank, id),
    )


class UserCard(Base):
    __tablename__ = "user_cards"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("dictionary_entries.id", ondelete="CASCADE"), primary_key=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    interval_days: Mapped[float] = mapped_column(Float, default=0)
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    last_grade: Mapped[int | None] = mapped_column(Integer)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="cards")
    entry: Mapped[DictionaryEntry] = relationship()


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("dictionary_entries.id", ondelete="CASCADE"), index=True
    )
    grade: Mapped[int] = mapped_column(Integer)
    correct: Mapped[bool] = mapped_column(Boolean)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_review_user_date", user_id, reviewed_at),)


class GrammarProgress(Base):
    __tablename__ = "grammar_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    lesson_slug: Mapped[str] = mapped_column(String(80), index=True)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    solved_exercises: Mapped[list[str]] = mapped_column(JSON, default=list)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_exercise_id: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (UniqueConstraint("user_id", "lesson_slug"),)
