import asyncio
import json
import logging

import httpx
import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.document import Document, DocumentStatus
from app.models.evidence_chunk import EvidenceChunk
from app.models.fact import Fact
from app.schemas.facts import FactCandidate
from app.services import facts as service
from app.services.fact_extractor import (
    PROMPT,
    EvidenceContext,
    ExtractorError,
    OpenAIFactExtractor,
    OpenRouterFactExtractor,
    build_windows,
    get_fact_extractor,
    output_schema,
)


def test_extraction_prompt_requires_stable_claim_roles_and_atomic_numeric_values():
    assert "never use a period" in PROMPT
    assert "concise stable metric/property name" in PROMPT
    assert "raw_value must be only the exact numeric literal" in PROMPT


class FakeFactExtractor:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    async def extract(self, window):
        self.calls.append(window)
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


async def source(text="Acme reported revenue of $1.2B in 2025. Acme is carbon neutral.", **kwargs):
    document = await Document(
        filename="report.pdf",
        original_filename="report.pdf",
        content_hash=str(PydanticObjectId()),
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        **kwargs,
    ).insert()
    chunk = await EvidenceChunk(
        document_id=document.id,
        page_number=1,
        block_index=0,
        text=text,
    ).insert()
    return document, chunk


def candidate(chunk, **kwargs):
    return {
        "evidence_chunk_ids": [str(chunk.id)],
        "subject": "Acme",
        "predicate": "revenue",
        "raw_value": "$1.2B",
        "value_type": "CURRENCY",
        "raw_unit": "USD",
        "extraction_confidence": 0.9,
        **kwargs,
    }


async def test_numeric_string_temporal_qualifiers_and_idempotency():
    document, chunk = await source()
    numeric = candidate(
        chunk,
        period_start="2025-01-01",
        period_end="2025-12-31",
        qualifiers={"basis": "reported", "segments": ["all"]},
    )
    semantic = candidate(
        chunk,
        predicate="sustainability",
        raw_value="carbon neutral",
        value_type="STRING",
        raw_unit=None,
        as_of_date="2025-12-31",
    )
    first = await service.extract_document_facts(
        document.id,
        settings(),
        FakeFactExtractor([[numeric, semantic, numeric]]),
    )
    assert (first.facts_created, first.facts_deduplicated) == (2, 1)
    second = await service.extract_document_facts(
        document.id,
        settings(),
        FakeFactExtractor([[numeric, semantic]]),
    )
    assert (second.facts_created, second.facts_deduplicated) == (0, 2)
    facts = await Fact.find_all().to_list()
    assert all(f.normalized_value is None and f.normalized_unit is None for f in facts)
    assert facts[0].qualifiers == numeric["qualifiers"]
    assert str(facts[0].period_end) == "2025-12-31"
    assert facts[1].raw_value == "carbon neutral"


async def test_dedup_keeps_distinct_context_and_nonoverlapping_evidence():
    document, chunk = await source()
    other = await EvidenceChunk(
        document_id=document.id,
        page_number=2,
        block_index=0,
        text=chunk.text,
    ).insert()
    candidates = [
        candidate(chunk),
        candidate(chunk, scope="group"),
        candidate(chunk, as_of_date="2025-12-31"),
        candidate(chunk, qualifiers={"basis": "estimated"}),
        candidate(other),
    ]
    result = await service.extract_document_facts(
        document.id,
        settings(),
        FakeFactExtractor([candidates]),
    )
    assert result.facts_created == 5


async def test_invalid_schema_and_evidence_are_rejected():
    document, chunk = await source()
    _, foreign = await source()
    candidates = [
        candidate(chunk, evidence_chunk_ids=[]),
        candidate(chunk, evidence_chunk_ids=[str(PydanticObjectId())]),
        candidate(chunk, evidence_chunk_ids=[str(foreign.id)]),
        candidate(chunk, evidence_chunk_ids=[str(chunk.id), str(foreign.id)]),
        candidate(chunk, raw_value="$99B"),
        candidate(chunk, subject="   "),
        candidate(chunk, extraction_confidence=1.1),
        candidate(chunk, value_type="BOGUS"),
        candidate(chunk, period_start="2026-01-01", period_end="2025-01-01"),
        candidate(chunk, normalized_value=1200000000),
        candidate(chunk),
    ]
    result = await service.extract_document_facts(
        document.id,
        settings(),
        FakeFactExtractor([candidates]),
    )
    assert result.candidates_rejected == 10
    assert result.facts_created == 1
    assert result.status == "partial"
    with pytest.raises(ValidationError):
        FactCandidate.model_validate(candidate(chunk, evidence_chunk_ids=[]))


