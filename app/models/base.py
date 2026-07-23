from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """
    Base declarative class for all SQLAlchemy ORM models.
    Automatically converts CamelCase class names to snake_case table names.
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Convert CamelCase class name to snake_case pluralized table name if needed
        # Or keep explicit tablename defined in subclasses
        name = cls.__name__
        return name.lower() + "s" if not name.endswith("s") else name.lower()


class TimestampMixin:
    """
    Shared mixin providing created_at and updated_at timestamps for models.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
