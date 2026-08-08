"""
app/models/profile.py

Module 2: LeetCode-Parity Data Models

Adds two new tables (non-destructive — no existing models modified):
  - user_profiles  : Cached aggregated stats per user (total solved, acceptance rate,
                     difficulty breakdown). Computed on-demand and cached here to avoid
                     expensive JOIN queries on every profile page load.
  - bookmarked_problems : User-starred/bookmarked problems with optional notes.

Both tables use FK relationships into the existing `users` and `problems` tables.
The SQLAlchemy relationships on User and Problem are declared with a TYPE_CHECKING
guard and back_populates added via string references to avoid circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.problem import Problem


class UserProfile(Base, TimestampMixin):
    """
    user_profiles — One-to-one extension of the `users` table.

    Stores aggregated submission statistics for a user's profile dashboard.
    Values are recomputed and upserted after every Accepted submission by
    the Celery `q_compile_exec` worker (Phase 5 hook).

    Design decision: keep stats as a separate table (not columns on `users`)
    so that the core auth schema stays lean and this table can be dropped/
    rebuilt without touching user credentials.
    """

    __tablename__ = "user_profiles"

    profile_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,      # enforces 1-to-1
        nullable=False,
        index=True,
    )

    # ── Aggregate Stats ────────────────────────────────────────────────
    total_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Acceptance rate stored as a float (0.0 – 1.0), displayed as % in UI
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Difficulty-level breakdown
    easy_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hard_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Optional free-text bio visible on the public profile page
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional display name / avatar URL / preferred language
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    preferred_language: Mapped[Optional[str]] = mapped_column(String(32), default="PYTHON3", nullable=True)

    # ── Relationship ────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="profile")


class BookmarkedProblem(Base, TimestampMixin):
    """
    bookmarked_problems — User-starred problems with optional private notes.

    Composite unique constraint on (user_id, problem_id) prevents duplicates.
    """

    __tablename__ = "bookmarked_problems"

    bookmark_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.problem_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional private note the user can attach to a bookmark
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Soft "priority" flag — user can mark a bookmark as high priority
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_bookmark_user_problem"),
    )

    # ── Relationships ───────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="bookmarks")
    problem: Mapped["Problem"] = relationship("Problem", back_populates="bookmarks")
