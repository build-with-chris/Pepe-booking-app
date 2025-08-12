"""Add instaLink and Gallery option for artistst

Revision ID: f1fcce6d44f0
Revises: e85a09579f4a
Create Date: 2025-08-12 11:40:24.470329

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1fcce6d44f0'
down_revision = 'e85a09579f4a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('artists', sa.Column('instagram', sa.String(length=255), nullable=True))
    op.add_column(
        'artists',
        sa.Column('gallery_urls', sa.JSON(), nullable=True, server_default='[]')
    )


def downgrade():
    op.drop_column('artists', 'gallery_urls')
    op.drop_column('artists', 'instagram')
