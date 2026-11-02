"""composite_indexes_and_soft_delete

Revision ID: e4a19b52c019
Revises: d39e30e14184
Create Date: 2026-11-02 16:00:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a19b52c019'
down_revision: Union[str, None] = 'd39e30e14184'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add soft delete column `deleted_at` to users and problems
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)

    op.add_column('problems', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_problems_deleted_at'), 'problems', ['deleted_at'], unique=False)

    # 2. Add composite indexes for high-throughput query paths
    op.create_index(
        'ix_submissions_user_problem_created',
        'submissions',
        ['user_id', 'problem_id', sa.text('created_at DESC')],
        unique=False
    )

    op.create_index(
        'ix_submissions_verdict_created',
        'submissions',
        ['verdict', sa.text('created_at DESC')],
        unique=False
    )

    op.create_index(
        'ix_problems_difficulty_created',
        'problems',
        ['difficulty', sa.text('created_at DESC')],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_problems_difficulty_created', table_name='problems')
    op.drop_index('ix_submissions_verdict_created', table_name='submissions')
    op.drop_index('ix_submissions_user_problem_created', table_name='submissions')
    op.drop_index(op.f('ix_problems_deleted_at'), table_name='problems')
    op.drop_column('problems', 'deleted_at')
    op.drop_index(op.f('ix_users_deleted_at'), table_name='users')
    op.drop_column('users', 'deleted_at')
