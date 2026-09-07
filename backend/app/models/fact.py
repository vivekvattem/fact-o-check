from datetime import date, datetime
from typing import Any, ClassVar

from beanie import Document as BeanieDocument
from beanie import Insert, PydanticObjectId, Replace, Save, before_event
from pydantic import Field, model_validator
from pymongo import ASCENDING, IndexModel

from app.models.common import utc_now
from app.models.evidence_chunk import EvidenceChunk


class Fact(BeanieDocument):
    document_id: PydanticObjectId
    evidence_chunk_ids: list[PydanticObjectId] = Field(default_factory=list)
    subject: str = Field(min_length=1, max_length=512)
    predicate: str = Field(min_length=1, max_length=512)
    normalized_subject: str | None = Field(default=None, max_length=512)
    normalized_predicate: str | None = Field(default=None, max_length=512)

    raw_value: Any | None = None
    normalized_value: Any | None = None
    value_type: str | None = Field(default=None, max_length=128)

    raw_unit: str | None = Field(default=None, max_length=128)
    normalized_unit: str | None = Field(default=None, max_length=128)

    period_start: date | None = None
    period_end: date | None = None
    as_of_date: date | None = None

    geography: str | None = Field(default=None, max_length=255)
    scope: str | None = Field(default=None, max_length=512)

    qualifiers: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_period(self) -> "Fact":
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self

    @before_event(Insert, Replace, Save)
    async def require_evidence(self) -> None:
        refs = set(self.evidence_chunk_ids)
        if not refs or await EvidenceChunk.find(
            {
                "_id": {"$in": list(refs)},
                "document_id": self.document_id,
            }
        ).count() != len(refs):
            raise ValueError("Facts require valid evidence chunks from their source document")

    class Settings:
        name = "facts"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("document_id", ASCENDING)]),
            IndexModel([("subject", ASCENDING)]),
            IndexModel([("predicate", ASCENDING)]),
            IndexModel([("subject", ASCENDING), ("predicate", ASCENDING)]),
            IndexModel([("normalized_subject", ASCENDING)]),
            IndexModel([("normalized_predicate", ASCENDING)]),
            IndexModel(
                [
                    ("document_id", ASCENDING),
                    ("normalized_subject", ASCENDING),
                    ("value_type", ASCENDING),
                ]
            ),
        ]
