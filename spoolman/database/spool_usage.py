"""Helper functions for interacting with spool_usage database objects."""

import logging
from datetime import datetime, timezone

import sqlalchemy
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from spoolman.database import models
from spoolman.exceptions import ItemNotFoundError

logger = logging.getLogger(__name__)


async def create(
    *,
    db: AsyncSession,
    spool_id: int,
    used_weight: float,
    printer_id: int | None = None,
    timestamp: datetime | None = None,
) -> models.SpoolUsage:
    """Record a usage event for a spool.

    Args:
        db: Database session
        spool_id: Spool ID
        used_weight: Weight of filament used in grams (negative for corrections)
        printer_id: Optional printer ID
        timestamp: Optional timestamp (defaults to now)

    Returns:
        The created SpoolUsage record

    """
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc).replace(microsecond=0, tzinfo=None)
    else:
        timestamp = timestamp.astimezone(tz=timezone.utc).replace(tzinfo=None)

    usage = models.SpoolUsage(
        spool_id=spool_id,
        printer_id=printer_id,
        timestamp=timestamp,
        used_weight=used_weight,
    )
    db.add(usage)
    await db.flush()
    return usage


async def get_total_usage(db: AsyncSession, spool_id: int) -> float:
    """Get total used weight for a spool by summing all usage records.

    Args:
        db: Database session
        spool_id: Spool ID

    Returns:
        Total used weight in grams

    """
    result = await db.execute(
        sqlalchemy.select(func.coalesce(func.sum(models.SpoolUsage.used_weight), 0.0)).where(
            models.SpoolUsage.spool_id == spool_id,
        ),
    )
    return float(result.scalar_one())


async def get_first_last_used(db: AsyncSession, spool_id: int) -> tuple[datetime | None, datetime | None]:
    """Get the first and last usage timestamps for a spool.

    Args:
        db: Database session
        spool_id: Spool ID

    Returns:
        Tuple of (first_used, last_used) datetimes, or (None, None) if no usage records exist

    """
    result = await db.execute(
        sqlalchemy.select(
            func.min(models.SpoolUsage.timestamp),
            func.max(models.SpoolUsage.timestamp),
        ).where(models.SpoolUsage.spool_id == spool_id),
    )
    row = result.one()
    return row[0], row[1]


async def find_by_spool(
    db: AsyncSession,
    spool_id: int,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[models.SpoolUsage], int]:
    """Find usage records for a spool.

    Args:
        db: Database session
        spool_id: Spool ID
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        Tuple of (list of usage records, total count)

    """
    stmt = (
        sqlalchemy.select(models.SpoolUsage)
        .where(models.SpoolUsage.spool_id == spool_id)
        .options(
            joinedload(models.SpoolUsage.printer),
            joinedload(models.SpoolUsage.spool).joinedload(models.Spool.filament).joinedload(models.Filament.vendor),
        )
        .order_by(models.SpoolUsage.timestamp.desc())
    )

    total_count_stmt = sqlalchemy.select(func.count()).where(models.SpoolUsage.spool_id == spool_id).select_from(
        models.SpoolUsage,
    )
    total_count = (await db.execute(total_count_stmt)).scalar_one()

    if limit is not None:
        stmt = stmt.offset(offset).limit(limit)

    rows = await db.execute(stmt)
    result = list(rows.unique().scalars().all())

    return result, total_count


async def delete(db: AsyncSession, usage_id: int) -> None:
    """Delete a usage record by ID."""
    usage = await db.get(models.SpoolUsage, usage_id)
    if usage is None:
        raise ItemNotFoundError(f"No usage record with ID {usage_id} found.")
    await db.delete(usage)


async def update(
    db: AsyncSession,
    usage_id: int,
    spool_id: int,
) -> models.SpoolUsage:
    """Update the spool_id of a usage record.

    Args:
        db: Database session
        usage_id: Usage record ID
        spool_id: New spool ID

    Returns:
        Updated SpoolUsage record

    """
    usage = await db.get(
        models.SpoolUsage,
        usage_id,
        options=[
            joinedload(models.SpoolUsage.printer),
            joinedload(models.SpoolUsage.spool).joinedload(models.Spool.filament).joinedload(models.Filament.vendor),
        ],
    )
    if usage is None:
        raise ItemNotFoundError(f"No usage record with ID {usage_id} found.")
    usage.spool_id = spool_id
    await db.flush()
    # Reload with relationships
    await db.refresh(usage)
    usage = await db.get(
        models.SpoolUsage,
        usage_id,
        options=[
            joinedload(models.SpoolUsage.printer),
            joinedload(models.SpoolUsage.spool).joinedload(models.Spool.filament).joinedload(models.Filament.vendor),
        ],
    )
    await db.commit()
    return usage


async def find_all(
    db: AsyncSession,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[models.SpoolUsage], int]:
    """Find all usage records across all spools.

    Args:
        db: Database session
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        Tuple of (list of usage records, total count)

    """
    stmt = (
        sqlalchemy.select(models.SpoolUsage)
        .options(
            joinedload(models.SpoolUsage.printer),
            joinedload(models.SpoolUsage.spool).joinedload(models.Spool.filament).joinedload(models.Filament.vendor),
        )
        .order_by(models.SpoolUsage.timestamp.desc())
    )

    total_count_stmt = sqlalchemy.select(func.count()).select_from(models.SpoolUsage)
    total_count = (await db.execute(total_count_stmt)).scalar_one()

    if limit is not None:
        stmt = stmt.offset(offset).limit(limit)

    rows = await db.execute(stmt)
    result = list(rows.unique().scalars().all())

    return result, total_count
