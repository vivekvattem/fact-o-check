import json
from datetime import date

import httpx
import pytest
from beanie import PydanticObjectId

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.document import Document, DocumentStatus
from app.models.evidence_chunk import EvidenceChunk
from app.models.fact import Fact
from app.models.fact_relation import FactRelation, FactRelationType
from app.schemas.relations import SemanticRelationDecision
from app.services.fact_extractor import ExtractorError
from app.services.relation_reasoner import (
    OpenAIRelationReasoner,
    OpenRouterRelationReasoner,
    get_relation_reasoner,
    relation_output_schema,
)
from app.services.relations import (
    _subject_match,
    classify_pair,
    compare_document_facts,
    deterministic_assessment,
)


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def fact(
    *,
    document_id=None,
    subject="Acme",
    predicate="Revenue",
    normalized_subject="acme",
    normalized_predicate="revenue",
    raw_value="₹1,266 million",
    normalized_value=12_660_000_000,
    value_type="CURRENCY",
    raw_unit="INR",
    normalized_unit="INR",
    metadata=None,
    **kwargs,
):
    return Fact(
        id=PydanticObjectId(),
        document_id=document_id or PydanticObjectId(),
        subject=subject,
        predicate=predicate,
        normalized_subject=normalized_subject,
        normalized_predicate=normalized_predicate,
        raw_value=raw_value,
        normalized_value=normalized_value,
        value_type=value_type,
        raw_unit=raw_unit,
        normalized_unit=normalized_unit,
        metadata=metadata or {},
        **kwargs,
    )


def relation_type(left: Fact, right: Fact) -> FactRelationType:
    decision = deterministic_assessment(left, right)
    assert decision is not None
    return decision.relation_type


@pytest.mark.parametrize(
    "left_fields,right_fields",
    [
        ({}, {"raw_value": "₹1,266 million"}),
        (
            {
                "raw_value": "6.5%",
                "normalized_value": 6.5,
                "value_type": "PERCENTAGE",
                "raw_unit": "%",
                "normalized_unit": "PERCENT",
            },
            {
                "raw_value": "6.50 per cent",
                "normalized_value": 6.5,
                "value_type": "PERCENTAGE",
                "raw_unit": "per cent",
                "normalized_unit": "PERCENT",
            },
        ),
        (
            {"raw_value": "₹81,415.38 million", "normalized_value": 81_415_380_000},
            {"raw_value": "₹81,420.00 million", "normalized_value": 81_420_000_000},
        ),
    ],
)
def test_corroborates_equal_typed_and_rounded_values(left_fields, right_fields):
    left, right = fact(**left_fields), fact(**right_fields)
    decision = deterministic_assessment(left, right)
    assert decision is not None
    assert decision.relation_type is FactRelationType.CORROBORATES
    assert decision.reasoning_details["value_comparison"]["tolerance_used"]


def test_equivalent_scaled_currency_is_reconcilable():
    rules = {"normalization": {"rules_applied": ["million_to_inr"]}}
    left = fact(metadata=rules)
    right = fact(
        raw_value="₹126.6 crore",
        raw_unit="INR crore",
        metadata={"normalization": {"rules_applied": ["crore_to_inr"]}},
    )
    decision = deterministic_assessment(left, right)
    assert decision is not None
    assert decision.relation_type is FactRelationType.RECONCILABLE
    assert decision.reasoning_details["unit_equivalence"] is True


def test_scaled_currency_rounding_is_reconcilable():
    left = fact(
        raw_value="₹1,266 Mn",
        normalized_value=1_266_000_000,
        value_type="NUMBER",
        metadata={"normalization": {"rules_applied": ["mn_to_inr"]}},
    )
    right = fact(
        raw_value="Rs. 127 Cr",
        normalized_value=1_270_000_000,
        metadata={"normalization": {"rules_applied": ["cr_to_inr"]}},
    )

    decision = deterministic_assessment(left, right)

    assert decision is not None
    assert decision.relation_type is FactRelationType.RECONCILABLE
    assert decision.reasoning_details["value_comparison"]["scale_rounding_used"] is True


def test_generic_value_predicates_compare_the_metric_subject():
    left = fact(normalized_predicate="value")
    right = fact(normalized_predicate="to")

    assert relation_type(left, right) is FactRelationType.CORROBORATES


def test_currency_normalized_from_number_type_is_compatible():
    left = fact(value_type="NUMBER")
    right = fact(raw_value="₹126.6 crore", value_type="CURRENCY")

    decision = deterministic_assessment(left, right)

    assert decision is not None
    assert decision.relation_type is FactRelationType.CORROBORATES


