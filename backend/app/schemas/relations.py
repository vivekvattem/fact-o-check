from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from app.models.fact_relation import FactRelationType
from app.schemas.facts import FactResponse


class SemanticRelationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relation_type: FactRelationType
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1, max_length=2000)
    context_dimensions: list[str] = Field(default_factory=list, max_length=20)
    needs_review_reason: str | None = Field(default=None, max_length=1000)


class RelationComparisonSummary(BaseModel):
    document_id: PydanticObjectId
    pairs_considered: int = 0
    relations_created: int = 0
    duplicates_skipped: int = 0
    corroborates: int = 0
    contradicts: int = 0
    reconcilable: int = 0
    needs_review: int = 0
    unrelated: int = 0


class RelationResponse(BaseModel):
    id: PydanticObjectId
    fact_a_id: PydanticObjectId
    fact_b_id: PydanticObjectId
    relation_type: FactRelationType
    confidence: float | None
    explanation: str | None
    reasoning_details: dict[str, Any]
    created_at: datetime
    fact_a: FactResponse
    fact_b: FactResponse


class RelationPageResponse(BaseModel):
    items: list[RelationResponse]
    total: int
    offset: int
    limit: int
