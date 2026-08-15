"""create notes table

Revision ID: 8896812e8bac
Revises: 
Create Date: 2026-08-14 14:31:15.142255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revisions-Kennungen, von Alembic verwendet.
revision: str = '8896812e8bac'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('notes')