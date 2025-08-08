"""Add Bio and Image toartist table

Revision ID: d0cdff8d171a
Revises: 1ff273b10c12
Create Date: 2025-08-08 11:43:40.165401

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd0cdff8d171a'
down_revision = '1ff273b10c12'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('artists')}

    with op.batch_alter_table('artists', schema=None) as batch_op:
        if 'profile_image_url' not in existing_cols:
            batch_op.add_column(sa.Column('profile_image_url', sa.String(length=512), nullable=True))
        if 'bio' not in existing_cols:
            batch_op.add_column(sa.Column('bio', sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('artists')}

    with op.batch_alter_table('artists', schema=None) as batch_op:
        if 'bio' in existing_cols:
            batch_op.drop_column('bio')
        if 'profile_image_url' in existing_cols:
            batch_op.drop_column('profile_image_url')
