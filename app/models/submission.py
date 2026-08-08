import enum
from typing import TYPE_CHECKING, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.problem import Problem


class LanguageEnum(str, enum.Enum):
    CPP = "C++"
    PYTHON3 = "Python3"
    JAVA = "Java"


class SubmissionVerdict(str, enum.Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILATION_ERROR = "Compilation Error"


class Submission(Base, TimestampMixin):
    """
    Submissions table capturing user code submissions and 1536-dimensional code vector embeddings.
    """
    __tablename__ = "submissions"

    submission_id: Mapped[int] = mapped_column(
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
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language_enum: Mapped[LanguageEnum] = mapped_column(
        Enum(LanguageEnum, name="languageenum", create_type=False),
        nullable=False,
    )
    verdict: Mapped[SubmissionVerdict] = mapped_column(
        Enum(SubmissionVerdict, name="submissionverdict", create_type=False),
        default=SubmissionVerdict.PENDING,
        nullable=False,
    )
    execution_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # in ms
    memory_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # in KB
    code_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="submissions")
    problem: Mapped["Problem"] = relationship("Problem", back_populates="submissions")
    ai_review: Mapped[Optional["AIReview"]] = relationship(
        "AIReview", back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )


class AIReview(Base, TimestampMixin):
    """
    AI_Reviews table (Section 3.C.2 HLD) storing automated AI code review, complexity analysis,
    and suggested refactorings linked 1-to-1 with a submission.
    """
    __tablename__ = "ai_reviews"

    review_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.submission_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    ai_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_refactoring: Mapped[str] = mapped_column(Text, nullable=False)
    code_quality_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationship
    submission: Mapped[Submission] = relationship("Submission", back_populates="ai_review")
