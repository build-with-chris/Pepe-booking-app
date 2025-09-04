"""add timestamps to booking requzests and index status

Revision ID: 7759e31194a7
Revises: 440ee552081b
Create Date: 2025-09-04 09:39:26.623571

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7759e31194a7'
down_revision = '440ee552081b'
branch_labels = None
depends_on = None


def upgrade():
    """Minimal migration: only add booking_requests timestamps + indexes."""
    # Columns: use server_default NOW() so existing rows pass NOT NULL,
    # the application-level defaults (datetime.utcnow) will handle new rows.
    op.add_column(
        'booking_requests',
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.add_column(
        'booking_requests',
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.add_column(
        'booking_requests',
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
    )

    # Indexes for sorting/filtering
    op.create_index('ix_booking_requests_created_at', 'booking_requests', ['created_at'], unique=False)
    op.create_index('ix_booking_requests_status', 'booking_requests', ['status'], unique=False)


def downgrade():
    """Revert only what this migration added."""
    op.drop_index('ix_booking_requests_status', table_name='booking_requests')
    op.drop_index('ix_booking_requests_created_at', table_name='booking_requests')

    op.drop_column('booking_requests', 'accepted_at')
    op.drop_column('booking_requests', 'updated_at')
    op.drop_column('booking_requests', 'created_at')
