"""conversation_and_treatment_intelligence

Revision ID: e3a891d47c02
Revises: c9d50a28957e
Create Date: 2026-09-27 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3a891d47c02'
down_revision: Union[str, Sequence[str], None] = 'c9d50a28957e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add conversational assistant sessions, evidence references, and treatment intelligence."""
    # 1. Policy conversations table
    op.create_table(
        'policy_conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('context_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_policy_conversations_id'), 'policy_conversations', ['id'], unique=False)
    op.create_index(op.f('ix_policy_conversations_policy_id'), 'policy_conversations', ['policy_id'], unique=False)
    op.create_index(op.f('ix_policy_conversations_user_id'), 'policy_conversations', ['user_id'], unique=False)

    # 2. Conversation messages table
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('confidence', sa.String(length=50), nullable=True),
        sa.Column('is_grounded', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('uncertainty_reason', sa.Text(), nullable=True),
        sa.Column('missing_information', sa.JSON(), nullable=True),
        sa.Column('treatment_scenario', sa.JSON(), nullable=True),
        sa.Column('cost_estimate', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['policy_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_conversation_messages_id'), 'conversation_messages', ['id'], unique=False)
    op.create_index(op.f('ix_conversation_messages_conversation_id'), 'conversation_messages', ['conversation_id'], unique=False)

    # 3. Conversation evidence references table
    op.create_table(
        'conversation_evidence_references',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('document_source', sa.String(length=255), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('clause_section', sa.String(length=255), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('interpretation', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['conversation_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_conversation_evidence_references_id'), 'conversation_evidence_references', ['id'], unique=False)
    op.create_index(op.f('ix_conversation_evidence_references_message_id'), 'conversation_evidence_references', ['message_id'], unique=False)
    op.create_index(op.f('ix_conversation_evidence_references_policy_id'), 'conversation_evidence_references', ['policy_id'], unique=False)

    # 4. Treatment costs benchmark catalog table
    op.create_table(
        'treatment_costs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('treatment_id', sa.String(length=100), nullable=False),
        sa.Column('treatment_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('hospital_type', sa.String(length=100), nullable=True),
        sa.Column('inpatient_outpatient', sa.String(length=50), server_default='inpatient', nullable=False),
        sa.Column('min_cost', sa.Float(), nullable=False),
        sa.Column('typical_cost', sa.Float(), nullable=False),
        sa.Column('max_cost', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('length_of_stay_days', sa.Integer(), server_default='1', nullable=False),
        sa.Column('data_source_type', sa.String(length=100), server_default='synthetic_benchmark', nullable=False),
        sa.Column('dataset_version', sa.String(length=50), server_default='1.0.0', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_treatment_costs_id'), 'treatment_costs', ['id'], unique=False)
    op.create_index(op.f('ix_treatment_costs_treatment_id'), 'treatment_costs', ['treatment_id'], unique=True)
    op.create_index(op.f('ix_treatment_costs_treatment_name'), 'treatment_costs', ['treatment_name'], unique=False)
    op.create_index(op.f('ix_treatment_costs_category'), 'treatment_costs', ['category'], unique=False)
    op.create_index(op.f('ix_treatment_costs_city'), 'treatment_costs', ['city'], unique=False)

    # 5. Treatment scenarios table
    op.create_table(
        'treatment_scenarios',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=True),
        sa.Column('treatment_name', sa.String(length=255), nullable=False),
        sa.Column('diagnosis', sa.String(length=255), nullable=True),
        sa.Column('hospital_name', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('hospital_type', sa.String(length=100), nullable=True),
        sa.Column('inpatient_outpatient', sa.String(length=50), server_default='inpatient', nullable=True),
        sa.Column('length_of_stay_days', sa.Integer(), nullable=True),
        sa.Column('patient_age', sa.Integer(), nullable=True),
        sa.Column('quoted_cost', sa.Float(), nullable=False),
        sa.Column('non_payable_items', sa.Float(), server_default='0', nullable=True),
        sa.Column('scenario_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['policy_conversations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_treatment_scenarios_id'), 'treatment_scenarios', ['id'], unique=False)
    op.create_index(op.f('ix_treatment_scenarios_policy_id'), 'treatment_scenarios', ['policy_id'], unique=False)
    op.create_index(op.f('ix_treatment_scenarios_conversation_id'), 'treatment_scenarios', ['conversation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema by dropping conversational and treatment intelligence tables."""
    op.drop_table('treatment_scenarios')
    op.drop_table('treatment_costs')
    op.drop_table('conversation_evidence_references')
    op.drop_table('conversation_messages')
    op.drop_table('policy_conversations')
