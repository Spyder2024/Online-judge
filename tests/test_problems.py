import unittest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models.problem import Problem, ProblemDifficulty
from app.schemas.problem import ProblemCreate
from app.api.v1.problems import SemanticSearchRequest


class TestProblemsLogic(unittest.TestCase):
    """Unit tests for problem models, difficulty mappings, and semantic search queries."""

    def test_problem_create_schema_valid(self):
        prob_in = ProblemCreate(
            title="Two Sum II",
            statement_text="Find two numbers such that they add up to target.",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.5,
            memory_limit=256
        )
        self.assertEqual(prob_in.title, "Two Sum II")
        self.assertEqual(prob_in.difficulty, ProblemDifficulty.MEDIUM)
        self.assertEqual(prob_in.time_limit, 1.5)

    def test_semantic_search_request_validation(self):
        # Valid query
        req = SemanticSearchRequest(query="find dynamic programming shortest path", limit=5)
        self.assertEqual(req.query, "find dynamic programming shortest path")
        self.assertEqual(req.limit, 5)

        # Missing query raises ValidationError
        with self.assertRaises(ValidationError):
            SemanticSearchRequest.model_validate({})

    def test_problem_soft_delete_model(self):
        problem = Problem(
            problem_id=99,
            title="Archived Challenge",
            statement_text="Old contest problem",
            difficulty=ProblemDifficulty.HARD,
            time_limit=2.0,
            memory_limit=512,
            deleted_at=None
        )
        self.assertIsNone(problem.deleted_at)

        # Simulate soft deletion
        now = datetime.now(timezone.utc)
        problem.deleted_at = now
        self.assertIsNotNone(problem.deleted_at)
        self.assertEqual(problem.deleted_at, now)


if __name__ == "__main__":
    unittest.main()
