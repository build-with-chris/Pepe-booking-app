"""add lat/lon to artists and event_lat/lon to booking_requests

Revision ID: 440ee552081b
Revises: b865c063252d
Create Date: 2025-09-04 08:13:27.551298

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '440ee552081b'
down_revision = 'b865c063252d'
branch_labels = None
depends_on = None



def upgrade():
    # Richtige Tabellen!
    op.add_column('artists', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('artists', sa.Column('lon', sa.Float(), nullable=True))

    op.add_column('booking_requests', sa.Column('event_lat', sa.Float(), nullable=True))
    op.add_column('booking_requests', sa.Column('event_lon', sa.Float(), nullable=True))

    # Optional: falls du versehentlich Singular-Tabellen angelegt hattest, könntest du hier
    # op.drop_column('artist', 'lat') usw. aufräumen – nur wenn diese Tabellen wirklich existieren.


def downgrade():
    op.drop_column('booking_requests', 'event_lon')
    op.drop_column('booking_requests', 'event_lat')

    op.drop_column('artists', 'lon')
    op.drop_column('artists', 'lat')