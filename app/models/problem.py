import enum
from typing import TYPE_CHECKING, List
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.contest import ContestProblem
    from app.models.ai import KnowledgeBaseHint
    from app.models.profile import BookmarkedProblem


class ProblemDifficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class ProblemTag(Base):
    """
    Problem_Tags association table linking Problems and Tags (Composite PK).
    """
    __tablename__ = "problem_tags"

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.problem_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.tag_id", ondelete="CASCADE"),
        primary_key=True,
    )


class Tag(Base):
    """
    Tags table for problem category classification (e.g., Dynamic Programming, Graph).
    """
    __tablename__ = "tags"

    tag_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    tag_name: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    # Relationship to problems via ProblemTag
    problems: Mapped[List["Problem"]] = relationship(
        "Problem", secondary="problem_tags", back_populates="tags"
    )


class Problem(Base, TimestampMixin):
    """
    Problems table with 1536-dimensional embedding column for semantic search and clustering.
    """
    __tablename__ = "problems"

    problem_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    statement_text: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[ProblemDifficulty] = mapped_column(
        Enum(ProblemDifficulty, name="problemdifficulty", create_type=False),
        nullable=False,
    )
    time_limit: Mapped[float] = mapped_column(Float, nullable=False)  # in seconds
    memory_limit: Mapped[int] = mapped_column(Integer, nullable=False)  # in MB
    problem_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384), nullable=True
    )

    # Relationships
    tags: Mapped[List[Tag]] = relationship(
        "Tag", secondary="problem_tags", back_populates="problems"
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase", back_populates="problem", cascade="all, delete-orphan"
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission", back_populates="problem", cascade="all, delete-orphan"
    )
    contest_problems: Mapped[List["ContestProblem"]] = relationship(
        "ContestProblem", back_populates="problem", cascade="all, delete-orphan"
    )
    hints: Mapped[List["KnowledgeBaseHint"]] = relationship(
        "KnowledgeBaseHint", back_populates="problem", cascade="all, delete-orphan"
    )
    # Module 2: Bookmarks back-reference
    bookmarks: Mapped[List["BookmarkedProblem"]] = relationship(
        "BookmarkedProblem", back_populates="problem", cascade="all, delete-orphan"
    )


class TestCase(Base, TimestampMixin):
    """
    TestCases table storing public and hidden test cases for problem evaluation.
    """
    __tablename__ = "test_cases"

    test_case_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.problem_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship
    problem: Mapped[Problem] = relationship("Problem", back_populates="test_cases")
