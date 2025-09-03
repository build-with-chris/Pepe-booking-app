"""add coords to artist and booking_req

Revision ID: b865c063252d
Revises: 32c83dfc95c5
Create Date: 2025-09-03 15:36:30.768705

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b865c063252d'
down_revision = '32c83dfc95c5'
branch_labels = None
depends_on = None


def upgrade():
    # Add cached coordinate columns
    op.add_column('artist', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('artist', sa.Column('lon', sa.Float(), nullable=True))

    op.add_column('booking_request', sa.Column('event_lat', sa.Float(), nullable=True))
    op.add_column('booking_request', sa.Column('event_lon', sa.Float(), nullable=True))


def downgrade():
    # Remove the added columns (reverse order)
    op.drop_column('booking_request', 'event_lon')
    op.drop_column('booking_request', 'event_lat')

    op.drop_column('artist', 'lon')
    op.drop_column('artist', 'lat')
