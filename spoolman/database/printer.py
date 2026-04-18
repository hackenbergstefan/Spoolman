"""Helper functions for interacting with printer database objects."""

import logging
from datetime import datetime

import sqlalchemy
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from spoolman.api.v1.models import EventType, Printer, PrinterEvent
from spoolman.database import models
from spoolman.database import spool as db_spool
from spoolman.database.utils import SortOrder, add_where_clause_str, add_where_clause_str_opt
from spoolman.exceptions import ItemCreateError, ItemNotFoundError
from spoolman.ws import websocket_manager

logger = logging.getLogger(__name__)


async def create(
    *,
    db: AsyncSession,
    name: str,
    spool_id: int | None = None,
    comment: str | None = None,
    external_id: str | None = None,
    extra: dict[str, str] | None = None,
) -> models.Printer:
    """Add a new printer to the database."""
    spool = None
    if spool_id is not None:
        spool = await db_spool.get_by_id(db, spool_id)

    printer = models.Printer(
        name=name,
        registered=datetime.utcnow().replace(microsecond=0),
        spool_id=spool.id if spool is not None else None,
        comment=comment,
        external_id=external_id,
        extra=[models.PrinterField(key=k, value=v) for k, v in (extra or {}).items()],
    )
    db.add(printer)
    try:
        await db.commit()
    except IntegrityError:
        raise ItemCreateError("Spool is already assigned to another printer.") from None

    # Re-load with relationships
    printer = await get_by_id(db, printer.id)
    await printer_changed(printer, EventType.ADDED)
    return printer


async def get_by_id(db: AsyncSession, printer_id: int) -> models.Printer:
    """Get a printer object from the database by the unique ID."""
    printer = await db.get(
        models.Printer,
        printer_id,
        options=[
            joinedload(models.Printer.spool).joinedload(models.Spool.filament).joinedload(models.Filament.vendor),
        ],
    )
    if printer is None:
        raise ItemNotFoundError(f"No printer with ID {printer_id} found.")
    return printer


async def find(
    *,
    db: AsyncSession,
    name: str | None = None,
    external_id: str | None = None,
    sort_by: dict[str, SortOrder] | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[models.Printer], int]:
    """Find a list of printer objects by search criteria.

    Returns a tuple containing the list of items and the total count of matching items.
    """
    stmt = select(models.Printer).options(
        joinedload(models.Printer.spool).joinedload(models.Spool.filament).joinedload(models.Filament.vendor),
    )

    stmt = add_where_clause_str(stmt, models.Printer.name, name)
    stmt = add_where_clause_str_opt(stmt, models.Printer.external_id, external_id)

    total_count = None

    if limit is not None:
        total_count_stmt = stmt.with_only_columns(func.count(), maintain_column_froms=True)
        total_count = (await db.execute(total_count_stmt)).scalar()

        stmt = stmt.offset(offset).limit(limit)

    if sort_by is not None:
        for fieldstr, order in sort_by.items():
            field = getattr(models.Printer, fieldstr)
            if order == SortOrder.ASC:
                stmt = stmt.order_by(field.asc())
            elif order == SortOrder.DESC:
                stmt = stmt.order_by(field.desc())

    rows = await db.execute(
        stmt,
        execution_options={"populate_existing": True},
    )
    result = list(rows.unique().scalars().all())
    if total_count is None:
        total_count = len(result)

    return result, total_count


async def update(
    *,
    db: AsyncSession,
    printer_id: int,
    data: dict,
) -> models.Printer:
    """Update the fields of a printer object."""
    printer = await get_by_id(db, printer_id)
    for k, v in data.items():
        if k == "extra":
            printer.extra = [models.PrinterField(key=k, value=v) for k, v in v.items()]
        elif k == "spool_id":
            if v is not None:
                spool = await db_spool.get_by_id(db, v)
                printer.spool_id = spool.id
            else:
                printer.spool_id = None
        else:
            setattr(printer, k, v)
    try:
        await db.commit()
    except IntegrityError:
        raise ItemCreateError("Spool is already assigned to another printer.") from None

    # Re-load with relationships
    printer = await get_by_id(db, printer_id)
    await printer_changed(printer, EventType.UPDATED)
    return printer


async def delete(db: AsyncSession, printer_id: int) -> None:
    """Delete a printer object."""
    printer = await get_by_id(db, printer_id)
    await db.delete(printer)
    await printer_changed(printer, EventType.DELETED)


async def clear_extra_field(db: AsyncSession, key: str) -> None:
    """Delete all extra fields with a specific key."""
    await db.execute(
        sqlalchemy.delete(models.PrinterField).where(models.PrinterField.key == key),
    )


async def printer_changed(printer: models.Printer, typ: EventType) -> None:
    """Notify websocket clients that a printer has changed."""
    try:
        await websocket_manager.send(
            ("printer", str(printer.id)),
            PrinterEvent(
                type=typ,
                resource="printer",
                date=datetime.utcnow(),
                payload=Printer.from_db(printer),
            ),
        )
    except Exception:
        # Important to have a catch-all here since we don't want to stop the call if this fails.
        logger.exception("Failed to send websocket message")
