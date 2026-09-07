import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from time import monotonic
from uuid import uuid4

from beanie import PydanticObjectId
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.common import utc_now
from app.models.document import Document, DocumentStatus
from app.models.evidence_chunk import EvidenceChunk
from app.models.fact import Fact
from app.schemas.documents import EvidenceChunkResponse
from app.schemas.facts import (
    ExtractionSummary,
    FactCandidate,
    FactResponse,
    SourceDocument,
    WindowFailure,
)
from app.services.documents import get_document_or_404
from app.services.fact_extractor import (
    ExtractorError,
    FactExtractor,
    build_windows,
    get_fact_extractor,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def document_fact_lease(document_id: PydanticObjectId) -> AsyncIterator[None]:
    """Cross-worker exclusion for extraction/deletion, with crash recovery after five minutes."""
    token = uuid4().hex
    collection = Document.get_motor_collection()
    result = await collection.update_one(
        {
            "_id": document_id,
            "$or": [
                {"fact_lease_until": {"$exists": False}},
                {"fact_lease_until": {"$lte": utc_now()}},
            ],
        },
        {"$set": {"fact_lease_token": token, "fact_lease_until": utc_now() + timedelta(minutes=5)}},
    )
    if not result.modified_count:
        await get_document_or_404(document_id)
        raise AppError(
            status_code=409, code="document_busy", message="Document is busy; retry later."
        )
    try:
        yield
    finally:
        await collection.update_one(
            {"_id": document_id, "fact_lease_token": token},
            {"$unset": {"fact_lease_token": "", "fact_lease_until": ""}},
        )


def identity(fact: Fact | FactCandidate) -> str:
    fields = (
        "subject",
        "predicate",
        "raw_value",
        "value_type",
        "raw_unit",
        "period_start",
        "period_end",
        "as_of_date",
        "geography",
        "scope",
        "qualifiers",
    )
    # Deliberately exact, including case and qualifiers: no semantic normalization.
    return json.dumps({key: getattr(fact, key) for key in fields}, sort_keys=True, default=str)


async def extract_document_facts(
    document_id: PydanticObjectId,
    settings: Settings,
    extractor: FactExtractor | None = None,
) -> ExtractionSummary:
    document = await get_document_or_404(document_id)
    if document.status != DocumentStatus.PROCESSED:
        raise AppError(
            status_code=409,
            code="document_not_processed",
            message="Only PROCESSED documents can be used for fact extraction.",
        )
    extractor = extractor or get_fact_extractor(settings)
    started = monotonic()
    summary = ExtractionSummary(document_id=document_id)
    async with document_fact_lease(document_id):
        chunks = await EvidenceChunk.find(EvidenceChunk.document_id == document_id).to_list()
        windows = build_windows(chunks, settings)
        summary.windows_total = len(windows)
        existing = await Fact.find(Fact.document_id == document_id).to_list()
        known: dict[str, list[set[PydanticObjectId]]] = {}
        for fact in existing:
            known.setdefault(identity(fact), []).append(set(fact.evidence_chunk_ids))
        for index, window in enumerate(windows):
            # Bound the whole request as well as each provider call. No hidden paid retries.
            remaining = 180 - (monotonic() - started)
            if index >= settings.extraction_max_windows or remaining <= 0:
                summary.windows_skipped = len(windows) - index
                break
            summary.windows_processed += 1
            try:
                async with asyncio.timeout(min(remaining, settings.llm_timeout_seconds)):
                    candidates = await extractor.extract(window)
                if not isinstance(candidates, list):
                    raise ExtractorError("malformed_output")
            except (ExtractorError, TimeoutError) as exc:
                code = "provider_timeout" if isinstance(exc, TimeoutError) else str(exc)
                summary.windows_failed += 1
                summary.failures.append(WindowFailure(window=index + 1, code=code))
                continue
            allowed = {PydanticObjectId(part.chunk_id) for part in window}
            for raw_candidate in candidates:
                try:
                    candidate = FactCandidate.model_validate(raw_candidate)
                except ValidationError:
                    summary.candidates_rejected += 1
                    continue
                refs = set(candidate.evidence_chunk_ids)
                if not refs <= allowed or not any(
                    candidate.raw_value in part.text
                    for part in window
                    if PydanticObjectId(part.chunk_id) in refs
                ):
                    summary.candidates_rejected += 1
                    continue
                summary.facts_produced += 1
                key = identity(candidate)
                if any(refs & previous for previous in known.get(key, [])):
                    summary.facts_deduplicated += 1
                    continue
                await Fact(
                    document_id=document_id,
                    **candidate.model_dump(exclude={"evidence_chunk_ids"}),
                    evidence_chunk_ids=sorted(refs, key=str),
                    metadata={
                        "provider": settings.llm_provider,
                        "model": settings.llm_model,
                        "extraction_version": "phase2-v1",
                        "window": index + 1,
                    },
                ).insert()
                known.setdefault(key, []).append(refs)
                summary.facts_created += 1
    if summary.windows_failed or summary.windows_skipped or summary.candidates_rejected:
        summary.status = "partial"
        if summary.windows_failed == summary.windows_processed and summary.windows_processed:
            summary.status = "failed"
    summary.duration_seconds = round(monotonic() - started, 3)
    logger.info(
        "Fact extraction document=%s windows=%d failed=%d produced=%d created=%d duration=%.3fs",
        document_id,
        summary.windows_processed,
        summary.windows_failed,
        summary.facts_produced,
        summary.facts_created,
        summary.duration_seconds,
    )
    return summary


async def serialize_facts(facts: list[Fact]) -> list[FactResponse]:
    if not facts:
        return []
    documents = await Document.find(
        {"_id": {"$in": list({f.document_id for f in facts})}}
    ).to_list()
    sources = {
        d.id: SourceDocument(id=d.id, original_filename=d.original_filename) for d in documents
    }
    ids = list({ref for fact in facts for ref in fact.evidence_chunk_ids})
    chunks = await EvidenceChunk.find({"_id": {"$in": ids}}).to_list()
    by_id = {c.id: c for c in chunks}
    responses = []
    for fact in facts:
        evidence = sorted(
            [
                by_id[ref]
                for ref in fact.evidence_chunk_ids
                if ref in by_id and by_id[ref].document_id == fact.document_id
            ],
            key=lambda c: (c.page_number, c.block_index),
        )
        responses.append(
            FactResponse(
                **fact.model_dump(exclude={"metadata"}),
                # Expose only application-controlled metadata, never legacy provider payloads.
                metadata={
                    k: fact.metadata[k]
                    for k in ("provider", "model", "extraction_version", "window")
                    if k in fact.metadata
                },
                source_document=sources.get(fact.document_id),
                page_numbers=sorted({c.page_number for c in evidence}),
                evidence=[EvidenceChunkResponse.from_chunk(c) for c in evidence],
            )
        )
    return responses
