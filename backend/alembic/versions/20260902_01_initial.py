"""Initial learning platform schema.

Revision ID: 20260902_01
Revises:
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_state",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("daily_goal", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("streak", sa.Integer(), nullable=False),
        sa.Column("last_study_date", sa.Date(), nullable=True),
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "dictionary_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(length=180), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("detail_url", sa.String(length=255), nullable=False),
        sa.Column("part_of_speech", sa.String(length=40), nullable=True),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("gloss", sa.Text(), nullable=False),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column("learning_rank", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dictionary_entries_word", "dictionary_entries", ["word"])
    op.create_index("ix_dictionary_entries_part_of_speech", "dictionary_entries", ["part_of_speech"])
    op.create_index("ix_dictionary_word_lower", "dictionary_entries", [sa.text("lower(word)")])
    op.create_index(
        "ix_dictionary_learning_pool", "dictionary_entries", ["learning_rank", "id"]
    )

    op.create_table(
        "user_cards",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.Float(), nullable=False),
        sa.Column("ease", sa.Float(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False),
        sa.Column("lapses", sa.Integer(), nullable=False),
        sa.Column("last_grade", sa.Integer(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["entry_id"], ["dictionary_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "entry_id"),
    )
    op.create_index("ix_user_cards_due_at", "user_cards", ["due_at"])

    op.create_table(
        "review_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["dictionary_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_logs_user_id", "review_logs", ["user_id"])
    op.create_index("ix_review_logs_entry_id", "review_logs", ["entry_id"])
    op.create_index("ix_review_user_date", "review_logs", ["user_id", "reviewed_at"])

    op.create_table(
        "grammar_progress",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_slug", sa.String(length=80), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("solved_exercises", sa.JSON(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("last_exercise_id", sa.String(length=80), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lesson_slug"),
    )
    op.create_index("ix_grammar_progress_user_id", "grammar_progress", ["user_id"])
    op.create_index("ix_grammar_progress_lesson_slug", "grammar_progress", ["lesson_slug"])


def downgrade() -> None:
    op.drop_table("grammar_progress")
    op.drop_table("review_logs")
    op.drop_table("user_cards")
    op.drop_table("dictionary_entries")
    op.drop_table("users")
    op.drop_table("app_state")
