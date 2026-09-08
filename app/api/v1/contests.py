from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.contest import Contest, ContestProblem
from app.schemas.contest import ContestResponse, ContestDetailResponse
from app.services.leaderboard import RedisLeaderboardService

router = APIRouter()


@router.get("", response_model=List[ContestResponse])
async def list_contests(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List active and upcoming contests."""
    stmt = select(Contest).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{contest_id}", response_model=ContestDetailResponse)
async def get_contest(
    contest_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Fetch contest details and problem sequence."""
    stmt = (
        select(Contest)
        .options(selectinload(Contest.contest_problems).selectinload(ContestProblem.problem))
        .where(Contest.contest_id == contest_id)
    )
    result = await db.execute(stmt)
    contest = result.scalar_one_or_none()
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    return contest


@router.get("/{contest_id}/leaderboard")
async def get_contest_leaderboard(
    contest_id: int,
    limit: int = 50
):
    """
    Fetch high-concurrency contest rankings instantly from Redis ZSET without DB table joins.
    """
    try:
        leaderboard = await RedisLeaderboardService.get_leaderboard(contest_id=contest_id, limit=limit)
    except Exception:
        leaderboard = []
    return {"contest_id": contest_id, "rankings": leaderboard}
