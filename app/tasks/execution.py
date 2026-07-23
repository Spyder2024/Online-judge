import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.ai import AsyncTaskLog, TaskStatus
from app.models.submission import Submission, SubmissionVerdict
from app.models.problem import Problem, TestCase
from app.services.sandbox import SandboxEngine, ExecutionResult


import json
import redis.asyncio as aioredis
from app.core.config import settings

async def _publish_event(submission_id: int, event_data: dict):
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.publish(f"submission_{submission_id}", json.dumps(event_data))
        await r.aclose()
    except Exception:
        pass


async def _evaluate_submission_async(task_id: str, submission_id: int) -> None:
    """Async wrapper to handle DB operations and trigger sandbox with real-time Pub/Sub streaming."""
    async with async_session_maker() as session:
        # 1. Update Async Task Log to PROCESSING
        result = await session.execute(select(AsyncTaskLog).where(AsyncTaskLog.task_id == task_id))
        task_log = result.scalar_one_or_none()
        if not task_log:
            return  # Invalid task log
            
        task_log.status = TaskStatus.PROCESSING
        await session.commit()
        await _publish_event(submission_id, {"event": "PROCESSING", "submission_id": submission_id})
        
        # 2. Fetch Submission, Problem, and Test Cases
        result = await session.execute(
            select(Submission)
            .options(selectinload(Submission.problem).selectinload(Problem.test_cases))
            .where(Submission.submission_id == submission_id)
        )
        submission = result.scalar_one_or_none()
        
        if not submission or not submission.problem:
            task_log.status = TaskStatus.FAILED
            task_log.error_message = "Submission or Problem not found"
            task_log.completed_at = datetime.now(timezone.utc)
            await session.commit()
            await _publish_event(submission_id, {"event": "FAILED", "error": "Submission or Problem not found"})
            return

        problem = submission.problem
        test_cases = problem.test_cases

        # Initialize Sandbox Engine
        engine = SandboxEngine(
            submission_id=submission.submission_id,
            code=submission.code,
            language=submission.language_enum,
            time_limit=problem.time_limit,
            memory_limit=problem.memory_limit
        )

        try:
            # Stage code to temporary directory
            engine.stage()
            await _publish_event(submission_id, {"event": "COMPILING", "language": submission.language_enum.value})
            
            # Compile
            compilation_success, compile_err = engine.compile()
            if not compilation_success:
                submission.verdict = SubmissionVerdict.COMPILATION_ERROR
                task_log.result = {"error": compile_err}
                task_log.status = TaskStatus.COMPLETED
                await _publish_event(submission_id, {
                    "event": "COMPLETED",
                    "verdict": SubmissionVerdict.COMPILATION_ERROR.value,
                    "error": compile_err
                })
            else:
                # Execute Test Cases
                max_time_ms = 0.0
                max_mem_kb = 0
                final_verdict = SubmissionVerdict.ACCEPTED
                total_tc = len(test_cases)
                
                for idx, tc in enumerate(test_cases, start=1):
                    await _publish_event(submission_id, {
                        "event": "EVALUATING_TESTCASE",
                        "current_testcase": idx,
                        "total_testcases": total_tc
                    })
                    
                    exec_result = engine.execute_test_case(tc.input_text, tc.output_text)
                    
                    max_time_ms = max(max_time_ms, exec_result.execution_time_ms)
                    max_mem_kb = max(max_mem_kb, exec_result.memory_consumed_kb)
                    
                    if exec_result.verdict != SubmissionVerdict.ACCEPTED:
                        final_verdict = exec_result.verdict
                        task_log.result = {"error": exec_result.error_message, "failed_test_case": tc.test_case_id}
                        break
                
                submission.verdict = final_verdict
                submission.execution_time = max_time_ms
                submission.memory_consumed = max_mem_kb
                task_log.status = TaskStatus.COMPLETED
                if not task_log.result:
                    task_log.result = {"message": "All test cases passed."}
                
                await _publish_event(submission_id, {
                    "event": "COMPLETED",
                    "verdict": final_verdict.value,
                    "execution_time_ms": max_time_ms,
                    "memory_consumed_kb": max_mem_kb
                })
                    
        except Exception as e:
            submission.verdict = SubmissionVerdict.RUNTIME_ERROR
            task_log.status = TaskStatus.FAILED
            task_log.error_message = str(e)
            await _publish_event(submission_id, {"event": "FAILED", "error": str(e)})
        finally:
            engine.teardown()
            task_log.completed_at = datetime.now(timezone.utc)
            await session.commit()


@celery_app.task(bind=True, name="app.tasks.execution.evaluate_submission_task")
def evaluate_submission_task(self, task_id: str, submission_id: int) -> Dict[str, Any]:
    """
    Celery task orchestrating the submission evaluation process.
    Dispatched to the `q_compile_exec` queue on high-CPU nodes.
    """
    asyncio.run(_evaluate_submission_async(task_id, submission_id))
    return {"status": "Evaluation completed", "submission_id": submission_id}
