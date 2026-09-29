"""universal_policy_ingestion_and_active_policy

Revision ID: b7e91234c01d
Revises: a4b78c91d20e
Create Date: 2026-09-29 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e91234c01d'
down_revision: Union[str, Sequence[str], None] = 'a4b78c91d20e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add universal policy ingestion fields, active policy tracking, and contractual rule attributes."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('active_policy_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('policies') as batch_op:
        batch_op.add_column(sa.Column('sum_insured', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('policy_start_date', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('policy_end_date', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('document_hash', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('extraction_confidence', sa.Float(), nullable=True))
        batch_op.create_index('ix_policies_document_hash', ['document_hash'], unique=False)

    with op.batch_alter_table('coverage_rules') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('procedure_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('rule_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('coverage_percentage', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('coverage_limit_amount', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('coverage_limit_percentage_of_si', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('unit_frequency', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('deductible_status', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('network_condition', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('waiting_period_type', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('conditions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('source_type', sa.String(length=50), server_default='contractual_rule', nullable=False))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))
        batch_op.create_index('ix_coverage_rules_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_coverage_rules_procedure_name', ['procedure_name'], unique=False)
        batch_op.create_index('ix_coverage_rules_source_type', ['source_type'], unique=False)

    with op.batch_alter_table('evidence_references') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('source_type', sa.String(length=50), server_default='contractual_rule', nullable=False))
        batch_op.create_index('ix_evidence_references_user_id', ['user_id'], unique=False)

    with op.batch_alter_table('policy_analyses') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.create_index('ix_policy_analyses_user_id', ['user_id'], unique=False)

    with op.batch_alter_table('simulations') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.create_index('ix_simulations_user_id', ['user_id'], unique=False)

    with op.batch_alter_table('treatment_scenarios') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.create_index('ix_treatment_scenarios_user_id', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema removing universal policy ingestion fields."""
    with op.batch_alter_table('treatment_scenarios') as batch_op:
        batch_op.drop_index('ix_treatment_scenarios_user_id')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('simulations') as batch_op:
        batch_op.drop_index('ix_simulations_user_id')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('policy_analyses') as batch_op:
        batch_op.drop_index('ix_policy_analyses_user_id')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('evidence_references') as batch_op:
        batch_op.drop_index('ix_evidence_references_user_id')
        batch_op.drop_column('source_type')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('coverage_rules') as batch_op:
        batch_op.drop_index('ix_coverage_rules_source_type')
        batch_op.drop_index('ix_coverage_rules_procedure_name')
        batch_op.drop_index('ix_coverage_rules_user_id')
        batch_op.drop_column('confidence')
        batch_op.drop_column('source_type')
        batch_op.drop_column('conditions')
        batch_op.drop_column('waiting_period_type')
        batch_op.drop_column('network_condition')
        batch_op.drop_column('deductible_status')
        batch_op.drop_column('unit_frequency')
        batch_op.drop_column('coverage_limit_percentage_of_si')
        batch_op.drop_column('coverage_limit_amount')
        batch_op.drop_column('coverage_percentage')
        batch_op.drop_column('rule_name')
        batch_op.drop_column('procedure_name')
        batch_op.drop_column('category')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('policies') as batch_op:
        batch_op.drop_index('ix_policies_document_hash')
        batch_op.drop_column('extraction_confidence')
        batch_op.drop_column('document_hash')
        batch_op.drop_column('policy_end_date')
        batch_op.drop_column('policy_start_date')
        batch_op.drop_column('sum_insured')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('active_policy_id')
