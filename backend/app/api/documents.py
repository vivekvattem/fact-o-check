from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.core.config import Settings, get_settings
from app.normalization.service import normalize_document_facts
from app.schemas.documents import DocumentResponse, DocumentUploadResponse, EvidencePageResponse
from app.schemas.facts import ExtractionSummary, NormalizationSummary
from app.services.document_ingestion import ingest_pdf
from app.services.documents import (
    delete_document,
    get_document_or_404,
    list_documents,
    list_evidence,
    serialize_document,
)
from app.services.facts import extract_document_facts

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/{document_id}/extract-facts", response_model=ExtractionSummary)
async def extract_facts(
    document_id: PydanticObjectId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExtractionSummary:
    return await extract_document_facts(document_id, settings)


@router.post("/{document_id}/normalize-facts", response_model=NormalizationSummary)
async def normalize_facts(document_id: PydanticObjectId) -> NormalizationSummary:
    return await normalize_document_facts(document_id)


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    response: Response,
    file: Annotated[UploadFile, File(description="PDF document")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentUploadResponse:
    try:
        result = await ingest_pdf(file, settings)
    finally:
        await file.close()

    if result.already_existed:
        response.status_code = status.HTTP_200_OK
    return DocumentUploadResponse(
        document=DocumentResponse.from_document(
            result.document,
            result.evidence_chunk_count,
        ),
        already_existed=result.already_existed,
    )


@router.get("", response_model=list[DocumentResponse])
async def get_documents() -> list[DocumentResponse]:
    return await list_documents()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: PydanticObjectId) -> DocumentResponse:
    return await serialize_document(await get_document_or_404(document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(document_id: PydanticObjectId) -> Response:
    await delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}/evidence", response_model=EvidencePageResponse)
async def get_document_evidence(
    document_id: PydanticObjectId,
    page: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> EvidencePageResponse:
    return await list_evidence(
        document_id,
        page=page,
        offset=offset,
        limit=limit,
    )
