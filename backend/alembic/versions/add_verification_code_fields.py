"""add verification code fields

Revision ID: add_verification_code
Revises: 18f72d4f708f
Create Date: 2026-02-21 19:23:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_verification_code'
down_revision = '18f72d4f708f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add verification_code and verification_code_expires columns to users table
    op.add_column('users', sa.Column('verification_code', sa.String(length=6), nullable=True))
    op.add_column('users', sa.Column('verification_code_expires', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove verification_code and verification_code_expires columns from users table
    op.drop_column('users', 'verification_code_expires')
    op.drop_column('users', 'verification_code')

# Made with Bob