@pytest.mark.parametrize(
    "left_fields,right_fields",
    [
        ({"normalized_value": 100}, {"normalized_value": 150}),
        (
            {
                "raw_value": "yes",
                "normalized_value": True,
                "value_type": "BOOLEAN",
                "raw_unit": None,
                "normalized_unit": "BOOLEAN",
            },
            {
                "raw_value": "no",
                "normalized_value": False,
                "value_type": "BOOLEAN",
                "raw_unit": None,
                "normalized_unit": "BOOLEAN",
            },
        ),
        (
            {
                "raw_value": "active",
                "normalized_value": None,
                "value_type": "STRING",
                "raw_unit": None,
                "normalized_unit": None,
            },
            {
                "raw_value": "inactive",
                "normalized_value": None,
                "value_type": "STRING",
                "raw_unit": None,
                "normalized_unit": None,
            },
        ),
    ],
)
def test_material_numeric_and_boolean_conflicts_contradict(left_fields, right_fields):
    left, right = fact(**left_fields), fact(**right_fields)
    assert relation_type(left, right) is FactRelationType.CONTRADICTS


@pytest.mark.parametrize(
    "context_a,context_b,expected_dimension",
    [
        (
            {"period_start": date(2023, 4, 1), "period_end": date(2024, 3, 31)},
            {"period_start": date(2024, 4, 1), "period_end": date(2025, 3, 31)},
            "temporal",
        ),
        ({"scope": "India operations"}, {"scope": "Global operations"}, "scope"),
        (
            {"qualifiers": {"basis": "estimate"}},
            {"qualifiers": {"basis": "actual"}},
            "qualifiers",
        ),
    ],
)
def test_explicit_context_explains_reconcilable_mismatch(
    context_a, context_b, expected_dimension
):
    left = fact(normalized_value=100, **context_a)
    right = fact(normalized_value=150, **context_b)
    decision = deterministic_assessment(left, right)
    assert decision is not None
    assert decision.relation_type is FactRelationType.RECONCILABLE
    assert expected_dimension in decision.reasoning_details["context"]["differences"]


def test_explicit_approximation_can_reconcile_rounding():
    left = fact(raw_value="about ₹100 million", normalized_value=100_000_000)
    right = fact(raw_value="₹100.4 million", normalized_value=100_400_000)
    decision = deterministic_assessment(left, right)
    assert decision is not None
    assert decision.relation_type is FactRelationType.RECONCILABLE
    assert decision.reasoning_details["value_comparison"]["rounding_indicators_present"]


@pytest.mark.parametrize(
    "right_fields",
    [
        {"subject": "Beta", "normalized_subject": "beta"},
        {"predicate": "Headcount", "normalized_predicate": "headcount"},
        {"scope": "Global", "normalized_value": 100},
    ],
)
def test_clearly_different_claims_are_unrelated(right_fields):
    left = fact(scope="India", normalized_value=100)
    right = fact(**right_fields)
    assert relation_type(left, right) is FactRelationType.UNRELATED


def test_conservative_subject_matching_handles_reporting_phrases_only():
    revenue = fact(subject="Revenue", normalized_subject="revenue")
    operations = fact(
        subject="Revenue from operations",
        normalized_subject="revenue from operations",
    )
    adjusted_ebitda = fact(subject="Adjusted EBITDA", normalized_subject="adjusted ebitda")
    ebitda = fact(subject="EBITDA", normalized_subject="ebitda")

    match = _subject_match(revenue, operations)

    assert match is not None and match["method"] == "common_reporting_phrase"
    assert _subject_match(adjusted_ebitda, ebitda) is None


def test_missing_normalization_and_context_prefer_review():
    missing_value = fact(normalized_value=None)
    assert relation_type(missing_value, fact()) is FactRelationType.NEEDS_REVIEW
    incomplete_context = fact(scope="India", normalized_value=100)
    assert (
        relation_type(incomplete_context, fact(normalized_value=150))
        is FactRelationType.NEEDS_REVIEW
    )


class FakeReasoner:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def compare(self, fact_a, fact_b, checks):
        self.calls.append((fact_a, fact_b, checks))
        if self.error:
            raise self.error
        return self.result


