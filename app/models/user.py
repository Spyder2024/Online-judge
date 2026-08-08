import enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.contest import ContestLeaderboard
    from app.models.profile import UserProfile, BookmarkedProblem


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
    password_hash: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # Nullable for OAuth-only users
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)

    # Module 3: OAuth identity columns
    # oauth_provider: "google" | "github" | None (None = username/password auth)
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    # oauth_id: the provider's stable user ID (sub claim for Google, id for GitHub)
    oauth_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
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
    # Module 2: Profile & Bookmarks (back-populated from profile.py)
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user",
        uselist=False, cascade="all, delete-orphan"
    )
    bookmarks: Mapped[List["BookmarkedProblem"]] = relationship(
        "BookmarkedProblem", back_populates="user", cascade="all, delete-orphan"
    )
