"""initial_schema

Revision ID: c9d50a28957e
Revises: 
Create Date: 2026-09-27 15:21:38.813532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d50a28957e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema and create initial CoverWise MVP tables."""
    # 1. Policies table
    op.create_table(
        'policies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('policy_number', sa.String(length=100), nullable=True),
        sa.Column('insurer_name', sa.String(length=255), nullable=True),
        sa.Column('plan_name', sa.String(length=255), nullable=True),
        sa.Column('policy_holder_name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='uploaded', nullable=False),
        sa.Column('raw_metadata', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_policies_id'), 'policies', ['id'], unique=False)
    op.create_index(op.f('ix_policies_user_id'), 'policies', ['user_id'], unique=False)
    op.create_index(op.f('ix_policies_policy_number'), 'policies', ['policy_number'], unique=False)
    op.create_index(op.f('ix_policies_insurer_name'), 'policies', ['insurer_name'], unique=False)
    op.create_index(op.f('ix_policies_status'), 'policies', ['status'], unique=False)

    # 2. Treatments catalog table
    op.create_table(
        'treatments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('typical_cost_min', sa.Float(), nullable=True),
        sa.Column('typical_cost_max', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_treatments_id'), 'treatments', ['id'], unique=False)
    op.create_index(op.f('ix_treatments_name'), 'treatments', ['name'], unique=True)
    op.create_index(op.f('ix_treatments_category'), 'treatments', ['category'], unique=False)

    # 3. Policy analyses table
    op.create_table(
        'policy_analyses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('treatment_id', sa.Integer(), nullable=True),
        sa.Column('treatment_name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['treatment_id'], ['treatments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_policy_analyses_id'), 'policy_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_policy_analyses_policy_id'), 'policy_analyses', ['policy_id'], unique=False)
    op.create_index(op.f('ix_policy_analyses_treatment_id'), 'policy_analyses', ['treatment_id'], unique=False)
    op.create_index(op.f('ix_policy_analyses_status'), 'policy_analyses', ['status'], unique=False)

    # 4. Coverage rules table
    op.create_table(
        'coverage_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('coverage_status', sa.String(length=50), server_default='covered', nullable=False),
        sa.Column('deductible', sa.Float(), nullable=True),
        sa.Column('copay', sa.Float(), nullable=True),
        sa.Column('copay_percentage', sa.Float(), nullable=True),
        sa.Column('coverage_limit', sa.Float(), nullable=True),
        sa.Column('exclusions', sa.JSON(), nullable=True),
        sa.Column('waiting_period', sa.String(length=100), nullable=True),
        sa.Column('room_category', sa.String(length=100), nullable=True),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_coverage_rules_id'), 'coverage_rules', ['id'], unique=False)
    op.create_index(op.f('ix_coverage_rules_policy_id'), 'coverage_rules', ['policy_id'], unique=False)
    op.create_index(op.f('ix_coverage_rules_coverage_status'), 'coverage_rules', ['coverage_status'], unique=False)

    # 5. Simulations table
    op.create_table(
        'simulations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=True),
        sa.Column('treatment_id', sa.Integer(), nullable=True),
        sa.Column('treatment_name', sa.String(length=255), nullable=True),
        sa.Column('hospital_quote', sa.Float(), nullable=False),
        sa.Column('room_category', sa.String(length=100), nullable=True),
        sa.Column('deductible', sa.Float(), server_default='0', nullable=True),
        sa.Column('copay', sa.Float(), server_default='0', nullable=True),
        sa.Column('coverage_limit', sa.Float(), nullable=True),
        sa.Column('estimated_insurance_share', sa.Float(), server_default='0', nullable=False),
        sa.Column('estimated_patient_share', sa.Float(), server_default='0', nullable=False),
        sa.Column('calculation_breakdown', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['treatment_id'], ['treatments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_simulations_id'), 'simulations', ['id'], unique=False)
    op.create_index(op.f('ix_simulations_policy_id'), 'simulations', ['policy_id'], unique=False)
    op.create_index(op.f('ix_simulations_treatment_id'), 'simulations', ['treatment_id'], unique=False)

    # 6. Evidence references table
    op.create_table(
        'evidence_references',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=True),
        sa.Column('analysis_id', sa.Integer(), nullable=True),
        sa.Column('document_source', sa.String(length=255), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('clause_section', sa.String(length=255), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('interpretation', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['policy_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['coverage_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evidence_references_id'), 'evidence_references', ['id'], unique=False)
    op.create_index(op.f('ix_evidence_references_policy_id'), 'evidence_references', ['policy_id'], unique=False)
    op.create_index(op.f('ix_evidence_references_rule_id'), 'evidence_references', ['rule_id'], unique=False)
    op.create_index(op.f('ix_evidence_references_analysis_id'), 'evidence_references', ['analysis_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema by dropping tables in reverse order of foreign key dependency."""
    op.drop_table('evidence_references')
    op.drop_table('simulations')
    op.drop_table('coverage_rules')
    op.drop_table('policy_analyses')
    op.drop_table('treatments')
    op.drop_table('policies')