async def test_partial_failure_keeps_success_and_previous_facts():
    document, chunk = await source()
    await EvidenceChunk(
        document_id=document.id, page_number=2, block_index=0, text="Other."
    ).insert()
    result = await service.extract_document_facts(
        document.id,
        settings(extraction_window_chunks=1),
        FakeFactExtractor([[candidate(chunk)], ExtractorError("provider_timeout")]),
    )
    assert result.status == "partial"
    assert (result.windows_processed, result.windows_failed, result.facts_created) == (2, 1, 1)
    retry = await service.extract_document_facts(
        document.id,
        settings(),
        FakeFactExtractor([ExtractorError("malformed_output")]),
    )
    assert retry.status == "failed"
    assert await Fact.find_all().count() == 1


async def test_window_scope_rejects_other_window_reference():
    document, chunk = await source()
    other = await EvidenceChunk(
        document_id=document.id,
        page_number=2,
        block_index=0,
        text=chunk.text,
    ).insert()
    result = await service.extract_document_facts(
        document.id,
        settings(extraction_window_chunks=1),
        FakeFactExtractor([[candidate(other)], []]),
    )
    assert result.candidates_rejected == 1
    assert result.facts_created == 0


async def test_empty_and_malformed_results_and_window_cap():
    document, chunk = await source()
    result = await service.extract_document_facts(document.id, settings(), FakeFactExtractor([[]]))
    assert result.status == "completed" and result.facts_created == 0
    result = await service.extract_document_facts(document.id, settings(), FakeFactExtractor([{}]))
    assert result.status == "failed" and result.failures[0].code == "malformed_output"
    await EvidenceChunk(
        document_id=document.id, page_number=2, block_index=0, text="Next."
    ).insert()
    result = await service.extract_document_facts(
        document.id,
        settings(extraction_window_chunks=1, extraction_max_windows=1),
        FakeFactExtractor([[candidate(chunk)]]),
    )
    assert result.windows_skipped == 1 and result.status == "partial"


async def test_window_bounds_order_no_overlap_or_dropped_text():
    document, chunk = await source(text="a" * 1100)
    other = await EvidenceChunk(
        document_id=document.id,
        page_number=2,
        block_index=0,
        text="b" * 250,
    ).insert()
    windows = build_windows([other, chunk], settings(extraction_window_chars=500))
    assert all(sum(len(c.text) for c in w) <= 500 for w in windows)
    assert "".join(c.text for w in windows for c in w) == chunk.text + other.text
    assert len(windows) == len(set(windows))


async def test_windows_preserve_layout_coordinates_for_table_association():
    _, chunk = await source()
    chunk.bbox = [10.0, 20.0, 30.0, 40.0]
    await chunk.save()

    windows = build_windows([chunk], settings())

    assert windows[0][0].bbox == (10.0, 20.0, 30.0, 40.0)


async def test_api_workflow_filters_detail_provenance_and_delete(client, monkeypatch):
    document, chunk = await source()
    fake = FakeFactExtractor([[candidate(chunk)]])
    monkeypatch.setattr(service, "get_fact_extractor", lambda _: fake)
    response = await client.post(f"/api/documents/{document.id}/extract-facts")
    assert response.status_code == 200 and response.json()["facts_created"] == 1
    response = await client.get(
        "/api/facts",
        params={
            "document_id": str(document.id),
            "subject": "Acme",
            "predicate": "revenue",
            "value_type": "CURRENCY",
            "limit": 1,
        },
    )
    assert response.status_code == 200
    fact = response.json()["items"][0]
    assert fact["source_document"]["original_filename"] == "report.pdf"
    assert fact["page_numbers"] == [1] and fact["evidence"][0]["text"] == chunk.text
    assert (await client.get(f"/api/facts/{fact['id']}")).json() == fact
    assert (await client.get("/api/facts?subject=other")).json()["total"] == 0
    assert (await client.get("/api/facts?offset=1")).json()["items"] == []
    assert (await client.get(f"/api/facts/{PydanticObjectId()}")).status_code == 404
    assert (await client.get("/api/facts/not-an-id")).status_code == 422
    assert (await client.delete(f"/api/documents/{document.id}")).status_code == 204
    assert await Fact.find_all().count() == 0


