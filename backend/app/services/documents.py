import asyncio

from beanie import PydanticObjectId
from fastapi import status

from app.core.exceptions import AppError
from app.models.document import Document
from app.models.evidence_chunk import EvidenceChunk
from app.schemas.documents import DocumentResponse, EvidenceChunkResponse, EvidencePageResponse


async def get_document_or_404(document_id: PydanticObjectId) -> Document:
    document = await Document.get(document_id)
    if document is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="document_not_found",
            message="Document not found",
        )
    return document


async def serialize_document(document: Document) -> DocumentResponse:
    chunk_count = await EvidenceChunk.find(EvidenceChunk.document_id == document.id).count()
    return DocumentResponse.from_document(document, chunk_count)


async def list_documents() -> list[DocumentResponse]:
    documents = await Document.find_all().sort("-created_at", "+_id").to_list()
    return await asyncio.gather(*(serialize_document(document) for document in documents))


async def list_evidence(
    document_id: PydanticObjectId,
    *,
    page: int | None,
    offset: int,
    limit: int,
) -> EvidencePageResponse:
    await get_document_or_404(document_id)
    query = EvidenceChunk.find(EvidenceChunk.document_id == document_id)
    if page is not None:
        query = query.find(EvidenceChunk.page_number == page)

    total = await query.count()
    chunks = (
        await query.sort("+page_number", "+block_index", "+_id")
        .skip(offset)
        .limit(limit)
        .to_list()
    )
    return EvidencePageResponse(
        items=[EvidenceChunkResponse.from_chunk(chunk) for chunk in chunks],
        total=total,
        offset=offset,
        limit=limit,
        page=page,
    )


async def delete_document(document_id: PydanticObjectId) -> None:
    document = await get_document_or_404(document_id)
    await EvidenceChunk.find(EvidenceChunk.document_id == document_id).delete()
    await document.delete()

