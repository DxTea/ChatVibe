"""Add is_read to messages

Revision ID: 5f5a4a35d91a
Revises: 2c9596112348
Create Date: 2025-05-16 00:23:04.577874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f5a4a35d91a'
down_revision: Union[str, None] = '2c9596112348'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Adding is_read column to messages table
    op.add_column('messages', sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'))
    # Set existing messages as read
    op.execute("UPDATE messages SET is_read = true")

def downgrade():
    # Remove is_read column
    op.drop_column('messages', 'is_read')