async def test_missing_config_status_and_missing_document(client, monkeypatch):
    from app.core.config import get_settings
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: settings(llm_api_key="")
    try:
        document, _ = await source()
        response = await client.post(f"/api/documents/{document.id}/extract-facts")
        assert (
            response.status_code == 503 and response.json()["error"]["code"] == "llm_not_configured"
        )
        document.status = DocumentStatus.FAILED
        await document.save()
        assert (await client.post(f"/api/documents/{document.id}/extract-facts")).status_code == 409
        assert (
            await client.post(f"/api/documents/{PydanticObjectId()}/extract-facts")
        ).status_code == 404
        assert (await client.get("/health")).status_code == 200
    finally:
        app.dependency_overrides.clear()


async def test_lease_blocks_concurrent_extraction_and_delete(client):
    document, _ = await source()
    async with service.document_fact_lease(document.id):
        with pytest.raises(AppError, match="busy"):
            await service.extract_document_facts(document.id, settings(), FakeFactExtractor([[]]))
        assert (await client.delete(f"/api/documents/{document.id}")).status_code == 409
    result = await service.extract_document_facts(document.id, settings(), FakeFactExtractor([[]]))
    assert result.status == "completed"


async def test_workflow_enforces_timeout():
    document, _ = await source()

    class SlowExtractor:
        async def extract(self, window):
            await asyncio.sleep(1)

    result = await service.extract_document_facts(
        document.id,
        settings(llm_timeout_seconds=0.001),
        SlowExtractor(),
    )
    assert result.failures[0].code == "provider_timeout"


@pytest.mark.parametrize(
    "mode", ["success", "malformed", "timeout", "http", "refusal", "truncated"]
)
async def test_openai_adapter_without_network(monkeypatch, mode):
    _, chunk = await source()
    wire_candidate = candidate(chunk, qualifiers=[{"key": "basis", "value": "reported"}])

    async def handle(request):
        payload = json.loads(request.content)
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert str(chunk.id) in payload["messages"][1]["content"]
        assert "bbox" in payload["messages"][1]["content"]
        if mode == "timeout":
            raise httpx.ReadTimeout("secret provider details", request=request)
        if mode == "http":
            return httpx.Response(401, json={"secret": "do not expose"})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length" if mode == "truncated" else "stop",
                        "message": {
                            "refusal": "no" if mode == "refusal" else None,
                            "content": "invalid"
                            if mode == "malformed"
                            else json.dumps({"facts": [wire_candidate]}),
                        },
                    }
                ]
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original(
            transport=httpx.MockTransport(handle),
            **kw,
        ),
    )
    extractor = OpenAIFactExtractor(settings(llm_api_key="fake-test-key"))
    window = (EvidenceContext(str(chunk.id), 1, chunk.text, bbox=(1, 2, 3, 4)),)
    if mode == "success":
        result = await extractor.extract(window)
        assert result[0]["qualifiers"] == {"basis": "reported"}
    else:
        with pytest.raises(ExtractorError) as caught:
            await extractor.extract(window)
        assert "secret" not in str(caught.value)


async def test_provider_http_error_is_safely_logged(monkeypatch, caplog):
    async def handle(request):
        return httpx.Response(
            401,
            json={"error": {"type": "authentication_error", "message": "Invalid key fake-key"}},
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    extractor = OpenRouterFactExtractor(
        settings(openrouter_api_key="fake-key", llm_model="vendor/model")
    )
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(ExtractorError, match="provider_unavailable"),
    ):
        await extractor.extract((EvidenceContext("smoke", 1, "Synthetic evidence."),))

    assert "provider=openrouter" in caplog.text
    assert "status_code=401" in caplog.text
    assert "error_type=authentication_error" in caplog.text
    assert "Invalid key [REDACTED]" in caplog.text
    assert "fake-key" not in caplog.text


