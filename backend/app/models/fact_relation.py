from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from beanie import Document as BeanieDocument
from beanie import PydanticObjectId
from pydantic import Field, model_validator
from pymongo import ASCENDING, IndexModel

from app.models.common import utc_now


class FactRelationType(StrEnum):
    CORROBORATES = "CORROBORATES"
    CONTRADICTS = "CONTRADICTS"
    RECONCILABLE = "RECONCILABLE"
    UNRELATED = "UNRELATED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class FactRelation(BeanieDocument):
    fact_a_id: PydanticObjectId
    fact_b_id: PydanticObjectId
    relation_type: FactRelationType
    confidence: float | None = Field(default=None, ge=0, le=1)
    explanation: str | None = None
    reasoning_details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_and_order_fact_pair(self) -> "FactRelation":
        if self.fact_a_id == self.fact_b_id:
            raise ValueError("a fact cannot have a relationship with itself")
        if str(self.fact_b_id) < str(self.fact_a_id):
            self.fact_a_id, self.fact_b_id = self.fact_b_id, self.fact_a_id
        return self

    class Settings:
        name = "fact_relations"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("fact_a_id", ASCENDING)]),
            IndexModel([("fact_b_id", ASCENDING)]),
            IndexModel([("relation_type", ASCENDING)]),
            IndexModel(
                [("fact_a_id", ASCENDING), ("fact_b_id", ASCENDING)],
                unique=True,
            ),
        ]
