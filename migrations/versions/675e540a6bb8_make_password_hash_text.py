"""Make password_hash text

Revision ID: 675e540a6bb8
Revises: aa1c94dbeb69
Create Date: 2025-08-04 09:36:59.910687

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '675e540a6bb8'
down_revision = 'aa1c94dbeb69'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("artists", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=128),
            type_=sa.Text(),
            existing_nullable=True,
        )

def downgrade():
    with op.batch_alter_table("artists", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
