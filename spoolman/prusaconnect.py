"""PrusaConnect polling module for automatic spool usage tracking.

Polls PrusaConnect cloud for print job status changes and automatically
updates assigned spool usage when prints finish, fail, or are aborted.

Uses the prusa-connect-sdk-client library. Authentication is handled by
the SDK — run `prusactl auth login` once to store credentials.
"""

import asyncio
import datetime
import logging
import os
from dataclasses import dataclass

from prusa.connect.client import PrusaConnectClient
from prusa.connect.client.exceptions import PrusaApiError, PrusaAuthError, PrusaNetworkError
from prusa.connect.client.models.jobs import Job
from prusa.connect.client.models.printers import Printer as PCPrinter
from scheduler.asyncio.scheduler import Scheduler
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from spoolman.database import spool as db_spool
from spoolman.database.database import get_db_session
from spoolman.database.models import Printer, Spool

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 30

# Terminal states that indicate a print job has ended
_TERMINAL_STATES = {"FINISHED", "STOPPED", "ERROR"}
# States where the printer is actively printing
_PRINTING_STATES = {"PRINTING", "PAUSED"}


@dataclass
class _PrinterPollState:
    """Tracks the last known state of a printer between polls."""

    last_state: str | None = None
    last_progress: float = 0.0
    filament_used_mm: float | None = None


# Tracks state per Spoolman printer ID
_printer_states: dict[int, _PrinterPollState] = {}

# Lazy-initialized PrusaConnect client (sync SDK, called via asyncio.to_thread)
_client: PrusaConnectClient | None = None


def _is_enabled() -> bool:
    """Check if PrusaConnect polling is enabled via environment variable."""
    return os.getenv("SPOOLMAN_PRUSACONNECT_ENABLED", "FALSE").upper() in {"TRUE", "1"}


def _get_poll_interval() -> int:
    """Get the polling interval in seconds from environment variable."""
    try:
        return int(os.getenv("SPOOLMAN_PRUSACONNECT_POLL_INTERVAL", str(DEFAULT_POLL_INTERVAL)))
    except ValueError:
        return DEFAULT_POLL_INTERVAL


def _get_client() -> PrusaConnectClient:
    """Get or create the PrusaConnect client (lazy singleton)."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = PrusaConnectClient()
        logger.info("PrusaConnect client initialized.")
    return _client


def _fetch_printer_status(client: PrusaConnectClient, printer_uuid: str) -> PCPrinter:
    """Fetch printer details from PrusaConnect API (sync — call via to_thread)."""
    return client.printers.get(printer_uuid)


def _fetch_printer_jobs(client: PrusaConnectClient, printer_uuid: str) -> list[Job]:
    """Fetch current printing jobs from PrusaConnect API (sync — call via to_thread)."""
    return client.get_printer_jobs(printer_uuid, state=["PRINTING"], limit=1)


async def _poll() -> None:
    """Poll all PrusaConnect-enabled printers and track spool usage on state transitions."""
    try:
        client = _get_client()
    except Exception:
        logger.exception("Failed to initialize PrusaConnect client. Is `prusactl auth login` configured?")
        return

    async for db in get_db_session():
        # Find all printers with PrusaConnect configured
        stmt = (
            select(Printer)
            .where(Printer.prusaconnect_printer_uuid.isnot(None))
            .options(
                joinedload(Printer.spool).joinedload(Spool.filament),
            )
        )
        result = await db.execute(stmt)
        printers = list(result.unique().scalars().all())

        if not printers:
            return

        for printer in printers:
            should_stop = await _poll_printer_safe(db, client, printer)
            if should_stop:
                return


async def _poll_printer_safe(db, client: PrusaConnectClient, printer: Printer) -> bool:  # noqa: ANN001
    """Poll a single printer with error handling. Returns True if polling should stop."""
    try:
        await _poll_printer(db, client, printer)
    except PrusaAuthError:
        logger.exception("PrusaConnect authentication failed. Run `prusactl auth login` to refresh credentials.")
        return True  # Don't poll remaining printers if auth is broken
    except (PrusaApiError, PrusaNetworkError):
        logger.debug(
            "Failed to poll printer '%s' (UUID: %s)",
            printer.name,
            printer.prusaconnect_printer_uuid,
            exc_info=True,
        )
    except Exception:
        logger.exception(
            "Unexpected error polling printer '%s' (UUID: %s)",
            printer.name,
            printer.prusaconnect_printer_uuid,
        )
    return False


async def _poll_printer(db, client: PrusaConnectClient, printer: Printer) -> None:  # noqa: ANN001
    """Poll a single printer and handle state transitions."""
    printer_uuid = printer.prusaconnect_printer_uuid
    if not printer_uuid:
        return

    # Fetch printer status from PrusaConnect cloud (sync SDK → run in thread)
    pc_printer = await asyncio.to_thread(_fetch_printer_status, client, printer_uuid)

    current_state = pc_printer.printer_state
    if current_state is None:
        # Try the 'state' field as fallback
        current_state = pc_printer.state
    if current_state is None:
        return

    current_state_str = str(current_state.value) if hasattr(current_state, "value") else str(current_state)

    # Extract progress from embedded job info
    current_progress = 0.0
    if pc_printer.job is not None and pc_printer.job.progress is not None:
        current_progress = pc_printer.job.progress

    # Get or create tracked state for this printer
    state = _printer_states.setdefault(printer.id, _PrinterPollState())
    previous_state = state.last_state

    # While printing, cache job info for filament data
    if current_state_str in _PRINTING_STATES:
        state.last_progress = current_progress
        if state.filament_used_mm is None:
            filament_mm = await _fetch_filament_used_mm(client, printer_uuid)
            if filament_mm is not None:
                state.filament_used_mm = filament_mm
                logger.debug(
                    "Cached filament usage for printer '%s': %.1f mm",
                    printer.name,
                    filament_mm,
                )

    # Detect transition from printing to terminal state
    if previous_state in _PRINTING_STATES and current_state_str not in _PRINTING_STATES:
        await _handle_print_ended(db, printer, state, current_state_str)
        # Clear cached job data after handling
        state.filament_used_mm = None
        state.last_progress = 0.0

    state.last_state = current_state_str


async def _fetch_filament_used_mm(client: PrusaConnectClient, printer_uuid: str) -> float | None:
    """Fetch filament used (mm) from the current printing job's file metadata."""
    try:
        jobs = await asyncio.to_thread(_fetch_printer_jobs, client, printer_uuid)
        if not jobs:
            return None

        job = jobs[0]
        if job.file is not None and hasattr(job.file, "meta") and job.file.meta is not None:
            meta = job.file.meta
            if hasattr(meta, "filament_used_mm") and meta.filament_used_mm is not None:
                return float(meta.filament_used_mm)
    except (PrusaApiError, PrusaNetworkError, ValueError, TypeError):
        logger.debug("Failed to fetch filament usage for printer UUID %s", printer_uuid, exc_info=True)
    return None


