"""Add supabase_user_id to Artist and backend_artist_id to profiles

Revision ID: 5318f0092b8e
Revises: 
Create Date: 2025-07-31 16:37:35.205709

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5318f0092b8e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('artists', schema=None) as batch_op:
        batch_op.add_column(sa.Column('supabase_user_id', sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint('uq_artists_supabase_user_id', ['supabase_user_id'])
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('backend_artist_id', sa.Text(), nullable=True))
        batch_op.create_unique_constraint('uq_profiles_backend_artist_id', ['backend_artist_id'])


def downgrade():
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.drop_constraint('uq_profiles_backend_artist_id', type_='unique')
        batch_op.drop_column('backend_artist_id')
    with op.batch_alter_table('artists', schema=None) as batch_op:
        batch_op.drop_constraint('uq_artists_supabase_user_id', type_='unique')
        batch_op.drop_column('supabase_user_id')