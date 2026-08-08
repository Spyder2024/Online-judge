"""
app/schemas/profile.py

Module 2: Pydantic schemas for UserProfile and BookmarkedProblem endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────
# UserProfile Schemas
# ──────────────────────────────────────────────

class UserProfileBase(BaseModel):
    bio: Optional[str] = Field(None, max_length=1000, description="Public profile bio")
    display_name: Optional[str] = Field(None, max_length=128, description="Display name shown on profile")
    avatar_url: Optional[str] = Field(None, max_length=512, description="Avatar image URL")
    preferred_language: Optional[str] = Field("PYTHON3", description="Preferred programming language (PYTHON3, CPP, JAVA)")


class UserProfileUpdate(UserProfileBase):
    """Fields the user can update themselves."""
    username: Optional[str] = Field(None, max_length=64, description="Optional new username")
    full_name: Optional[str] = Field(None, max_length=128, description="Alias for display_name")


class UserProfileResponse(UserProfileBase):
    profile_id: int
    user_id: int
    username: Optional[str] = None
    total_solved: int
    total_submissions: int
    acceptance_rate: float = Field(..., description="Acceptance rate as a decimal (0.0–1.0)")
    easy_solved: int
    medium_solved: int
    hard_solved: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────
# BookmarkedProblem Schemas
# ──────────────────────────────────────────────

class BookmarkCreate(BaseModel):
    problem_id: int = Field(..., gt=0, description="ID of the problem to bookmark")
    note: Optional[str] = Field(None, max_length=2000, description="Optional private note")
    is_priority: bool = Field(False, description="Mark as high-priority bookmark")


class BookmarkUpdate(BaseModel):
    note: Optional[str] = Field(None, max_length=2000)
    is_priority: Optional[bool] = None


class BookmarkResponse(BaseModel):
    bookmark_id: int
    user_id: int
    problem_id: int
    note: Optional[str]
    is_priority: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────
# Submission History (paginated)
# ──────────────────────────────────────────────

class SubmissionHistoryItem(BaseModel):
    """Lightweight submission record for history listing."""
    submission_id: int
    problem_id: int
    language_enum: str
    verdict: str
    execution_time: float
    memory_consumed: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSubmissionHistory(BaseModel):
    items: list[SubmissionHistoryItem]
    total_count: int
    page: int
    limit: int
    total_pages: int
