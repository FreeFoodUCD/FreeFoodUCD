"""add post feedback table

Revision ID: add_post_feedback
Revises: add_reminder_fields_to_events
Create Date: 2026-02-23 15:07:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_post_feedback'
down_revision = 'add_reminder_fields_to_events'
branch_labels = None
depends_on = None


def upgrade():
    # Create post_feedback table
    op.create_table(
        'post_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('admin_email', sa.String(length=255), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('correct_classification', sa.Boolean(), nullable=True),
        sa.Column('classification_notes', sa.Text(), nullable=True),
        sa.Column('correct_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correct_time', sa.String(length=10), nullable=True),
        sa.Column('correct_location', sa.String(length=255), nullable=True),
        sa.Column('extraction_notes', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_post_feedback_post_id'), 'post_feedback', ['post_id'], unique=False)
    op.create_index(op.f('ix_post_feedback_created_at'), 'post_feedback', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_post_feedback_created_at'), table_name='post_feedback')
    op.drop_index(op.f('ix_post_feedback_post_id'), table_name='post_feedback')
    op.drop_table('post_feedback')

# Made with Bob
