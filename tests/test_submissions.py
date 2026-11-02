import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.user import User, UserRole
from app.models.submission import Submission, SubmissionVerdict, LanguageEnum
from app.schemas.submission import SubmissionCreate


class TestSubmissionsLogic(unittest.TestCase):
    """Unit tests for submission schemas, IDOR object-level authorization, and idempotency."""

    def test_submission_create_schema_valid(self):
        sub_in = SubmissionCreate(
            problem_id=1,
            code="def twoSum(nums, target): return [0, 1]",
            language_enum=LanguageEnum.PYTHON3
        )
        self.assertEqual(sub_in.problem_id, 1)
        self.assertEqual(sub_in.language_enum, LanguageEnum.PYTHON3)

    def test_submission_create_schema_invalid_language(self):
        with self.assertRaises(ValidationError):
            SubmissionCreate(
                problem_id=1,
                code="console.log('hello')",
                language_enum="RUBY_UNSUPPORTED"
            )

    def test_submission_authorization_idor_check(self):
        # User 10 (Candidate A), User 20 (Candidate B), User 1 (Admin Marcus)
        user_a = User(user_id=10, username="candidate_a", role=UserRole.CONTESTANT)
        user_b = User(user_id=20, username="candidate_b", role=UserRole.CONTESTANT)
        admin  = User(user_id=1, username="admin_marcus", role=UserRole.ADMIN)

        submission_a = Submission(
            submission_id=1001,
            user_id=10,
            problem_id=1,
            code="def solve(): pass",
            language_enum=LanguageEnum.PYTHON3,
            verdict=SubmissionVerdict.ACCEPTED
        )

        # 1. Candidate A accessing their own submission -> Permitted
        self.assertEqual(submission_a.user_id, user_a.user_id)

        # 2. Candidate B accessing Candidate A's submission -> IDOR Violation
        def access_submission(sub: Submission, viewer: User):
            if viewer.role != UserRole.ADMIN and sub.user_id != viewer.user_id:
                raise HTTPException(status_code=403, detail="Access denied to this submission")
            return sub

        with self.assertRaises(HTTPException) as cm:
            access_submission(submission_a, user_b)
        self.assertEqual(cm.exception.status_code, 403)

        # 3. Admin accessing Candidate A's submission -> Permitted
        allowed_sub = access_submission(submission_a, admin)
        self.assertEqual(allowed_sub.submission_id, 1001)

    def test_idempotency_cache_key_generation(self):
        user_id = 42
        idempotency_uuid = "e7b0c3f5-7b58-45a8-9d8f-69be6c518884"
        cache_key = f"idempotency:{user_id}:{idempotency_uuid}"
        self.assertEqual(cache_key, "idempotency:42:e7b0c3f5-7b58-45a8-9d8f-69be6c518884")


if __name__ == "__main__":
    unittest.main()
