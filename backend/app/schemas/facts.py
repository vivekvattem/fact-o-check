from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.documents import EvidenceChunkResponse


class ValueType(StrEnum):
    NUMBER = "NUMBER"
    PERCENTAGE = "PERCENTAGE"
    CURRENCY = "CURRENCY"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    STRING = "STRING"
    ENTITY = "ENTITY"
    QUANTITY = "QUANTITY"


class FactCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_chunk_ids: list[PydanticObjectId] = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=512, pattern=r"\S")
    predicate: str = Field(min_length=1, max_length=512, pattern=r"\S")
    raw_value: str = Field(min_length=1, max_length=8000, pattern=r"\S")
    value_type: ValueType
    raw_unit: str | None = Field(default=None, max_length=128)
    period_start: date | None = None
    period_end: date | None = None
    as_of_date: date | None = None
    geography: str | None = Field(default=None, max_length=255)
    scope: str | None = Field(default=None, max_length=512)
    qualifiers: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def ordered_period(self) -> "FactCandidate":
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class SourceDocument(BaseModel):
    id: PydanticObjectId
    original_filename: str


class FactResponse(BaseModel):
    id: PydanticObjectId
    document_id: PydanticObjectId
    evidence_chunk_ids: list[PydanticObjectId]
    subject: str
    predicate: str
    raw_value: Any
    normalized_value: Any | None
    value_type: str | None
    raw_unit: str | None
    normalized_unit: str | None
    period_start: date | None
    period_end: date | None
    as_of_date: date | None
    geography: str | None
    scope: str | None
    qualifiers: dict[str, Any]
    extraction_confidence: float | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    source_document: SourceDocument | None
    page_numbers: list[int]
    evidence: list[EvidenceChunkResponse]


class FactPageResponse(BaseModel):
    items: list[FactResponse]
    total: int
    offset: int
    limit: int


class WindowFailure(BaseModel):
    window: int
    code: str


class ExtractionSummary(BaseModel):
    document_id: PydanticObjectId
    status: Literal["completed", "partial", "failed"] = "completed"
    windows_total: int = 0
    windows_processed: int = 0
    windows_failed: int = 0
    windows_skipped: int = 0
    facts_produced: int = 0
    facts_created: int = 0
    facts_deduplicated: int = 0
    candidates_rejected: int = 0
    duration_seconds: float = 0
    failures: list[WindowFailure] = Field(default_factory=list)