async def _handle_print_ended(
    db,  # noqa: ANN001
    printer: Printer,
    state: _PrinterPollState,
    terminal_state: str,
) -> None:
    """Handle a print job ending by updating spool usage."""
    if printer.spool_id is None:
        logger.debug("Printer '%s' has no spool assigned, skipping usage update.", printer.name)
        return

    if state.filament_used_mm is None or state.filament_used_mm <= 0:
        logger.warning(
            "Printer '%s' finished printing but no filament usage data was cached.",
            printer.name,
        )
        return

    # Calculate actual usage based on terminal state
    if terminal_state in {"FINISHED", "IDLE", "READY"}:
        # Completed successfully — use full filament length
        used_mm = state.filament_used_mm
        progress_pct = 100.0
    elif terminal_state in _TERMINAL_STATES:
        # Stopped or errored — use progress-proportional filament length
        progress_pct = state.last_progress
        used_mm = state.filament_used_mm * (progress_pct / 100.0)
    else:
        # Unknown terminal state (e.g. BUSY, ATTENTION) — skip
        logger.debug(
            "Printer '%s' transitioned to '%s', not tracking spool usage.",
            printer.name,
            terminal_state,
        )
        return

    if used_mm <= 0:
        logger.debug("Printer '%s' used 0 mm of filament, skipping.", printer.name)
        return

    try:
        await db_spool.use_length(db, printer.spool_id, used_mm, printer_id=printer.id)
        logger.info(
            "Updated spool #%d by %.1f mm for printer '%s' (state: %s, progress: %.0f%%)",
            printer.spool_id,
            used_mm,
            printer.name,
            terminal_state,
            progress_pct,
        )
    except Exception:
        logger.exception(
            "Failed to update spool #%d for printer '%s'",
            printer.spool_id,
            printer.name,
        )


def schedule_tasks(scheduler: Scheduler) -> None:
    """Schedule PrusaConnect polling tasks.

    Args:
        scheduler: The scheduler to use for scheduling tasks.

    """
    if not _is_enabled():
        logger.info("PrusaConnect polling is disabled. Set SPOOLMAN_PRUSACONNECT_ENABLED=TRUE to enable.")
        return

    poll_interval = _get_poll_interval()
    logger.info("Scheduling PrusaConnect polling every %d seconds.", poll_interval)

    # Run once on startup after a short delay
    scheduler.once(datetime.timedelta(seconds=5), _poll)  # type: ignore[arg-type]

    # Then run periodically
    scheduler.cyclic(datetime.timedelta(seconds=poll_interval), _poll)  # type: ignore[arg-type]
