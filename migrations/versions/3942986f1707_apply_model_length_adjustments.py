"""Apply model length adjustments

Revision ID: 3942986f1707
Revises: 675e540a6bb8
Create Date: 2025-08-04 10:55:06.147672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3942986f1707'
down_revision = '675e540a6bb8'
branch_labels = None
depends_on = None


def upgrade():
    # Zeile: show_discipline war vermutlich zu kurz (varchar(20)), deswegen auf Text erweitern.
    with op.batch_alter_table('booking_requests') as batch_op:
        batch_op.alter_column(
            'show_discipline',
            existing_type=sa.String(length=20),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade():
    # Rückgängig: show_discipline wieder auf varchar(20) beschränken.
    with op.batch_alter_table('booking_requests') as batch_op:
        batch_op.alter_column(
            'show_discipline',
            existing_type=sa.Text(),
            type_=sa.String(length=20),
            existing_nullable=True,
        )
