"""Add status for individual Artist in table booking_artist

Revision ID: 1ff273b10c12
Revises: ad3977442792
Create Date: 2025-08-08 08:55:26.719070

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1ff273b10c12'
down_revision = 'ad3977442792'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('booking_artists', sa.Column('status', sa.String(length=20), server_default='angefragt', nullable=False))
    # Backfill existing rows explicitly (safety on some engines)
    op.execute("UPDATE booking_artists SET status='angefragt' WHERE status IS NULL")

    # Optional: remove server default so new inserts must set the value explicitly
    op.alter_column('booking_artists', 'status', server_default=None)

    # Enforce allowed values via CHECK constraint
    op.create_check_constraint(
        'ck_booking_artists_status_allowed',
        'booking_artists',
        "status IN ('angefragt','angeboten','akzeptiert','abgelehnt','storniert')"
    )


def downgrade():
    # Drop the CHECK constraint first (if present)
    op.drop_constraint('ck_booking_artists_status_allowed', 'booking_artists', type_='check')
    op.drop_column('booking_artists', 'status')
