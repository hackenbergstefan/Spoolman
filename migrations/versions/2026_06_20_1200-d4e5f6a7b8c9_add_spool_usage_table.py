"""add_spool_usage_table.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-20 12:00:00.000000
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create spool_usage table and migrate data from spool.used_weight."""
    # Create the spool_usage table
    op.create_table(
        "spool_usage",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("spool_id", sa.Integer(), nullable=False),
        sa.Column("printer_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("used_weight", sa.Float(), nullable=False, comment="Weight of filament used in grams. Negative for corrections."),
        sa.ForeignKeyConstraint(["spool_id"], ["spool.id"]),
        sa.ForeignKeyConstraint(["printer_id"], ["printer.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_spool_usage_id"), "spool_usage", ["id"], unique=False)
    op.create_index(op.f("ix_spool_usage_spool_id"), "spool_usage", ["spool_id"], unique=False)
    op.create_index(op.f("ix_spool_usage_printer_id"), "spool_usage", ["printer_id"], unique=False)

    # Migrate existing used_weight data: insert a seed record for each spool with used_weight > 0
    conn = op.get_bind()
    spools = conn.execute(
        sa.text("SELECT id, used_weight, first_used, registered FROM spool WHERE used_weight > 0"),
    )
    spool_usage_table = sa.table(
        "spool_usage",
        sa.column("spool_id", sa.Integer),
        sa.column("printer_id", sa.Integer),
        sa.column("timestamp", sa.DateTime),
        sa.column("used_weight", sa.Float),
    )
    def _parse_dt(val):
        if isinstance(val, datetime):
            return val
        return datetime.fromisoformat(val)

    rows = [
        {
            "spool_id": row[0],
            "printer_id": None,
            "timestamp": _parse_dt(row[2]) if row[2] is not None else _parse_dt(row[3]),
            "used_weight": row[1],
        }
        for row in spools
    ]
    if rows:
        op.bulk_insert(spool_usage_table, rows)

    # Drop the migrated columns from spool table
    with op.batch_alter_table("spool") as batch_op:
        batch_op.drop_column("used_weight")
        batch_op.drop_column("first_used")
        batch_op.drop_column("last_used")


def downgrade() -> None:
    """Restore used_weight, first_used, last_used columns and drop spool_usage table."""
    # Re-add columns to spool
    with op.batch_alter_table("spool") as batch_op:
        batch_op.add_column(sa.Column("used_weight", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("first_used", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_used", sa.DateTime(), nullable=True))

    # Restore data from spool_usage
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE spool SET
                used_weight = COALESCE((SELECT SUM(used_weight) FROM spool_usage WHERE spool_usage.spool_id = spool.id), 0),
                first_used = (SELECT MIN(timestamp) FROM spool_usage WHERE spool_usage.spool_id = spool.id),
                last_used = (SELECT MAX(timestamp) FROM spool_usage WHERE spool_usage.spool_id = spool.id)
            """,
        ),
    )

    # Remove server default
    with op.batch_alter_table("spool") as batch_op:
        batch_op.alter_column("used_weight", server_default=None)

    # Drop spool_usage table
    op.drop_index(op.f("ix_spool_usage_printer_id"), table_name="spool_usage")
    op.drop_index(op.f("ix_spool_usage_spool_id"), table_name="spool_usage")
    op.drop_index(op.f("ix_spool_usage_id"), table_name="spool_usage")
    op.drop_table("spool_usage")
