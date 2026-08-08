import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
import redis.asyncio as aioredis

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.ai import AsyncTaskLog, TaskStatus
from app.models.submission import Submission, SubmissionVerdict
from app.models.problem import Problem, TestCase
from app.services.sandbox import SandboxEngine, ExecutionResult

logger = logging.getLogger(__name__)


async def _publish_event(submission_id: int, event_data: dict):
    """
    Publish real-time evaluation state updates and failure events to Redis Pub/Sub channel.
    WebSocket subscribers consume these events for live UI progress updates.
    """
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.publish(f"submission_{submission_id}", json.dumps(event_data))
        await r.aclose()
    except Exception as exc:
        logger.warning(f"[Celery Worker #{submission_id}] Redis pub/sub error: {exc}")


async def _evaluate_submission_async(task_id: str, submission_id: int) -> None:
    """
    Async core execution worker routine:
    Directive 1: Default verdict MUST NOT be ACCEPTED. It defaults to WRONG_ANSWER and only
    becomes ACCEPTED if and only if all_tests_passed remains True after evaluating every test case.
    """
    async with async_session_maker() as session:
        # 1. Update Async Task Log to PROCESSING
        result = await session.execute(select(AsyncTaskLog).where(AsyncTaskLog.task_id == task_id))
        task_log = result.scalar_one_or_none()
        if not task_log:
            logger.error(f"Task log ID {task_id} not found.")
            return

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

        logger.info(f"[Celery Worker] Evaluating Submission #{submission_id} (Language: {submission.language_enum.value})")

        # Initialize Sandbox Engine
        engine = SandboxEngine(
            submission_id=submission.submission_id,
            code=submission.code,
            language=submission.language_enum,
            time_limit=problem.time_limit,
            memory_limit=problem.memory_limit
        )

        try:
            engine.stage()
            await _publish_event(submission_id, {"event": "COMPILING", "language": submission.language_enum.value})

            # Check compile readiness
            compilation_success, compile_err = engine.compile()
            if not compilation_success:
                submission.verdict = SubmissionVerdict.COMPILATION_ERROR
                task_log.result = {"error": compile_err}
                task_log.status = TaskStatus.COMPLETED
                logger.warning(f"[Celery Worker #{submission_id}] Compilation failed: {compile_err}")
                await _publish_event(submission_id, {
                    "event": "COMPLETED",
                    "verdict": SubmissionVerdict.COMPILATION_ERROR.value,
                    "error": compile_err
                })
            else:
                max_time_ms = 0.0
                max_mem_kb = 0
                total_tc = len(test_cases)
                
                # Directive 1: Default to WRONG_ANSWER; only ACCEPTED if all_tests_passed is True
                final_verdict = SubmissionVerdict.WRONG_ANSWER
                all_tests_passed = False

                if total_tc == 0:
                    task_log.result = {"error": "No test cases configured for this problem."}
                else:
                    all_tests_passed = True
                    for idx, tc in enumerate(test_cases, start=1):
                        await _publish_event(submission_id, {
                            "event": "EVALUATING_TESTCASE",
                            "current_testcase": idx,
                            "total_testcases": total_tc
                        })

                        # Execute single testcase
                        exec_result: ExecutionResult = await engine.execute_test_case_remote_async(
                            tc.input_text, tc.output_text
                        )

                        max_time_ms = max(max_time_ms, exec_result.execution_time_ms)
                        max_mem_kb = max(max_mem_kb, exec_result.memory_consumed_kb)

                        # Directive 1 & 2: Instantly fail loop on any non-ACCEPTED verdict
                        if exec_result.verdict != SubmissionVerdict.ACCEPTED:
                            all_tests_passed = False
                            final_verdict = exec_result.verdict
                            task_log.result = {
                                "error": exec_result.error_message or f"Failed at testcase #{idx}",
                                "failed_test_case": tc.test_case_id,
                                "verdict": exec_result.verdict.value
                            }
                            logger.warning(
                                f"[Celery Worker #{submission_id}] Test Case #{idx} Failed -> Verdict: {exec_result.verdict.value} | Error: {exec_result.error_message}"
                            )
                            await _publish_event(submission_id, {
                                "event": "TESTCASE_FAILED",
                                "current_testcase": idx,
                                "verdict": exec_result.verdict.value,
                                "error": exec_result.error_message
                            })
                            break

                if all_tests_passed and total_tc > 0:
                    final_verdict = SubmissionVerdict.ACCEPTED

                submission.verdict = final_verdict
                submission.execution_time = max_time_ms
                submission.memory_consumed = max_mem_kb
                task_log.status = TaskStatus.COMPLETED
                if not task_log.result:
                    task_log.result = {"message": "All test cases passed cleanly."}

                logger.info(f"[Celery Worker #{submission_id}] Final Verdict: {final_verdict.value}")

                await _publish_event(submission_id, {
                    "event": "COMPLETED",
                    "verdict": final_verdict.value,
                    "execution_time_ms": max_time_ms,
                    "memory_consumed_kb": max_mem_kb
                })

        except Exception as e:
            logger.error(f"[Celery Worker #{submission_id}] Unhandled exception: {e}", exc_info=True)
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
    Celery task orchestrating submission evaluation process.
    Dispatched to `q_compile_exec` queue.
    """
    asyncio.run(_evaluate_submission_async(task_id, submission_id))

    # Auto-trigger AI Analysis Workflow in q_ai_analysis queue
    from app.tasks.ai import analyze_submission_task
    analyze_submission_task.apply_async(args=[task_id, submission_id], queue="q_ai_analysis")

    return {"status": "Evaluation completed", "submission_id": submission_id}
