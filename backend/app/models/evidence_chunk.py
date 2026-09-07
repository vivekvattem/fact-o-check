from datetime import datetime
from typing import Any, ClassVar

from beanie import Document as BeanieDocument
from beanie import PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.models.common import utc_now


class EvidenceChunk(BeanieDocument):
    document_id: PydanticObjectId
    page_number: int = Field(ge=1)
    text: str = Field(min_length=1)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "evidence_chunks"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("document_id", ASCENDING)]),
            IndexModel([("document_id", ASCENDING), ("page_number", ASCENDING)]),
        ]
