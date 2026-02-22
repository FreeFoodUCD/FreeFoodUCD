"""add reminder fields to events

Revision ID: add_reminder_fields
Revises: add_verification_code_fields
Create Date: 2026-02-22 17:47:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_reminder_fields'
down_revision = 'add_verification_code_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add reminder_sent and reminder_sent_at columns to events table
    op.add_column('events', sa.Column('reminder_sent', sa.Boolean(), nullable=True))
    op.add_column('events', sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create index on reminder_sent for faster queries
    op.create_index(op.f('ix_events_reminder_sent'), 'events', ['reminder_sent'], unique=False)
    
    # Set default value for existing rows
    op.execute("UPDATE events SET reminder_sent = false WHERE reminder_sent IS NULL")
    
    # Make reminder_sent NOT NULL after setting defaults
    op.alter_column('events', 'reminder_sent', nullable=False, server_default=sa.false())


def downgrade():
    # Remove index
    op.drop_index(op.f('ix_events_reminder_sent'), table_name='events')
    
    # Remove columns
    op.drop_column('events', 'reminder_sent_at')
    op.drop_column('events', 'reminder_sent')

# Made with Bob
