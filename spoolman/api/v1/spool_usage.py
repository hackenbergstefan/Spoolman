"""Spool usage related endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spoolman.api.v1.models import Message, SpoolUsageResponse
from spoolman.database import spool_usage as spool_usage_db
from spoolman.database.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/spool_usage",
    tags=["spool_usage"],
)

# ruff: noqa: D103


@router.get(
    "",
    name="Find spool usage",
    description="Get a list of all spool usage records.",
    response_model_exclude_none=True,
    responses={
        200: {"model": list[SpoolUsageResponse]},
    },
)
async def find(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[
        int | None,
        Query(title="Limit", description="Maximum number of items in the response."),
    ] = None,
    offset: Annotated[int, Query(title="Offset", description="Offset in the full result set if a limit is set.")] = 0,
) -> JSONResponse:
    db_items, total_count = await spool_usage_db.find_all(db, limit=limit, offset=offset)
    return JSONResponse(
        content=jsonable_encoder(
            [SpoolUsageResponse.from_db(item) for item in db_items],
            exclude_none=True,
        ),
        headers={"x-total-count": str(total_count)},
    )


class SpoolUsageUpdateParameters(BaseModel):
    spool_id: int = Field(description="The new spool ID to assign to this usage record.")


@router.patch(
    "/{usage_id}",
    name="Update spool usage",
    description="Update a spool usage record (e.g. reassign to a different spool).",
    response_model_exclude_none=True,
    response_model=SpoolUsageResponse,
    responses={
        404: {"model": Message},
    },
)
async def update(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    usage_id: int,
    body: SpoolUsageUpdateParameters,
) -> SpoolUsageResponse:
    db_item = await spool_usage_db.update(db, usage_id, spool_id=body.spool_id)
    return SpoolUsageResponse.from_db(db_item)
