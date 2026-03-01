"""add nlp_failed and nlp_error to posts

Revision ID: add_nlp_failed
Revises: add_post_feedback
Create Date: 2026-03-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_nlp_failed'
down_revision = 'add_post_feedback'
branch_labels = None
depends_on = None


def upgrade():
    # Add nlp_failed flag — True when Gemini API fails so the post can be re-queued.
    # Default False (existing rows are treated as not failed).
    op.add_column(
        'posts',
        sa.Column('nlp_failed', sa.Boolean(), nullable=False, server_default='false')
    )
    op.create_index('ix_posts_nlp_failed', 'posts', ['nlp_failed'], unique=False)

    # Add nlp_error text — stores the exception message for debugging.
    op.add_column(
        'posts',
        sa.Column('nlp_error', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_index('ix_posts_nlp_failed', table_name='posts')
    op.drop_column('posts', 'nlp_error')
    op.drop_column('posts', 'nlp_failed')

# Made with Bob