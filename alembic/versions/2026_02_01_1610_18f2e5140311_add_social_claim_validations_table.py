"""add_social_claim_validations_table

Revision ID: 18f2e5140311
Revises: create_motivational_model_tables
Create Date: 2026-02-01 16:10:33.229914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18f2e5140311'
down_revision: Union[str, None] = 'create_motivational_model_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'social_claim_validations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_platform', sa.String(50), nullable=False),
        sa.Column('source_post_id', sa.String(255), nullable=False),
        sa.Column('source_agent_name', sa.String(255), nullable=True),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('validation_status', sa.Enum('verified', 'unverified', 'contradicted', 'untestable', name='validation_status_enum'), nullable=False),
        sa.Column('supporting_evidence', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('validator_agent_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['validator_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_social_claim_platform', 'social_claim_validations', ['source_platform'])
    op.create_index('idx_social_claim_status', 'social_claim_validations', ['validation_status'])
    op.create_index('idx_social_claim_created', 'social_claim_validations', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_social_claim_created', 'social_claim_validations')
    op.drop_index('idx_social_claim_status', 'social_claim_validations')
    op.drop_index('idx_social_claim_platform', 'social_claim_validations')
    op.drop_table('social_claim_validations')
    op.execute('DROP TYPE validation_status_enum')
