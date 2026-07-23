from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.submission import Submission, AIReview
from app.services.ai_agent import MultiAgentReviewPanel, TLEAnalyzer, EdgeCaseProvider

router = APIRouter()


@router.get("/submissions/{submission_id}/ai-review")
async def get_submission_ai_review(
    submission_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch generated AI Review, Multi-Agent panel feedback, TLE analysis, or edge cases
    linked 1-to-1 with a submission.
    """
    stmt = (
        select(AIReview)
        .where(AIReview.submission_id == submission_id)
    )
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if review:
        return {
            "review_id": review.review_id,
            "submission_id": review.submission_id,
            "ai_feedback": review.ai_feedback,
            "suggested_refactoring": review.suggested_refactoring,
            "code_quality_score": review.code_quality_score,
            "created_at": review.created_at
        }

    # If review not generated in DB yet, fetch submission and compute dynamically
    stmt_sub = select(Submission).options(selectinload(Submission.problem)).where(Submission.submission_id == submission_id)
    res_sub = await db.execute(stmt_sub)
    submission = res_sub.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Generate fallback dynamic review
    panel_res = MultiAgentReviewPanel.synthesize_review(submission.code, submission.language_enum.value)
    return {
        "review_id": 0,
        "submission_id": submission_id,
        "ai_feedback": panel_res["ai_feedback"],
        "suggested_refactoring": panel_res["suggested_refactoring"],
        "code_quality_score": panel_res["code_quality_score"],
        "created_at": None
    }
