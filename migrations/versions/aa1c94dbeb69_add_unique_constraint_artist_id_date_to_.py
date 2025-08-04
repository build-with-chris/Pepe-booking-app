"""Add supabase_user_id to Artist and backend_artist_id to profiles

Revision ID: 5318f0092b8e
Revises:
Create Date: 2025-07-31 16:37:35.205709
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '5318f0092b8e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # artists: supabase_user_id nur hinzufügen, wenn noch nicht vorhanden
    artist_columns = [col['name'] for col in inspector.get_columns('artists')]
    if 'supabase_user_id' not in artist_columns:
        with op.batch_alter_table('artists', schema=None) as batch_op:
            batch_op.add_column(sa.Column('supabase_user_id', sa.String(length=255), nullable=True))
            batch_op.create_index('ix_artists_supabase_user_id', ['supabase_user_id'], unique=False)

    # profiles: backend_artist_id nur hinzufügen, wenn noch nicht vorhanden
    profile_columns = [col['name'] for col in inspector.get_columns('profiles')]
    if 'backend_artist_id' not in profile_columns:
        with op.batch_alter_table('profiles', schema=None) as batch_op:
            batch_op.add_column(sa.Column('backend_artist_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_profiles_backend_artist_id_artists',
                'artists',
                ['backend_artist_id'],
                ['id'],
            )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # artists: supabase_user_id entfernen, wenn vorhanden
    artist_columns = [col['name'] for col in inspector.get_columns('artists')]
    if 'supabase_user_id' in artist_columns:
        with op.batch_alter_table('artists', schema=None) as batch_op:
            batch_op.drop_index('ix_artists_supabase_user_id')
            batch_op.drop_column('supabase_user_id')

    # profiles: backend_artist_id entfernen, wenn vorhanden
    profile_columns = [col['name'] for col in inspector.get_columns('profiles')]
    if 'backend_artist_id' in profile_columns:
        with op.batch_alter_table('profiles', schema=None) as batch_op:
            try:
                batch_op.drop_constraint('fk_profiles_backend_artist_id_artists', type_='foreignkey')
            except Exception:
                pass
            batch_op.drop_column('backend_artist_id')

"""Add unique constraint artist_id+date to availability

Revision ID: aa1c94dbeb69
Revises: 5318f0092b8e
Create Date: 2025-08-01 10:04:22.403723
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'aa1c94dbeb69'
down_revision = '5318f0092b8e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Unique constraint auf (artist_id, date) nur hinzufügen, wenn sie noch nicht existiert
    existing = [c['name'] for c in inspector.get_unique_constraints('availabilities')]
    if 'uq_artist_date' not in existing:
        with op.batch_alter_table('availabilities', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_artist_date', ['artist_id', 'date'])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Unique constraint nur entfernen, wenn sie existiert
    existing = [c['name'] for c in inspector.get_unique_constraints('availabilities')]
    if 'uq_artist_date' in existing:
        with op.batch_alter_table('availabilities', schema=None) as batch_op:
            batch_op.drop_constraint('uq_artist_date', type_='unique')