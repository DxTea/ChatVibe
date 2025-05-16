"""Add file_path to messages table

Revision ID: 9737e97f481d
Revises: 5f5a4a35d91a
Create Date: 2025-05-16 02:03:45.883862

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9737e97f481d'
down_revision: Union[str, None] = '5f5a4a35d91a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('messages', sa.Column('file_path', sa.String(), nullable=True))

def downgrade():
    op.drop_column('messages', 'file_path')