async def test_ambiguous_semantics_use_fallback_and_failure_is_review():
    left = fact(
        raw_value="profitable",
        normalized_value=None,
        value_type="STRING",
        raw_unit=None,
        normalized_unit=None,
    )
    right = fact(
        raw_value="in the black",
        normalized_value=None,
        value_type="STRING",
        raw_unit=None,
        normalized_unit=None,
    )
    semantic = FakeReasoner(
        SemanticRelationDecision(
            relation_type="CORROBORATES",
            confidence=0.8,
            explanation="Both phrases state profitability.",
            context_dimensions=[],
        )
    )
    result = await classify_pair(left, right, reasoner=semantic)
    assert result.relation_type is FactRelationType.CORROBORATES
    assert result.reasoning_details["semantic_fallback_used"] is True
    failed = await classify_pair(
        left,
        right,
        reasoner=FakeReasoner(error=ExtractorError("malformed_output")),
    )
    assert failed.relation_type is FactRelationType.NEEDS_REVIEW


async def test_clear_deterministic_pair_never_calls_reasoner():
    reasoner = FakeReasoner(error=AssertionError("must not be called"))
    result = await classify_pair(fact(), fact(), reasoner=reasoner)
    assert result.relation_type is FactRelationType.CORROBORATES
    assert reasoner.calls == []


async def test_relation_provider_rejects_invalid_structured_output(monkeypatch):
    async def handle(_request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"content": '{"relation_type":"NOPE"}'}}
                ]
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    reasoner = OpenRouterRelationReasoner(
        settings(llm_provider="openrouter", openrouter_api_key="fake", llm_model="vendor/model")
    )
    with pytest.raises(ExtractorError, match="malformed_output"):
        await reasoner.compare({}, {}, {})


async def test_openrouter_relation_provider_uses_configured_endpoint(monkeypatch):
    seen = {}

    async def handle(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["payload"] = request.content
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "relation_type": "NEEDS_REVIEW",
                                    "confidence": 0.5,
                                    "explanation": "Context is ambiguous.",
                                    "context_dimensions": ["scope"],
                                    "needs_review_reason": "Scope is unclear.",
                                }
                            )
                        },
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
    reasoner = OpenRouterRelationReasoner(
        settings(
            llm_provider="openrouter",
            llm_model="vendor/model",
            openrouter_api_key="router-key",
            openrouter_base_url="https://router.example/api/v1/",
            openrouter_http_referer="https://fact-o-check.example",
            openrouter_x_title="Fact-O-Check",
        )
    )
    result = await reasoner.compare({}, {}, {})
    assert result.relation_type is FactRelationType.NEEDS_REVIEW
    assert seen["url"] == "https://router.example/api/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer router-key"
    assert seen["headers"]["http-referer"] == "https://fact-o-check.example"
    assert b'"model":"vendor/model"' in seen["payload"]


def test_relation_provider_selection_and_configuration_errors():
    assert isinstance(
        get_relation_reasoner(settings(llm_api_key="openai-key")),
        OpenAIRelationReasoner,
    )
    assert isinstance(
        get_relation_reasoner(
            settings(llm_provider="openrouter", openrouter_api_key="router-key")
        ),
        OpenRouterRelationReasoner,
    )
    with pytest.raises(AppError, match="active provider API key"):
        get_relation_reasoner(settings(llm_provider="openrouter"))
    with pytest.raises(AppError, match="must be 'openai' or 'openrouter'"):
        get_relation_reasoner(settings(llm_provider="unknown", llm_api_key="key"))


def test_relation_provider_schema_is_strict():
    schema = relation_output_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


async def persisted_fact(document, chunk, value, *, predicate="Revenue"):
    return await Fact(
        document_id=document.id,
        evidence_chunk_ids=[chunk.id],
        subject="Acme",
        predicate=predicate,
        normalized_subject="acme",
        normalized_predicate=predicate.casefold(),
        raw_value=str(value),
        normalized_value=value,
        value_type="NUMBER",
        normalized_unit="COUNT",
        extraction_confidence=0.9,
    ).insert()


async def source(filename, value):
    document = await Document(
        filename=filename,
        original_filename=filename,
        content_hash=f"hash-{filename}",
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
    ).insert()
    chunk = await EvidenceChunk(
        document_id=document.id,
        page_number=2,
        block_index=0,
        text=f"Acme revenue was {value}.",
    ).insert()
    fact_record = await persisted_fact(document, chunk, value)
    return document, chunk, fact_record


