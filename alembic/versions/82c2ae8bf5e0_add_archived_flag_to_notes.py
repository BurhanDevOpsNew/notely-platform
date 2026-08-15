"""add archived flag to notes

Revision ID: 82c2ae8bf5e0
Revises: 8896812e8bac
Create Date: 2026-08-16 00:57:11.088173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revisions-Kennungen, von Alembic verwendet.
revision: str = '82c2ae8bf5e0'
down_revision: Union[str, None] = '8896812e8bac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'notes',
        sa.Column('archived', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('notes', 'archived')