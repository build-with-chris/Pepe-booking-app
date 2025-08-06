"""Add artist_gage and artist_offer_date to BookingRequest

Revision ID: ad3977442792
Revises: 80e563a2e395
Create Date: 2025-08-06 14:14:59.190436

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad3977442792'
down_revision = '80e563a2e395'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('booking_requests', sa.Column('artist_gage', sa.Integer(), nullable=True))
    op.add_column('booking_requests', sa.Column('artist_offer_date', sa.DateTime(), nullable=True))
    # Backfill existing rows: copy old price_offered into artist_gage
    op.execute(
        "UPDATE booking_requests SET artist_gage = price_offered"
    )
    # Initialize artist_offer_date from created_at (or another timestamp column)
    op.execute(
        "UPDATE booking_requests SET artist_offer_date = created_at"
    )


def downgrade():
    op.drop_column('booking_requests', 'artist_offer_date')
    op.drop_column('booking_requests', 'artist_gage')
