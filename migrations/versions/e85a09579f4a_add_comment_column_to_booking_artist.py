"""Add comment column to booking artist

Revision ID: e85a09579f4a
Revises: d0cdff8d171a
Create Date: 2025-08-11 13:56:07.135559

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e85a09579f4a'
down_revision = 'd0cdff8d171a'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('booking_artists')]
    if 'comment' not in existing_columns:
        op.add_column('booking_artists', sa.Column('comment', sa.Text(), nullable=True))
        print("[Alembic] Column 'comment' added to 'booking_artists'.")
    else:
        print("[Alembic] Column 'comment' already exists in 'booking_artists'.")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('booking_artists')]
    if 'comment' in existing_columns:
        op.drop_column('booking_artists', 'comment')
        print("[Alembic] Column 'comment' dropped from 'booking_artists'.")
    else:
        print("[Alembic] Column 'comment' does not exist in 'booking_artists'.")
