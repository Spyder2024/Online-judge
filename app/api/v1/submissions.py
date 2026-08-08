import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
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
    current_user: User = Depends(get_current_user)
):
    """
    Submit code for asynchronous evaluation.
    Requires valid JWT Bearer token authentication.
    """
    submission = Submission(
        user_id=current_user.user_id,
        problem_id=sub_in.problem_id,
        code=sub_in.code,
        language_enum=sub_in.language_enum,
        verdict=SubmissionVerdict.PENDING,
        execution_time=0.0,
        memory_consumed=0
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    
    # Create Async Task Log
    task_id = str(uuid.uuid4())
    task_log = AsyncTaskLog(
        task_id=task_id,
        task_name="app.tasks.execution.evaluate_submission_task",
        status=TaskStatus.PENDING,
        payload={"submission_id": submission.submission_id, "user_id": current_user.user_id}
    )
    db.add(task_log)
    await db.commit()
    
    # Dispatch to Celery queue q_compile_exec
    evaluate_submission_task.apply_async(
        args=[task_id, submission.submission_id],
        queue="q_compile_exec"
    )
    
    return submission


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Fetch details and verdict of a single submission."""
    stmt = select(Submission).where(Submission.submission_id == submission_id)
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission
