"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE IF NOT EXISTS votetype AS ENUM ('up', 'down', 'skip')")
    op.execute("CREATE TYPE IF NOT EXISTS billstatus AS ENUM ('introduced', 'in_committee', 'passed_house', 'passed_senate', 'in_conference', 'passed_both', 'vetoed', 'enacted')")
    
    # Create bills table
    op.create_table('bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('congress', sa.Integer(), nullable=False),
        sa.Column('bill_type', sa.String(length=10), nullable=False),
        sa.Column('bill_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('introduced_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latest_action_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('introduced', 'in_committee', 'passed_house', 'passed_senate', 'in_conference', 'passed_both', 'vetoed', 'enacted', name='billstatus', create_type=False), nullable=True),
        sa.Column('sponsor', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source_urls', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bill_identifier', 'bills', ['congress', 'bill_type', 'bill_number'], unique=True)
    op.create_index(op.f('ix_bills_congress'), 'bills', ['congress'], unique=False)
    op.create_index(op.f('ix_bills_latest_action_date'), 'bills', ['latest_action_date'], unique=False)
    op.create_index(op.f('ix_bills_status'), 'bills', ['status'], unique=False)
    
    # Create bill_versions table
    op.create_table('bill_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_label', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bill_versions_bill_id'), 'bill_versions', ['bill_id'], unique=False)
    
    # Create bill_sections table
    op.create_table('bill_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_key', sa.String(length=100), nullable=True),
        sa.Column('heading', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('section_text', sa.Text(), nullable=False),
        sa.Column('section_text_hash', sa.String(length=64), nullable=True),
        sa.Column('summary_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('evidence_quotes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bill_section_order', 'bill_sections', ['bill_id', 'order_index'], unique=False)
    op.create_index(op.f('ix_bill_sections_bill_id'), 'bill_sections', ['bill_id'], unique=False)
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('is_anonymous', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_session_id'), 'users', ['session_id'], unique=True)
    
    # Create votes table
    op.create_table('votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vote', sa.Enum('up', 'down', 'skip', name='votetype', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
        sa.ForeignKeyConstraint(['section_id'], ['bill_sections.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_section_vote', 'votes', ['user_id', 'section_id'], unique=True)
    op.create_index(op.f('ix_votes_bill_id'), 'votes', ['bill_id'], unique=False)
    op.create_index(op.f('ix_votes_section_id'), 'votes', ['section_id'], unique=False)
    op.create_index(op.f('ix_votes_user_id'), 'votes', ['user_id'], unique=False)
    
    # Create user_bill_summaries table
    op.create_table('user_bill_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('upvote_count', sa.Integer(), nullable=True),
        sa.Column('downvote_count', sa.Integer(), nullable=True),
        sa.Column('skip_count', sa.Integer(), nullable=True),
        sa.Column('upvote_ratio', sa.Float(), nullable=True),
        sa.Column('verdict_label', sa.String(length=50), nullable=True),
        sa.Column('liked_sections', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('disliked_sections', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_bill_summary', 'user_bill_summaries', ['user_id', 'bill_id'], unique=True)
    op.create_index(op.f('ix_user_bill_summaries_bill_id'), 'user_bill_summaries', ['bill_id'], unique=False)
    op.create_index(op.f('ix_user_bill_summaries_user_id'), 'user_bill_summaries', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('user_bill_summaries')
    op.drop_table('votes')
    op.drop_table('users')
    op.drop_table('bill_sections')
    op.drop_table('bill_versions')
    op.drop_table('bills')
    op.execute('DROP TYPE votetype')
    op.execute('DROP TYPE billstatus')