def test_strict_provider_schema():
    schema = output_schema()

    def inspect(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                inspect(value)
        elif isinstance(node, list):
            for item in node:
                inspect(item)

    inspect(schema)


def test_provider_selection_and_missing_keys():
    assert isinstance(get_fact_extractor(settings(llm_api_key="openai-key")), OpenAIFactExtractor)
    assert isinstance(
        get_fact_extractor(
            settings(
                llm_provider="openrouter", openrouter_api_key="router-key", llm_model="vendor/model"
            )
        ),
        OpenRouterFactExtractor,
    )
    with pytest.raises(AppError, match="OPENROUTER_API_KEY"):
        get_fact_extractor(settings(llm_provider="openrouter"))
    with pytest.raises(AppError, match="must be 'openai' or 'openrouter'"):
        get_fact_extractor(settings(llm_provider="other", llm_api_key="key"))
    with pytest.raises(AppError, match="LLM_MODEL"):
        get_fact_extractor(settings(llm_model="", llm_api_key="key"))


async def test_openrouter_adapter_uses_configured_base_url_and_headers(monkeypatch):
    _, chunk = await source()
    seen = {}

    async def handle(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps({"facts": [candidate(chunk)]})},
                    }
                ]
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    configured = settings(
        llm_provider="openrouter",
        llm_model="vendor/model",
        openrouter_api_key="router-key",
        openrouter_base_url="https://router.example/api/v1/",
        openrouter_http_referer="https://fact-o-check.example",
        openrouter_x_title="Fact-O-Check",
    )
    result = await get_fact_extractor(configured).extract(
        (EvidenceContext(str(chunk.id), chunk.page_number, chunk.text),)
    )
    assert result == [candidate(chunk)]
    assert seen["url"] == "https://router.example/api/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer router-key"
    assert seen["headers"]["http-referer"] == "https://fact-o-check.example"
    assert seen["headers"]["x-title"] == "Fact-O-Check"
    assert seen["payload"]["model"] == "vendor/model"
    assert seen["payload"]["response_format"]["json_schema"]["strict"] is True


async def test_openrouter_uses_default_base_url_without_optional_headers(monkeypatch):
    _, chunk = await source()
    seen = {}

    async def handle(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps({"facts": []})},
                    }
                ]
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    extractor = OpenRouterFactExtractor(
        settings(openrouter_api_key="router-key", openrouter_x_title=None)
    )
    assert await extractor.extract((EvidenceContext(str(chunk.id), 1, chunk.text),)) == []
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert "http-referer" not in seen["headers"]
    assert "x-title" not in seen["headers"]


async def test_fact_persistence_requires_real_evidence():
    document, chunk = await source()
    for refs in ([], [PydanticObjectId()]):
        with pytest.raises(ValueError, match="valid evidence"):
            await Fact(
                document_id=document.id,
                evidence_chunk_ids=refs,
                subject="Acme",
                predicate="revenue",
            ).insert()
    _, foreign = await source()
    with pytest.raises(ValueError, match="valid evidence"):
        await Fact(
            document_id=document.id,
            evidence_chunk_ids=[foreign.id],
            subject="Acme",
            predicate="revenue",
        ).insert()
    fact = await Fact(
        document_id=document.id, evidence_chunk_ids=[chunk.id], subject="Acme", predicate="revenue"
    ).insert()
    fact.evidence_chunk_ids = []
    with pytest.raises(ValueError, match="valid evidence"):
        await fact.save()


@pytest.mark.parametrize(
    "value_type, raw_value",
    [
        ("NUMBER", "42"),
        ("PERCENTAGE", "12%"),
        ("CURRENCY", "$1.2B"),
        ("DATE", "2025-01-01"),
        ("BOOLEAN", "true"),
        ("STRING", "carbon neutral"),
        ("ENTITY", "Acme"),
        ("QUANTITY", "7 kg"),
    ],
)
async def test_all_value_types_preserve_original_strings(value_type, raw_value):
    document, chunk = await source(text=f"Acme reports {raw_value}.")
    result = await service.extract_document_facts(
        document.id,
        settings(),
        FakeFactExtractor(
            [
                [
                    candidate(chunk, value_type=value_type, raw_value=raw_value),
                ]
            ]
        ),
    )
    assert result.facts_created == 1
    fact = await Fact.find_one(Fact.document_id == document.id)
    assert fact.raw_value == raw_value and fact.value_type == value_type


async def test_no_evidence_makes_no_provider_calls():
    document, chunk = await source()
    await chunk.delete()
    fake = FakeFactExtractor([])
    result = await service.extract_document_facts(document.id, settings(), fake)
    assert result.status == "completed" and result.windows_total == 0
    assert fake.calls == []
