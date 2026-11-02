import unittest
from app.models.submission import SubmissionVerdict
from app.models.problem import ProblemDifficulty


def evaluate_run(time_taken: float, time_limit: float, memory_kb: int, memory_limit_mb: int, exit_code: int, user_out: str, expected_out: str) -> SubmissionVerdict:
    """Core evaluation verdict decision tree."""
    if exit_code != 0:
        return SubmissionVerdict.RUNTIME_ERROR
    if time_taken > time_limit:
        return SubmissionVerdict.TIME_LIMIT_EXCEEDED
    if (memory_kb / 1024.0) > memory_limit_mb:
        return SubmissionVerdict.MEMORY_LIMIT_EXCEEDED
    if user_out.strip() != expected_out.strip():
        return SubmissionVerdict.WRONG_ANSWER
    return SubmissionVerdict.ACCEPTED


def calculate_icpc_score(problems_solved: int, time_minutes: int, penalty_per_failed: int, failed_attempts: int) -> int:
    """Calculate ICPC style contest penalty score."""
    if problems_solved == 0:
        return 0
    return time_minutes + (penalty_per_failed * failed_attempts)


class TestJudgeVerdicts(unittest.TestCase):
    """Unit tests for judge verdict transitions, runtime thresholds, and contest scoring."""

    def test_accepted_verdict(self):
        verdict = evaluate_run(
            time_taken=0.12,
            time_limit=1.0,
            memory_kb=15400,
            memory_limit_mb=256,
            exit_code=0,
            user_out="[0, 1]\n",
            expected_out="[0, 1]",
        )
        self.assertEqual(verdict, SubmissionVerdict.ACCEPTED)

    def test_wrong_answer_verdict(self):
        verdict = evaluate_run(
            time_taken=0.08,
            time_limit=1.0,
            memory_kb=14000,
            memory_limit_mb=256,
            exit_code=0,
            user_out="[1, 2]",
            expected_out="[0, 1]",
        )
        self.assertEqual(verdict, SubmissionVerdict.WRONG_ANSWER)

    def test_time_limit_exceeded_verdict(self):
        verdict = evaluate_run(
            time_taken=2.05,
            time_limit=2.0,
            memory_kb=12000,
            memory_limit_mb=256,
            exit_code=0,
            user_out="[0, 1]",
            expected_out="[0, 1]",
        )
        self.assertEqual(verdict, SubmissionVerdict.TIME_LIMIT_EXCEEDED)

    def test_memory_limit_exceeded_verdict(self):
        verdict = evaluate_run(
            time_taken=0.5,
            time_limit=2.0,
            memory_kb=300000,  # ~293 MB > 256 MB
            memory_limit_mb=256,
            exit_code=0,
            user_out="[0, 1]",
            expected_out="[0, 1]",
        )
        self.assertEqual(verdict, SubmissionVerdict.MEMORY_LIMIT_EXCEEDED)

    def test_runtime_error_verdict(self):
        verdict = evaluate_run(
            time_taken=0.01,
            time_limit=1.0,
            memory_kb=8000,
            memory_limit_mb=256,
            exit_code=139,  # Segfault
            user_out="",
            expected_out="[0, 1]",
        )
        self.assertEqual(verdict, SubmissionVerdict.RUNTIME_ERROR)

    def test_contest_score_calculation(self):
        # 1 problem solved at minute 45 with 2 failed attempts (20 min penalty each)
        score = calculate_icpc_score(problems_solved=1, time_minutes=45, penalty_per_failed=20, failed_attempts=2)
        self.assertEqual(score, 85)

        # 0 problems solved has 0 penalty regardless of failed attempts
        zero_score = calculate_icpc_score(problems_solved=0, time_minutes=120, penalty_per_failed=20, failed_attempts=5)
        self.assertEqual(zero_score, 0)


if __name__ == "__main__":
    unittest.main()
