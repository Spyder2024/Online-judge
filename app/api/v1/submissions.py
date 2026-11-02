import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_cache, set_cache
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.submission import Submission, SubmissionVerdict
from app.models.ai import AsyncTaskLog, TaskStatus
from app.schemas.submission import SubmissionCreate, SubmissionResponse
from app.tasks.execution import evaluate_submission_task

router = APIRouter()
security_bearer = HTTPBearer(auto_error=False)


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_code(
    sub_in: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Submit code for asynchronous evaluation.
    Requires valid JWT Bearer token authentication.
    Supports optional Idempotency-Key header to eliminate duplicate submissions.
    """
    if idempotency_key:
        cache_key = f"idempotency:{current_user.user_id}:{idempotency_key}"
        try:
            cached_sub_id = await get_cache(cache_key)
            if cached_sub_id:
                stmt = select(Submission).where(Submission.submission_id == int(cached_sub_id))
                existing_sub = (await db.execute(stmt)).scalar_one_or_none()
                if existing_sub:
                    return existing_sub
        except Exception:
            pass  # Gracefully proceed if Redis is temporarily unreachable

    submission = Submission(
        user_id=current_user.user_id,
        problem_id=sub_in.problem_id,
        code=sub_in.code,
        language_enum=sub_in.language_enum,
        verdict=SubmissionVerdict.PENDING,
        execution_time=0.0,
        memory_consumed=0,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    if idempotency_key:
        try:
            await set_cache(
                f"idempotency:{current_user.user_id}:{idempotency_key}",
                str(submission.submission_id),
                expire_seconds=120,
            )
        except Exception:
            pass

    # Create Async Task Log
    task_id = str(uuid.uuid4())
    task_log = AsyncTaskLog(
        task_id=task_id,
        task_name="app.tasks.execution.evaluate_submission_task",
        status=TaskStatus.PENDING,
        payload={"submission_id": submission.submission_id, "user_id": current_user.user_id},
    )
    db.add(task_log)
    await db.commit()

    # Dispatch to Celery queue q_compile_exec
    try:
        evaluate_submission_task.apply_async(
            args=[task_id, submission.submission_id],
            queue="q_compile_exec",
        )
    except Exception:
        pass  # In serverless environment, local queue or background worker processes independently

    return submission


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch details and verdict of a single submission (owner or admin only)."""
    stmt = select(Submission).where(Submission.submission_id == submission_id)
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if current_user.role != UserRole.ADMIN and submission.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this submission",
        )
    return submission
