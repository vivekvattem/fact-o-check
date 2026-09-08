"""Temporary authenticated production diagnostics."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.services.fact_extractor import EvidenceContext, ExtractorError, get_fact_extractor

router = APIRouter(prefix="/debug", tags=["debug"])


class ProviderSmokeResponse(BaseModel):
    success: bool
    provider: str
    model: str
    http_status: int | None
    error_type: str | None
    message: str


def _authorize(debug_token: str | None, settings: Settings) -> None:
    expected = settings.debug_token.get_secret_value()
    if not expected or debug_token is None or not secrets.compare_digest(debug_token, expected):
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Invalid debug token",
        )


@router.post("/provider-smoke", response_model=ProviderSmokeResponse)
async def provider_smoke(
    settings: Annotated[Settings, Depends(get_settings)],
    debug_token: Annotated[str | None, Header(alias="X-Debug-Token")] = None,
) -> ProviderSmokeResponse:
    _authorize(debug_token, settings)
    try:
        extractor = get_fact_extractor(settings)
        await extractor.extract(
            (EvidenceContext("000000000000000000000000", 1, "Fact-O-Check provider smoke test."),)
        )
    except ExtractorError as exc:
        return ProviderSmokeResponse(
            success=False,
            provider=settings.llm_provider,
            model=settings.llm_model,
            http_status=exc.http_status,
            error_type=exc.error_type or exc.code,
            message=exc.safe_message or exc.code,
        )
    except AppError as exc:
        return ProviderSmokeResponse(
            success=False,
            provider=settings.llm_provider,
            model=settings.llm_model,
            http_status=None,
            error_type=exc.code,
            message=exc.message,
        )
    return ProviderSmokeResponse(
        success=True,
        provider=settings.llm_provider,
        model=settings.llm_model,
        http_status=200,
        error_type=None,
        message="Provider request completed",
    )
