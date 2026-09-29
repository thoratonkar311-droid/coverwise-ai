"""widen_coverage_rule_text_columns

Revision ID: a4b78c91d20e
Revises: f5b72184a19c
Create Date: 2026-09-28 07:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b78c91d20e'
down_revision: Union[str, Sequence[str], None] = 'f5b72184a19c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen text columns on coverage_rules to support full health policy conditions and citations."""
    with op.batch_alter_table('coverage_rules') as batch_op:
        batch_op.alter_column(
            'waiting_period',
            existing_type=sa.String(length=100),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'room_category',
            existing_type=sa.String(length=100),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'source_reference',
            existing_type=sa.String(length=255),
            type_=sa.String(length=500),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema to restore original column lengths on coverage_rules."""
    with op.batch_alter_table('coverage_rules') as batch_op:
        batch_op.alter_column(
            'source_reference',
            existing_type=sa.String(length=500),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'room_category',
            existing_type=sa.String(length=255),
            type_=sa.String(length=100),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'waiting_period',
            existing_type=sa.String(length=500),
            type_=sa.String(length=100),
            existing_nullable=True,
        )