async def test_incremental_comparison_duplicate_and_reversed_pair_prevention():
    first, _, first_fact = await source("first.pdf", 100)
    second, _, second_fact = await source("second.pdf", 100)
    initial = await compare_document_facts(second.id, settings())
    assert (initial.pairs_considered, initial.relations_created, initial.corroborates) == (1, 1, 1)
    repeated = await compare_document_facts(first.id, settings())
    assert repeated.relations_created == 0
    assert repeated.duplicates_skipped == 1
    relation = await FactRelation.find_one()
    assert relation is not None
    assert {relation.fact_a_id, relation.fact_b_id} == {first_fact.id, second_fact.id}

    third, _, _ = await source("third.pdf", 100)
    incremental = await compare_document_facts(third.id, settings())
    assert incremental.pairs_considered == 2
    assert incremental.relations_created == 2
    assert await FactRelation.count() == 3


async def test_document_comparison_can_disable_semantic_fallback():
    _first, _, _ = await source("first.pdf", 100)
    second, _, _ = await source("second.pdf", 100)
    second_fact = await Fact.find_one(Fact.document_id == second.id)
    second_fact.predicate = "Revenue amount"
    second_fact.normalized_predicate = None
    await second_fact.save()
    reasoner = FakeReasoner(error=AssertionError("must not be called"))

    summary = await compare_document_facts(
        second.id,
        settings(),
        reasoner=reasoner,
        allow_semantic_fallback=False,
    )

    assert summary.needs_review == 1
    assert reasoner.calls == []


async def test_document_comparison_can_refresh_existing_relation():
    first, _, _ = await source("first.pdf", 100)
    second, _, second_fact = await source("second.pdf", 100)
    await compare_document_facts(second.id, settings())
    second_fact.raw_value = "150"
    second_fact.normalized_value = None
    await second_fact.save()

    await compare_document_facts(first.id, settings(), refresh_existing=True)

    relation = await FactRelation.find_one()
    assert relation is not None
    assert relation.relation_type is FactRelationType.CONTRADICTS


async def test_comparison_normalizes_pool_and_records_lexical_candidate_match():
    _first, _, first_fact = await source("first.pdf", 100)
    second, _, second_fact = await source("second.pdf", 100)
    first_fact.subject = "Revenue"
    first_fact.predicate = "value"
    first_fact.normalized_subject = None
    first_fact.normalized_predicate = None
    await first_fact.save()
    second_fact.subject = "Revenue from operations"
    second_fact.predicate = "value"
    second_fact.normalized_subject = None
    second_fact.normalized_predicate = None
    await second_fact.save()

    summary = await compare_document_facts(second.id, settings())

    assert summary.corroborates == 1
    relation = await FactRelation.find_one()
    assert relation is not None
    assert relation.reasoning_details["candidate_match"]["method"] == (
        "common_reporting_phrase"
    )
    assert (await Fact.get(first_fact.id)).normalized_subject == "revenue"


async def test_relation_api_filters_and_detail_are_evidence_grounded(client):
    first, _, _ = await source("annual.pdf", 100)
    second, _, _ = await source("presentation.pdf", 150)
    response = await client.post(f"/api/documents/{second.id}/compare-facts")
    assert response.status_code == 200
    assert response.json()["contradicts"] == 1

    filtered = await client.get(
        "/api/relations",
        params={
            "relation_type": "CONTRADICTS",
            "document_id": str(first.id),
            "subject": "Acme",
            "min_confidence": 0.9,
        },
    )
    payload = filtered.json()
    assert filtered.status_code == 200
    assert payload["total"] == 1
    relation = payload["items"][0]
    assert relation["fact_a"]["source_document"]["original_filename"] in {
        "annual.pdf",
        "presentation.pdf",
    }
    assert relation["fact_a"]["evidence"][0]["page_number"] == 2
    assert "Acme revenue" in relation["fact_b"]["evidence"][0]["text"]
    assert relation["reasoning_details"]["deterministic"] is True

    detail = await client.get(f"/api/relations/{relation['id']}")
    assert detail.status_code == 200
    assert detail.json()["fact_a"]["raw_value"] in {"100", "150"}
    missing = await client.get(f"/api/relations/{PydanticObjectId()}")
    assert missing.status_code == 404


async def test_deleting_document_cascades_relations(client):
    first, _, _ = await source("delete.pdf", 100)
    second, _, _ = await source("keep.pdf", 100)
    await compare_document_facts(second.id, settings())
    assert await FactRelation.count() == 1
    response = await client.delete(f"/api/documents/{first.id}")
    assert response.status_code == 204
    assert await FactRelation.count() == 0
