from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.submission import LanguageEnum, SubmissionVerdict


class AIReviewResponse(BaseModel):
    review_id: int
    submission_id: int
    ai_feedback: str = Field(..., description="Detailed AI code review and complexity analysis")
    suggested_refactoring: str = Field(..., description="AI suggested code refactoring")
    code_quality_score: float = Field(..., ge=0.0, le=100.0, description="Code quality rating score out of 100")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionBase(BaseModel):
    problem_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, description="Source code text submitted for evaluation")
    language_enum: LanguageEnum = Field(..., description="Programming language selected")


class SubmissionCreate(SubmissionBase):
    code_embedding: Optional[list[float]] = Field(
        default=None, min_length=384, max_length=384, description="Optional 384-dimensional code embedding"
    )


class SubmissionUpdate(BaseModel):
    verdict: Optional[SubmissionVerdict] = None
    execution_time: Optional[float] = Field(None, ge=0.0)
    memory_consumed: Optional[int] = Field(None, ge=0)
    code_embedding: Optional[list[float]] = Field(None, min_length=384, max_length=384)


class SubmissionResponse(SubmissionBase):
    submission_id: int
    user_id: int
    verdict: SubmissionVerdict
    execution_time: float
    memory_consumed: int
    created_at: datetime
    updated_at: datetime
    ai_review: Optional[AIReviewResponse] = None

    model_config = ConfigDict(from_attributes=True)
