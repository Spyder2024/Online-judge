import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.problem import Problem


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class KnowledgeBaseHint(Base, TimestampMixin):
    """
    Knowledge_Base_Hints table (Section 3.C.2 HLD) storing progressive AI hints
    with 1536-dimensional vector embeddings for semantic retrieval.
    """
    __tablename__ = "knowledge_base_hints"

    hint_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.problem_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1: Nudge, 2: Idea, 3: Pseudocode
    hint_content: Mapped[str] = mapped_column(Text, nullable=False)
    hint_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384), nullable=True
    )

    # Relationship
    problem: Mapped["Problem"] = relationship("Problem", back_populates="hints")


class AsyncTaskLog(Base):
    """
    Async_Task_Logs table (Section 3.C.2 HLD) recording background evaluation,
    AI review generation, and vector embedding worker tasks.
    """
    __tablename__ = "async_task_logs"

    task_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    task_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="taskstatus", create_type=False),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    payload: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
