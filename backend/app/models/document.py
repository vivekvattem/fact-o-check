from datetime import datetime
from enum import StrEnum
from typing import ClassVar

from beanie import Document as BeanieDocument
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.models.common import utc_now


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Document(BeanieDocument):
    filename: str = Field(min_length=1, max_length=512)
    original_filename: str = Field(min_length=1, max_length=512)
    content_hash: str = Field(min_length=1, max_length=128)
    mime_type: str = Field(min_length=1, max_length=255)
    page_count: int | None = Field(default=None, ge=0)
    file_size_bytes: int | None = Field(default=None, ge=0)
    status: DocumentStatus = DocumentStatus.UPLOADED
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "documents"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("content_hash", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]
