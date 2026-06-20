"""add_prusalink_fields.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2024-06-02 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Perform the upgrade."""
    op.add_column("printer", sa.Column("prusalink_host", sa.String(length=256), nullable=True))
    op.add_column("printer", sa.Column("prusalink_apikey", sa.String(length=256), nullable=True))


def downgrade() -> None:
    """Perform the downgrade."""
    op.drop_column("printer", "prusalink_apikey")
    op.drop_column("printer", "prusalink_host")
