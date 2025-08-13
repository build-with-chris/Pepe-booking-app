"""Adding approval Status for Artists by Admin

Revision ID: 32e406277c3b
Revises: f1fcce6d44f0
Create Date: 2025-08-13 09:53:17.527043

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32e406277c3b'
down_revision = 'f1fcce6d44f0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('artists', sa.Column('approval_status', sa.String(length=20), server_default='unsubmitted', nullable=False))
    op.add_column('artists', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('artists', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('artists', sa.Column('approved_by', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'artists', 'artists', ['approved_by'], ['id'])


def downgrade():
    op.drop_constraint(None, 'artists', type_='foreignkey')
    op.drop_column('artists', 'approved_by')
    op.drop_column('artists', 'approved_at')
    op.drop_column('artists', 'rejection_reason')
    op.drop_column('artists', 'approval_status')
