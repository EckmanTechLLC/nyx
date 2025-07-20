"""Fix prompt template unique constraint for versioning

Revision ID: 5f861654a180
Revises: 0a3b29465901
Create Date: 2025-07-19 14:02:48.977223

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f861654a180'
down_revision: Union[str, None] = '0a3b29465901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing unique constraint on name
    op.drop_constraint('prompt_templates_name_key', 'prompt_templates', type_='unique')
    
    # Create new unique constraint on (name, version)
    op.create_unique_constraint('prompt_templates_name_version_key', 'prompt_templates', ['name', 'version'])


def downgrade() -> None:
    # Drop the new unique constraint
    op.drop_constraint('prompt_templates_name_version_key', 'prompt_templates', type_='unique')
    
    # Recreate the old unique constraint (this might fail if multiple versions exist)
    op.create_unique_constraint('prompt_templates_name_key', 'prompt_templates', ['name'])
