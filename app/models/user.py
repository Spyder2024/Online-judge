import enum
from typing import TYPE_CHECKING, List
from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.contest import ContestLeaderboard


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    CONTESTANT = "Contestant"
    STUDENT = "Student"


class User(Base, TimestampMixin):
    """
    Users table representing system users: Admins, Contestants, and Students.
    """
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", create_type=False),
        default=UserRole.CONTESTANT,
        nullable=False,
    )

    # Relationships
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission", back_populates="user", cascade="all, delete-orphan"
    )
    leaderboard_entries: Mapped[List["ContestLeaderboard"]] = relationship(
        "ContestLeaderboard", back_populates="user", cascade="all, delete-orphan"
    )
