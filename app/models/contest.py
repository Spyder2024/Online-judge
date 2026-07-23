from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.problem import Problem


class ContestProblem(Base):
    """
    Contest_Problems association table linking Contests and Problems (Composite PK)
    with sequence ordering and custom points values.
    """
    __tablename__ = "contest_problems"

    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contests.contest_id", ondelete="CASCADE"),
        primary_key=True,
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.problem_id", ondelete="CASCADE"),
        primary_key=True,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    points_value: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    contest: Mapped["Contest"] = relationship("Contest", back_populates="contest_problems")
    problem: Mapped["Problem"] = relationship("Problem", back_populates="contest_problems")


class Contest(Base, TimestampMixin):
    """
    Contests table managing competitive coding contests.
    """
    __tablename__ = "contests"

    contest_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    contest_problems: Mapped[List[ContestProblem]] = relationship(
        "ContestProblem", back_populates="contest", cascade="all, delete-orphan"
    )
    leaderboard_entries: Mapped[List["ContestLeaderboard"]] = relationship(
        "ContestLeaderboard", back_populates="contest", cascade="all, delete-orphan"
    )


class ContestLeaderboard(Base, TimestampMixin):
    """
    ContestLeaderboard table tracking total scores and penalty times for contestants.
    Enforces a unique constraint on (contest_id, user_id).
    """
    __tablename__ = "contest_leaderboard"
    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_user_leaderboard"),
    )

    leaderboard_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contests.contest_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalty_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    contest: Mapped[Contest] = relationship("Contest", back_populates="leaderboard_entries")
    user: Mapped["User"] = relationship("User", back_populates="leaderboard_entries")
