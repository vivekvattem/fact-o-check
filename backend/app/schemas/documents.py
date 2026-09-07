from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from app.models.document import Document, DocumentStatus
from app.models.evidence_chunk import EvidenceChunk


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    original_filename: str
    content_hash: str
    mime_type: str
    file_size_bytes: int | None
    page_count: int | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    evidence_chunk_count: int

    @classmethod
    def from_document(cls, document: Document, evidence_chunk_count: int) -> "DocumentResponse":
        return cls.model_validate(
            {
                **document.model_dump(),
                "evidence_chunk_count": evidence_chunk_count,
            }
        )


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    already_existed: bool


class EvidenceChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    document_id: PydanticObjectId
    page_number: int
    block_index: int
    text: str
    bbox: list[float] | None
    metadata: dict[str, Any] | None
    created_at: datetime

    @classmethod
    def from_chunk(cls, chunk: EvidenceChunk) -> "EvidenceChunkResponse":
        return cls.model_validate(chunk)


class EvidencePageResponse(BaseModel):
    items: list[EvidenceChunkResponse]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    page: int | None = Field(default=None, ge=1)

