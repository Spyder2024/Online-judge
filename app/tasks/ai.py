import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.ai import AsyncTaskLog, TaskStatus
from app.models.submission import Submission, SubmissionVerdict, AIReview
from app.services.ai_agent import (
    TLEAnalyzer,
    MultiAgentReviewPanel,
    EdgeCaseProvider,
    PlagiarismDetector
)
from app.tasks.execution import _publish_event


async def _analyze_submission_async(task_id: str, submission_id: int) -> None:
    """
    Asynchronous AI Agent Workflow Execution inside Celery `q_ai_analysis` queue.
    Orchestrates TLE Analysis, Multi-Agent Review Panel, Edge-Case Generation,
    and pgvector Plagiarism / Logic-Clone detection.
    """
    async with async_session_maker() as session:
        # Fetch Submission and Problem
        stmt = (
            select(Submission)
            .options(selectinload(Submission.problem))
            .where(Submission.submission_id == submission_id)
        )
        result = await session.execute(stmt)
        submission = result.scalar_one_or_none()

        if not submission or not submission.problem:
            return

        problem = submission.problem
        verdict = submission.verdict
        code = submission.code
        lang = submission.language_enum.value

        ai_feedback = ""
        suggested_refactor = ""
        quality_score = 85.0
        metrics = {}

        # 1. TLE Analysis
        if verdict == SubmissionVerdict.TIME_LIMIT_EXCEEDED:
            tle_res = TLEAnalyzer.analyze(code, lang, problem.statement_text, problem.time_limit)
            ai_feedback = tle_res["explanation"]
            suggested_refactor = "// TLE Fix: Refactor loop structures to O(N log N) or O(N)"
            quality_score = 45.0
            metrics = tle_res["metrics"]

        # 2. Edge-Case Counter-Example Provider
        elif verdict == SubmissionVerdict.WRONG_ANSWER:
            edge_res = EdgeCaseProvider.generate(code, problem.statement_text)
            ec = edge_res["edge_case"]
            ai_feedback = (
                f"### ❌ Edge-Case Counter-Example\n\n"
                f"Your code failed on a hidden edge case. Here is a minimal reproducible scenario:\n\n"
                f"- **Input**: `{ec['input']}`\n"
                f"- **Expected Output**: `{ec['expected_output']}`\n\n"
                f"**Pedagogical Guidance**: {ec['reasoning']}"
            )
            suggested_refactor = "// Check edge case bounds (e.g. N=1, negative numbers, overflow)"
            quality_score = 60.0
            metrics = edge_res["metrics"]

        # 3. Accepted: Multi-Agent Review Panel & pgvector Plagiarism Check
        else:
            # Plagiarism & Logic-Clone Check
            plag_res = await PlagiarismDetector.check_and_embed(session, submission)
            
            # Dream Team Panel
            review_res = MultiAgentReviewPanel.synthesize_review(code, lang)
            ai_feedback = review_res["ai_feedback"]
            suggested_refactor = review_res["suggested_refactoring"]
            quality_score = review_res["code_quality_score"]
            metrics = review_res["metrics"]

            if plag_res["is_plagiarized"]:
                ai_feedback += (
                    f"\n\n> ⚠️ **Plagiarism Alert**: pgvector similarity check detected a "
                    f"`{plag_res['similarity_score'] * 100:.1f}%` logic-clone match with "
                    f"Submission #{plag_res['flagged_submission_id']}."
                )

        # 4. Save or Update AIReview record in Database
        stmt_rev = select(AIReview).where(AIReview.submission_id == submission_id)
        res_rev = await session.execute(stmt_rev)
        existing_review = res_rev.scalar_one_or_none()

        if existing_review:
            existing_review.ai_feedback = ai_feedback
            existing_review.suggested_refactoring = suggested_refactor
            existing_review.code_quality_score = quality_score
        else:
            new_review = AIReview(
                submission_id=submission_id,
                ai_feedback=ai_feedback,
                suggested_refactoring=suggested_refactor,
                code_quality_score=quality_score
            )
            session.add(new_review)

        await session.commit()

        # Publish AI completion event to Redis Pub/Sub
        await _publish_event(submission_id, {
            "event": "AI_REVIEW_COMPLETED",
            "submission_id": submission_id,
            "code_quality_score": quality_score,
            "metrics": metrics
        })


@celery_app.task(bind=True, name="app.tasks.ai.analyze_submission_task")
def analyze_submission_task(self, task_id: str, submission_id: int) -> Dict[str, Any]:
    """
    Celery task for AI Analysis Workflows in `q_ai_analysis`.
    """
    asyncio.run(_analyze_submission_async(task_id, submission_id))
    return {"status": "AI Analysis completed", "submission_id": submission_id}
