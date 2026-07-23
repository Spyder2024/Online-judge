from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContestProblemCreate(BaseModel):
    problem_id: int = Field(..., gt=0)
    sequence_order: int = Field(..., gt=0, description="Order inside the contest")
    points_value: int = Field(..., gt=0, description="Points awarded for solving")


class ContestProblemResponse(ContestProblemCreate):
    model_config = ConfigDict(from_attributes=True)


class ContestBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    start_time: datetime = Field(..., description="Contest start timestamp")
    end_time: datetime = Field(..., description="Contest end timestamp")
    is_active: bool = Field(default=True)


class ContestCreate(ContestBase):
    problems: Optional[List[ContestProblemCreate]] = Field(default=None, description="Initial contest problems")


class ContestResponse(ContestBase):
    contest_id: int
    contest_problems: List[ContestProblemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntryResponse(BaseModel):
    leaderboard_id: int
    contest_id: int
    user_id: int
    username: Optional[str] = None
    total_score: int
    penalty_time: float
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
