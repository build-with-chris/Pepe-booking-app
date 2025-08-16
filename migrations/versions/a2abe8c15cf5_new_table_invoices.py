"""New Table Invoices

Revision ID: a2abe8c15cf5
Revises: 3c3af185f98b
Create Date: 2025-08-16 10:00:17.695798

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2abe8c15cf5'
down_revision = '3c3af185f98b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='uploaded', nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(length=8), server_default='EUR', nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist_id', 'storage_path', name='uq_invoice_artist_path'),
        sa.CheckConstraint("status IN ('uploaded','verified','paid','rejected')", name='ck_invoices_status'),
    )
    op.create_index(op.f('ix_invoices_artist_id'), 'invoices', ['artist_id'], unique=False)
    op.create_index(op.f('ix_invoices_created_at'), 'invoices', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_invoices_artist_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_created_at'), table_name='invoices')
    op.drop_table('invoices')
