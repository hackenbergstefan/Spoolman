"""replace_prusalink_with_prusaconnect.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2024-06-03 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace prusalink_host/prusalink_apikey with prusaconnect_printer_uuid."""
    # Rename prusalink_host -> prusaconnect_printer_uuid (preserves any existing UUIDs stored in host field)
    with op.batch_alter_table("printer") as batch_op:
        batch_op.alter_column(
            "prusalink_host",
            new_column_name="prusaconnect_printer_uuid",
            existing_type=sa.String(length=256),
            existing_nullable=True,
        )
        batch_op.drop_column("prusalink_apikey")


def downgrade() -> None:
    """Restore prusalink_host and prusalink_apikey columns."""
    with op.batch_alter_table("printer") as batch_op:
        batch_op.alter_column(
            "prusaconnect_printer_uuid",
            new_column_name="prusalink_host",
            existing_type=sa.String(length=256),
            existing_nullable=True,
        )
        batch_op.add_column(sa.Column("prusalink_apikey", sa.String(length=256), nullable=True))
