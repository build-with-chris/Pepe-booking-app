"""Updated fields (z.B. show_discipline length)

Revision ID: 80e563a2e395
Revises: 3942986f1707
Create Date: 2025-08-04 11:26:13.655072

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '80e563a2e395'
down_revision = '3942986f1707'
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
