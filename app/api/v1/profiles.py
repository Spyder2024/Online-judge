"""
app/api/v1/profiles.py

Module 2: LeetCode-Parity CRUD Endpoints

REST endpoints added (all prefixed /api/v1/profiles):

  GET    /me                       → current user's profile (auto-creates if absent)
  PATCH  /me                       → update bio, display_name, avatar_url
  GET    /{user_id}                → public profile view for any user

  GET    /me/submissions           → paginated submission history for current user
  GET    /me/submissions/{sub_id}  → single submission detail

  GET    /me/bookmarks             → list all bookmarked problems
  POST   /me/bookmarks             → add a bookmark
  PATCH  /me/bookmarks/{bookmark_id} → update note / priority flag
  DELETE /me/bookmarks/{bookmark_id} → remove a bookmark

Non-destructive: does not modify any existing router or model file.
Registration is done in router.py via a single append.
"""

from __future__ import annotations

import math
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.problem import ProblemDifficulty
from app.models.profile import BookmarkedProblem, UserProfile
from app.models.submission import Submission, SubmissionVerdict
from app.models.user import User
from app.schemas.profile import (
    BookmarkCreate,
    BookmarkResponse,
    BookmarkUpdate,
    PaginatedSubmissionHistory,
    SubmissionHistoryItem,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Helper: get-or-create UserProfile
# ─────────────────────────────────────────────────────────────

async def _get_or_create_profile(user: User, db: AsyncSession) -> UserProfile:
    """
    Fetch an existing UserProfile for `user`, or create a blank one on first access.
    Returned object is already attached to the session.
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def _recompute_stats(user_id: int, db: AsyncSession) -> dict:
    """
    Recompute aggregate submission stats for a user and return as dict.
    Called after profile GET so stats are always fresh.
    """
    # Total submissions
    total_q = await db.execute(
        select(func.count(Submission.submission_id)).where(
            Submission.user_id == user_id
        )
    )
    total_submissions = total_q.scalar_one() or 0

    # Accepted submissions (distinct problems)
    accepted_q = await db.execute(
        select(func.count(Submission.submission_id.distinct())).where(
            Submission.user_id == user_id,
            Submission.verdict == SubmissionVerdict.ACCEPTED,
        )
    )
    total_solved = accepted_q.scalar_one() or 0

    acceptance_rate = round(total_solved / total_submissions, 4) if total_submissions else 0.0

    # Difficulty breakdown — join on Problem
    from app.models.problem import Problem

    diff_q = await db.execute(
        select(Problem.difficulty, func.count(Problem.problem_id))
        .join(Submission, Submission.problem_id == Problem.problem_id)
        .where(
            Submission.user_id == user_id,
            Submission.verdict == SubmissionVerdict.ACCEPTED,
        )
        .group_by(Problem.difficulty)
    )
    diff_counts = {row[0]: row[1] for row in diff_q.fetchall()}

    return {
        "total_submissions": total_submissions,
        "total_solved": total_solved,
        "acceptance_rate": acceptance_rate,
        "easy_solved": diff_counts.get(ProblemDifficulty.EASY, 0),
        "medium_solved": diff_counts.get(ProblemDifficulty.MEDIUM, 0),
        "hard_solved": diff_counts.get(ProblemDifficulty.HARD, 0),
    }


# ─────────────────────────────────────────────────────────────
# Profile Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfileResponse, summary="Get my profile")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the current user's profile with live-recomputed stats.
    Auto-creates a blank profile on first call.
    """
    profile = await _get_or_create_profile(current_user, db)

    # Recompute and sync stats
    stats = await _recompute_stats(current_user.user_id, db)
    for field, value in stats.items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)

    res_dict = UserProfileResponse.model_validate(profile).model_dump()
    res_dict["username"] = current_user.username
    return res_dict


