"""Initial schema with 13 core/AI tables, pgvector extension, and HNSW cosine distance indexes.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-07-17 01:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector PostgreSQL extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create users table
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "CONTESTANT", "STUDENT", name="userrole"),
            nullable=False,
            server_default="CONTESTANT",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_users_user_id"), "users", ["user_id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # 3. Create problems table with Vector(1536) embedding
    op.create_table(
        "problems",
        sa.Column("problem_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("statement_text", sa.Text(), nullable=False),
        sa.Column(
            "difficulty",
            sa.Enum("EASY", "MEDIUM", "HARD", name="problemdifficulty"),
            nullable=False,
        ),
        sa.Column("time_limit", sa.Float(), nullable=False),
        sa.Column("memory_limit", sa.Integer(), nullable=False),
        sa.Column("problem_embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("problem_id"),
    )
    op.create_index(op.f("ix_problems_problem_id"), "problems", ["problem_id"], unique=False)
    op.create_index(op.f("ix_problems_title"), "problems", ["title"], unique=False)
    # HNSW Cosine Distance Index for problem embedding vector search
    op.create_index(
        "ix_problems_problem_embedding_hnsw",
        "problems",
        ["problem_embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"problem_embedding": "vector_cosine_ops"},
    )

    # 4. Create tags table
    op.create_table(
        "tags",
        sa.Column("tag_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tag_name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("tag_id"),
    )
    op.create_index(op.f("ix_tags_tag_id"), "tags", ["tag_id"], unique=False)
    op.create_index(op.f("ix_tags_tag_name"), "tags", ["tag_name"], unique=True)

    # 5. Create problem_tags composite association table
    op.create_table(
        "problem_tags",
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.problem_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.tag_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("problem_id", "tag_id"),
    )

    # 6. Create test_cases table
    op.create_table(
        "test_cases",
        sa.Column("test_case_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.problem_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("test_case_id"),
    )
    op.create_index(op.f("ix_test_cases_test_case_id"), "test_cases", ["test_case_id"], unique=False)
    op.create_index(op.f("ix_test_cases_problem_id"), "test_cases", ["problem_id"], unique=False)

    # 7. Create submissions table with Vector(1536) embedding
    op.create_table(
        "submissions",
        sa.Column("submission_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column(
            "language_enum",
            sa.Enum("CPP", "PYTHON3", "JAVA", name="languageenum"),
            nullable=False,
        ),
        sa.Column(
            "verdict",
            sa.Enum(
                "PENDING",
                "ACCEPTED",
                "WRONG_ANSWER",
                "TIME_LIMIT_EXCEEDED",
                "MEMORY_LIMIT_EXCEEDED",
                "RUNTIME_ERROR",
                "COMPILATION_ERROR",
                name="submissionverdict",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("execution_time", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("memory_consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("code_embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.problem_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("submission_id"),
    )
    op.create_index(op.f("ix_submissions_submission_id"), "submissions", ["submission_id"], unique=False)
    op.create_index(op.f("ix_submissions_user_id"), "submissions", ["user_id"], unique=False)
    op.create_index(op.f("ix_submissions_problem_id"), "submissions", ["problem_id"], unique=False)
    # HNSW Cosine Distance Index for code embedding vector search
    op.create_index(
        "ix_submissions_code_embedding_hnsw",
        "submissions",
        ["code_embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"code_embedding": "vector_cosine_ops"},
    )

    # 8. Create ai_reviews table (Section 3.C.2 HLD)
    op.create_table(
        "ai_reviews",
        sa.Column("review_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("ai_feedback", sa.Text(), nullable=False),
        sa.Column("suggested_refactoring", sa.Text(), nullable=False),
        sa.Column("code_quality_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.submission_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index(op.f("ix_ai_reviews_review_id"), "ai_reviews", ["review_id"], unique=False)
    op.create_index(op.f("ix_ai_reviews_submission_id"), "ai_reviews", ["submission_id"], unique=True)

    # 9. Create contests table
    op.create_table(
        "contests",
        sa.Column("contest_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("contest_id"),
    )
    op.create_index(op.f("ix_contests_contest_id"), "contests", ["contest_id"], unique=False)
    op.create_index(op.f("ix_contests_title"), "contests", ["title"], unique=False)

    # 10. Create contest_problems composite association table
    op.create_table(
        "contest_problems",
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("points_value", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["contest_id"], ["contests.contest_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.problem_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("contest_id", "problem_id"),
    )

    # 11. Create contest_leaderboard table
    op.create_table(
        "contest_leaderboard",
        sa.Column("leaderboard_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("penalty_time", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contest_id"], ["contests.contest_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("leaderboard_id"),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_user_leaderboard"),
    )
    op.create_index(op.f("ix_contest_leaderboard_leaderboard_id"), "contest_leaderboard", ["leaderboard_id"], unique=False)
    op.create_index(op.f("ix_contest_leaderboard_contest_id"), "contest_leaderboard", ["contest_id"], unique=False)
    op.create_index(op.f("ix_contest_leaderboard_user_id"), "contest_leaderboard", ["user_id"], unique=False)

    # 12. Create knowledge_base_hints table with Vector(1536) (Section 3.C.2 HLD)
    op.create_table(
        "knowledge_base_hints",
        sa.Column("hint_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("hint_level", sa.Integer(), nullable=False),
        sa.Column("hint_content", sa.Text(), nullable=False),
        sa.Column("hint_embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.problem_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("hint_id"),
    )
    op.create_index(op.f("ix_knowledge_base_hints_hint_id"), "knowledge_base_hints", ["hint_id"], unique=False)
    op.create_index(op.f("ix_knowledge_base_hints_problem_id"), "knowledge_base_hints", ["problem_id"], unique=False)
    # HNSW Cosine Distance Index for hint embedding vector search
    op.create_index(
        "ix_hints_hint_embedding_hnsw",
        "knowledge_base_hints",
        ["hint_embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"hint_embedding": "vector_cosine_ops"},
    )

    # 13. Create async_task_logs table (Section 3.C.2 HLD)
    op.create_table(
        "async_task_logs",
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="taskstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index(op.f("ix_async_task_logs_task_id"), "async_task_logs", ["task_id"], unique=False)
    op.create_index(op.f("ix_async_task_logs_task_name"), "async_task_logs", ["task_name"], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of dependencies
    op.drop_index(op.f("ix_async_task_logs_task_name"), table_name="async_task_logs")
    op.drop_index(op.f("ix_async_task_logs_task_id"), table_name="async_task_logs")
    op.drop_table("async_task_logs")

    op.drop_index("ix_hints_hint_embedding_hnsw", table_name="knowledge_base_hints", postgresql_using="hnsw")
    op.drop_index(op.f("ix_knowledge_base_hints_problem_id"), table_name="knowledge_base_hints")
    op.drop_index(op.f("ix_knowledge_base_hints_hint_id"), table_name="knowledge_base_hints")
    op.drop_table("knowledge_base_hints")

    op.drop_index(op.f("ix_contest_leaderboard_user_id"), table_name="contest_leaderboard")
    op.drop_index(op.f("ix_contest_leaderboard_contest_id"), table_name="contest_leaderboard")
    op.drop_index(op.f("ix_contest_leaderboard_leaderboard_id"), table_name="contest_leaderboard")
    op.drop_table("contest_leaderboard")

    op.drop_table("contest_problems")

    op.drop_index(op.f("ix_contests_title"), table_name="contests")
    op.drop_index(op.f("ix_contests_contest_id"), table_name="contests")
    op.drop_table("contests")

    op.drop_index(op.f("ix_ai_reviews_submission_id"), table_name="ai_reviews")
    op.drop_index(op.f("ix_ai_reviews_review_id"), table_name="ai_reviews")
    op.drop_table("ai_reviews")

    op.drop_index("ix_submissions_code_embedding_hnsw", table_name="submissions", postgresql_using="hnsw")
    op.drop_index(op.f("ix_submissions_problem_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_user_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_submission_id"), table_name="submissions")
    op.drop_table("submissions")

    op.drop_index(op.f("ix_test_cases_problem_id"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_test_case_id"), table_name="test_cases")
    op.drop_table("test_cases")

    op.drop_table("problem_tags")

    op.drop_index(op.f("ix_tags_tag_name"), table_name="tags")
    op.drop_index(op.f("ix_tags_tag_id"), table_name="tags")
    op.drop_table("tags")

    op.drop_index("ix_problems_problem_embedding_hnsw", table_name="problems", postgresql_using="hnsw")
    op.drop_index(op.f("ix_problems_title"), table_name="problems")
    op.drop_index(op.f("ix_problems_problem_id"), table_name="problems")
    op.drop_table("problems")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_user_id"), table_name="users")
    op.drop_table("users")

    # Drop custom enums
    sa.Enum(name="taskstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="submissionverdict").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="languageenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="problemdifficulty").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)

    # Disable pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector;")
