from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.exceptions import AppError
from app.db.database import DatabaseManager, get_database_manager
from app.schemas.system import HealthResponse, ReadyResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable"}},
)
async def ready(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> ReadyResponse:
    if not await database.ping():
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="database_unavailable",
            message="MongoDB connection is unavailable",
        )
    return ReadyResponse()