@router.put("/me", response_model=UserProfileResponse, summary="Update my profile (PUT)")
@router.patch("/me", response_model=UserProfileResponse, summary="Update my profile (PATCH)")
async def update_my_profile(
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update editable profile fields: username, full_name/display_name, bio, preferred_language, avatar_url."""
    profile = await _get_or_create_profile(current_user, db)

    if body.username and body.username.strip():
        new_un = body.username.strip()
        res_existing = await db.execute(
            select(User).where(User.username == new_un, User.user_id != current_user.user_id)
        )
        if res_existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username is already taken.")
        current_user.username = new_un

    if body.full_name and body.full_name.strip():
        profile.display_name = body.full_name.strip()
    elif body.display_name and body.display_name.strip():
        profile.display_name = body.display_name.strip()

    if body.bio is not None:
        profile.bio = body.bio
    if body.avatar_url is not None:
        profile.avatar_url = body.avatar_url
    if body.preferred_language is not None:
        profile.preferred_language = body.preferred_language

    await db.commit()
    await db.refresh(profile)
    await db.refresh(current_user)

    res_dict = UserProfileResponse.model_validate(profile).model_dump()
    res_dict["username"] = current_user.username
    return res_dict


@router.get("/{user_id}", response_model=UserProfileResponse, summary="Get public profile")
async def get_public_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Public profile view — no authentication required."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found for this user.")
    return profile


# ─────────────────────────────────────────────────────────────
# Submission History Endpoints
# ─────────────────────────────────────────────────────────────

@router.get(
    "/me/submissions",
    response_model=PaginatedSubmissionHistory,
    summary="My submission history (paginated)",
)
async def get_my_submissions(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit

    # Total count
    count_q = await db.execute(
        select(func.count(Submission.submission_id)).where(
            Submission.user_id == current_user.user_id
        )
    )
    total_count = count_q.scalar_one() or 0
    total_pages = math.ceil(total_count / limit) if total_count else 1

    # Paginated items
    items_q = await db.execute(
        select(Submission)
        .where(Submission.user_id == current_user.user_id)
        .order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = items_q.scalars().all()

    return PaginatedSubmissionHistory(
        items=[SubmissionHistoryItem.model_validate(s) for s in items],
        total_count=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get(
    "/me/submissions/{submission_id}",
    response_model=SubmissionHistoryItem,
    summary="Get single submission detail",
)
async def get_my_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission).where(
            Submission.submission_id == submission_id,
            Submission.user_id == current_user.user_id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return sub


# ─────────────────────────────────────────────────────────────
# Bookmarks Endpoints
# ─────────────────────────────────────────────────────────────

@router.get(
    "/me/bookmarks",
    response_model=List[BookmarkResponse],
    summary="List my bookmarked problems",
)
async def list_bookmarks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BookmarkedProblem)
        .where(BookmarkedProblem.user_id == current_user.user_id)
        .order_by(BookmarkedProblem.is_priority.desc(), BookmarkedProblem.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/me/bookmarks",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bookmark a problem",
)
async def add_bookmark(
    body: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicate
    existing = await db.execute(
        select(BookmarkedProblem).where(
            BookmarkedProblem.user_id == current_user.user_id,
            BookmarkedProblem.problem_id == body.problem_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Problem is already bookmarked.",
        )

    bookmark = BookmarkedProblem(
        user_id=current_user.user_id,
        problem_id=body.problem_id,
        note=body.note,
        is_priority=body.is_priority,
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    return bookmark


@router.patch(
    "/me/bookmarks/{bookmark_id}",
    response_model=BookmarkResponse,
    summary="Update a bookmark note or priority",
)
async def update_bookmark(
    bookmark_id: int,
    body: BookmarkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BookmarkedProblem).where(
            BookmarkedProblem.bookmark_id == bookmark_id,
            BookmarkedProblem.user_id == current_user.user_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(bookmark, field, value)

    await db.commit()
    await db.refresh(bookmark)
    return bookmark


@router.delete(
    "/me/bookmarks/{bookmark_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a bookmark",
)
async def delete_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BookmarkedProblem).where(
            BookmarkedProblem.bookmark_id == bookmark_id,
            BookmarkedProblem.user_id == current_user.user_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found.")

    await db.delete(bookmark)
    await db.commit()
