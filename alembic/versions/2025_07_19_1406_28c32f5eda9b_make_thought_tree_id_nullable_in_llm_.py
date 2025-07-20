"""Make thought_tree_id nullable in llm_interactions

Revision ID: 28c32f5eda9b
Revises: 5f861654a180
Create Date: 2025-07-19 14:06:48.294680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28c32f5eda9b'
down_revision: Union[str, None] = '5f861654a180'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make thought_tree_id nullable in llm_interactions
    op.alter_column('llm_interactions', 'thought_tree_id', nullable=True)


def downgrade() -> None:
    # Make thought_tree_id not nullable again
    op.alter_column('llm_interactions', 'thought_tree_id', nullable=False)
