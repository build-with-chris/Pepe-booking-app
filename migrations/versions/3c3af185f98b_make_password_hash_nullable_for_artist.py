"""Make password_hash nullable for Artist

Revision ID: 3c3af185f98b
Revises: 32e406277c3b
Create Date: 2025-08-14 12:48:56.445083

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c3af185f98b'
down_revision = '32e406277c3b'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('artists', 'password_hash',
               existing_type=sa.TEXT(),
               nullable=True)


def downgrade():
    op.alter_column('artists', 'password_hash',
               existing_type=sa.TEXT(),
               nullable=False)
