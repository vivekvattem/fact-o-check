import hashlib
import logging
from dataclasses import dataclass
from pathlib import PurePath

from anyio import to_thread
from beanie import PydanticObjectId
from fastapi import UploadFile, status
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.common import utc_now
from app.models.document import Document, DocumentStatus
from app.models.evidence_chunk import EvidenceChunk
from app.services.pdf_parser import ParsedPdf, parse_pdf

logger = logging.getLogger(__name__)

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
READ_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class IngestionResult:
    document: Document
    evidence_chunk_count: int
    already_existed: bool


async def _read_upload(upload: UploadFile, max_size: int) -> bytes:
    chunks: list[bytes] = []
    total_size = 0

    while True:
        read_size = min(READ_CHUNK_SIZE, max_size - total_size + 1)
        chunk = await upload.read(read_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise AppError(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                code="file_too_large",
                message=f"PDF exceeds the maximum upload size of {max_size} bytes",
            )
        chunks.append(chunk)

    if total_size == 0:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="empty_file",
            message="The uploaded PDF is empty",
        )
    return b"".join(chunks)


def _validate_pdf_type(upload: UploadFile, content: bytes) -> None:
    content_type = (upload.content_type or "").split(";", maxsplit=1)[0].lower()
    filename_is_pdf = bool(upload.filename and upload.filename.lower().endswith(".pdf"))
    declared_as_pdf = content_type in PDF_CONTENT_TYPES or filename_is_pdf
    if not declared_as_pdf or b"%PDF-" not in content[:1_024]:
        raise AppError(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="invalid_file_type",
            message="Only valid PDF uploads are accepted",
        )


async def _evidence_count(document_id: PydanticObjectId) -> int:
    return await EvidenceChunk.find(EvidenceChunk.document_id == document_id).count()


async def _mark_failed(document: Document, message: str) -> None:
    document.status = DocumentStatus.FAILED
    document.error_message = message[:2_000]
    document.updated_at = utc_now()
    await document.save()


async def _existing_result(document: Document) -> IngestionResult:
    return IngestionResult(
        document=document,
        evidence_chunk_count=await _evidence_count(document.id),
        already_existed=True,
    )


async def ingest_pdf(upload: UploadFile, settings: Settings) -> IngestionResult:
    content = await _read_upload(upload, settings.max_upload_size_bytes)
    _validate_pdf_type(upload, content)

    content_hash = hashlib.sha256(content).hexdigest()
    existing = await Document.find_one(Document.content_hash == content_hash)
    if existing is not None:
        return await _existing_result(existing)

    original_filename = upload.filename or "upload.pdf"
    safe_filename = PurePath(original_filename).name or "upload.pdf"
    document = Document(
        filename=safe_filename,
        original_filename=original_filename,
        content_hash=content_hash,
        mime_type="application/pdf",
        file_size_bytes=len(content),
        status=DocumentStatus.UPLOADED,
    )

    try:
        await document.insert()
    except DuplicateKeyError:
        concurrent_document = await Document.find_one(Document.content_hash == content_hash)
        if concurrent_document is None:
            raise
        return await _existing_result(concurrent_document)

    document.status = DocumentStatus.PROCESSING
    document.updated_at = utc_now()
    await document.save()

    try:
        parsed_pdf: ParsedPdf = await to_thread.run_sync(parse_pdf, content)
    except Exception as exc:
        error_message = f"PDF parsing failed: {exc}"
        logger.info("PDF parsing failed for document %s", document.id)
        await _mark_failed(document, error_message)
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="pdf_processing_failed",
            message="The PDF could not be parsed",
            details={"document_id": str(document.id)},
        ) from exc

    evidence = [
        EvidenceChunk(
            document_id=document.id,
            page_number=block.page_number,
            block_index=block.block_index,
            text=block.text,
            bbox=block.bbox,
            metadata=block.metadata,
        )
        for block in parsed_pdf.blocks
    ]

    try:
        if evidence:
            await EvidenceChunk.insert_many(evidence)
        document.page_count = parsed_pdf.page_count
        document.status = DocumentStatus.PROCESSED
        document.error_message = None
        document.updated_at = utc_now()
        await document.save()
    except Exception as exc:
        try:
            await EvidenceChunk.find(EvidenceChunk.document_id == document.id).delete()
            await _mark_failed(document, f"Evidence persistence failed: {exc}")
        except PyMongoError:
            logger.exception("Could not complete ingestion failure cleanup")
        raise

    return IngestionResult(
        document=document,
        evidence_chunk_count=len(evidence),
        already_existed=False,
    )
