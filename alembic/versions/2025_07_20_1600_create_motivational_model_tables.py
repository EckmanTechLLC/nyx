"""Create motivational model tables

Revision ID: create_motivational_model_tables
Revises: b8d9cdf757ae
Create Date: 2025-07-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_motivational_model_tables'
down_revision: Union[str, None] = 'b8d9cdf757ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create motivational_states table
    op.create_table('motivational_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('motivation_type', sa.String(length=50), nullable=False),
        sa.Column('urgency', sa.Float(), nullable=False),
        sa.Column('satisfaction', sa.Float(), nullable=False),
        sa.Column('decay_rate', sa.Float(), nullable=False),
        sa.Column('boost_factor', sa.Float(), nullable=False),
        sa.Column('trigger_condition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_satisfied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('max_urgency', sa.Float(), nullable=True),
        sa.Column('min_satisfaction', sa.Float(), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=True),
        sa.Column('failure_count', sa.Integer(), nullable=True),
        sa.Column('total_attempts', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.CheckConstraint('urgency >= 0.0 AND urgency <= 1.0', name='check_motivational_states_urgency_range'),
        sa.CheckConstraint('satisfaction >= 0.0 AND satisfaction <= 1.0', name='check_motivational_states_satisfaction_range'),
        sa.CheckConstraint('decay_rate >= 0.0 AND decay_rate <= 1.0', name='check_motivational_states_decay_rate_range'),
        sa.CheckConstraint('success_rate >= 0.0 AND success_rate <= 1.0', name='check_motivational_states_success_rate_range'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_motivational_states_active', 'motivational_states', ['is_active'], unique=False)
    op.create_index('idx_motivational_states_last_triggered', 'motivational_states', ['last_triggered_at'], unique=False)
    op.create_index('idx_motivational_states_satisfaction', 'motivational_states', ['satisfaction'], unique=False)
    op.create_index('idx_motivational_states_type', 'motivational_states', ['motivation_type'], unique=False)
    op.create_index('idx_motivational_states_urgency', 'motivational_states', ['urgency'], unique=False)

    # Create motivational_tasks table
    op.create_table('motivational_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('motivational_state_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('thought_tree_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generated_prompt', sa.Text(), nullable=False),
        sa.Column('task_priority', sa.Float(), nullable=False),
        sa.Column('arbitration_score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('spawned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('outcome_score', sa.Float(), nullable=True),
        sa.Column('satisfaction_gain', sa.Float(), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("status IN ('generated', 'queued', 'spawned', 'active', 'completed', 'failed', 'cancelled')", name='check_motivational_tasks_status'),
        sa.CheckConstraint('task_priority >= 0.0 AND task_priority <= 1.0', name='check_motivational_tasks_priority_range'),
        sa.ForeignKeyConstraint(['motivational_state_id'], ['motivational_states.id'], ),
        sa.ForeignKeyConstraint(['thought_tree_id'], ['thought_trees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_motivational_tasks_priority', 'motivational_tasks', ['task_priority'], unique=False)
    op.create_index('idx_motivational_tasks_spawned_at', 'motivational_tasks', ['spawned_at'], unique=False)
    op.create_index('idx_motivational_tasks_state_id', 'motivational_tasks', ['motivational_state_id'], unique=False)
    op.create_index('idx_motivational_tasks_status', 'motivational_tasks', ['status'], unique=False)
    op.create_index('idx_motivational_tasks_thought_tree_id', 'motivational_tasks', ['thought_tree_id'], unique=False)


def downgrade() -> None:
    # Drop motivational_tasks table
    op.drop_index('idx_motivational_tasks_thought_tree_id', table_name='motivational_tasks')
    op.drop_index('idx_motivational_tasks_status', table_name='motivational_tasks')
    op.drop_index('idx_motivational_tasks_state_id', table_name='motivational_tasks')
    op.drop_index('idx_motivational_tasks_spawned_at', table_name='motivational_tasks')
    op.drop_index('idx_motivational_tasks_priority', table_name='motivational_tasks')
    op.drop_table('motivational_tasks')
    
    # Drop motivational_states table
    op.drop_index('idx_motivational_states_urgency', table_name='motivational_states')
    op.drop_index('idx_motivational_states_type', table_name='motivational_states')
    op.drop_index('idx_motivational_states_satisfaction', table_name='motivational_states')
    op.drop_index('idx_motivational_states_last_triggered', table_name='motivational_states')
    op.drop_index('idx_motivational_states_active', table_name='motivational_states')
    op.drop_table('motivational_states')