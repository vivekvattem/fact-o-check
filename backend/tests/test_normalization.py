from datetime import date

import pytest
from beanie import PydanticObjectId

from app.models.document import Document, DocumentStatus
from app.models.evidence_chunk import EvidenceChunk
from app.models.fact import Fact
from app.normalization.dates import normalize_temporal
from app.normalization.entities import normalize_entity
from app.normalization.predicates import normalize_predicate
from app.normalization.service import normalize_document_facts, normalize_fact_fields
from app.normalization.units import normalize_value


@pytest.mark.parametrize(
    ("raw", "raw_unit", "expected", "unit"),
    [
        ("₹1,266 million", None, 1_266_000_000, "INR"),
        ("₹126.6 crore", None, 1_266_000_000, "INR"),
        ("₹8,142 crore", None, 81_420_000_000, "INR"),
        ("₹81,420 million", None, 81_420_000_000, "INR"),
        ("₹12.5 lakh", None, 1_250_000, "INR"),
        ("₹1,234 thousand", None, 1_234_000, "INR"),
        ("1266", "INR million", 1_266_000_000, "INR"),
        ("(₹1.5 crore)", None, -15_000_000, "INR"),
        ("₹-1,23,456.50", None, -123_456.5, "INR"),
        ("$2.5 billion", None, 2_500_000_000, "USD"),
        ("INR 2 crores", None, 20_000_000, "INR"),
        ("₹127Cr", None, 1_270_000_000, "INR"),
        ("Rs. 127 Cr", None, 1_270_000_000, "INR"),
        ("₹8,142 Cr", None, 81_420_000_000, "INR"),
        ("$2.5Bn", None, 2_500_000_000, "USD"),
    ],
)
def test_currency_normalization(raw, raw_unit, expected, unit):
    result = normalize_value(raw, "CURRENCY", raw_unit)
    assert result.value == expected
    assert result.unit == unit


def test_currency_requires_supported_explicit_currency():
    missing = normalize_value("1.2 million", "CURRENCY", None)
    unsupported = normalize_value("€1.2 million", "CURRENCY", None)
    mixed = normalize_value("₹1 million USD", "CURRENCY", None)
    assert missing.value is None and missing.warnings
    assert unsupported.value is None and unsupported.warnings
    assert mixed.value is None and mixed.warnings


def test_number_with_currency_unit_is_normalized_as_currency():
    result = normalize_value("1,266", "NUMBER", "₹ million")

    assert result.value == 1_266_000_000
    assert result.unit == "INR"
    assert "currency_to_base_unit" in result.rules


@pytest.mark.parametrize(
    ("raw", "raw_unit", "expected"),
    [
        ("6.5%", None, 6.5),
        ("6.5 percent", None, 6.5),
        ("6.50 per cent", None, 6.5),
        ("-2.25%", None, -2.25),
        ("(6.5%)", None, -6.5),
        ("6.5", "percent", 6.5),
    ],
)
def test_percentages_use_percentage_points(raw, raw_unit, expected):
    result = normalize_value(raw, "PERCENTAGE", raw_unit)
    assert result.value == expected and result.unit == "PERCENT"


@pytest.mark.parametrize(
    ("raw", "raw_unit", "kind", "expected", "unit"),
    [
        ("1,234", None, "NUMBER", 1234, "COUNT"),
        ("1.2 million", None, "NUMBER", 1_200_000, "COUNT"),
        ("12.5", "lakh", "NUMBER", 1_250_000, "COUNT"),
        ("7.5 thousand", "kg", "QUANTITY", 7500, "KG"),
    ],
)
def test_numbers_and_quantities(raw, raw_unit, kind, expected, unit):
    result = normalize_value(raw, kind, raw_unit)
    assert (result.value, result.unit) == (expected, unit)


def test_ambiguous_numbers_remain_unnormalized():
    for raw in ("about 12", "10-12", "1,2,3"):
        result = normalize_value(raw, "NUMBER", None)
        assert result.value is None and result.warnings
    quantity = normalize_value("7", "QUANTITY", None)
    assert quantity.value is None and quantity.warnings == ["quantity unit is missing"]


def test_fiscal_year_and_quarter_rules_require_india_context():
    fy24 = normalize_temporal("FY24", india_fy_context=True)
    assert (fy24.period_start, fy24.period_end) == (date(2023, 4, 1), date(2024, 3, 31))
    ranged = normalize_temporal("FY 2023-24", india_fy_context=True)
    assert (ranged.period_start, ranged.period_end) == (date(2023, 4, 1), date(2024, 3, 31))
    full = normalize_temporal("FY2024", india_fy_context=True)
    assert (full.period_start, full.period_end) == (date(2023, 4, 1), date(2024, 3, 31))
    quarter = normalize_temporal("Q4 FY24", india_fy_context=True)
    assert (quarter.period_start, quarter.period_end) == (date(2024, 1, 1), date(2024, 3, 31))
    ambiguous = normalize_temporal("FY24", india_fy_context=False)
    assert ambiguous.period_start is None and ambiguous.warnings


def test_year_ended_and_as_of_dates():
    ended = normalize_temporal("year ended March 31, 2024", india_fy_context=False)
    assert (ended.period_start, ended.period_end) == (date(2023, 4, 1), date(2024, 3, 31))
    as_of = normalize_temporal("as of March 31, 2024", india_fy_context=False)
    assert as_of.as_of_date == date(2024, 3, 31)
    invalid = normalize_temporal("as of someday", india_fy_context=False)
    assert invalid.as_of_date is None
    leap = normalize_temporal("year ended February 29, 2024", india_fy_context=False)
    assert (leap.period_start, leap.period_end) == (date(2023, 3, 1), date(2024, 2, 29))


def test_temporal_qualifier_key_value_forms():
    year_ended = Fact(
        document_id=PydanticObjectId(),
        evidence_chunk_ids=[PydanticObjectId()],
        subject="Example",
        predicate="revenue",
        raw_value="1",
        value_type="NUMBER",
        qualifiers={"year_ended": "March 31, 2024"},
    )
    result = normalize_fact_fields(year_ended)
    assert (result["period_start"], result["period_end"]) == (
        date(2023, 4, 1),
        date(2024, 3, 31),
    )
    as_of = year_ended.model_copy(update={"qualifiers": {"as_of": "March 31, 2024"}})
    assert normalize_fact_fields(as_of)["as_of_date"] == date(2024, 3, 31)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Delhivery Limited ", "delhivery"),
        ("DELHIVERY Ltd.", "delhivery"),
        ("Delhivery, Ltd. Limited", "delhivery"),
        ("Acme, Inc.", "acme"),
    ],
)
def test_entity_formatting(raw, expected):
    assert normalize_entity(raw).value == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("FY24 revenue from services", "revenue from services"),
        ("Revenue from services in FY24", "revenue from services"),
        ("EBITDA (₹ million)", "ebitda"),
    ],
)
def test_entity_formatting_removes_context_and_unit_labels(raw, expected):
    assert normalize_entity(raw).value == expected


def test_subject_and_predicate_supply_temporal_context():
    fact = Fact(
        document_id=PydanticObjectId(),
        evidence_chunk_ids=[PydanticObjectId()],
        subject="FY24 revenue from services",
        predicate="revenue",
        raw_value="₹8,142 Cr",
        value_type="CURRENCY",
    )

    result = normalize_fact_fields(fact)

    assert (result["period_start"], result["period_end"]) == (
        date(2023, 4, 1),
        date(2024, 3, 31),
    )


def test_rs_currency_supplies_india_fiscal_year_context():
    fact = Fact(
        document_id=PydanticObjectId(),
        evidence_chunk_ids=[PydanticObjectId()],
        subject="FY24 EBITDA",
        predicate="value",
        raw_value="Rs. 127 Cr",
        value_type="CURRENCY",
    )

    result = normalize_fact_fields(fact)

    assert (result["period_start"], result["period_end"]) == (
        date(2023, 4, 1),
        date(2024, 3, 31),
    )


def test_context_dependent_entity_alias_is_not_guessed():
    result = normalize_entity("the Company")
    assert result.value is None and result.warnings


def test_entity_and_date_fact_values_are_canonicalized():
    entity = Fact(
        document_id=PydanticObjectId(),
        evidence_chunk_ids=[PydanticObjectId()],
        subject="Example",
        predicate="legal name",
        raw_value="Acme Limited",
        value_type="ENTITY",
    )
    normalized_entity = normalize_fact_fields(entity)
    assert (normalized_entity["normalized_value"], normalized_entity["normalized_unit"]) == (
        "acme",
        "ENTITY",
    )
    dated = Fact(
        document_id=PydanticObjectId(),
        evidence_chunk_ids=[PydanticObjectId()],
        subject="Example",
        predicate="report date",
        raw_value="March 31, 2024",
        value_type="DATE",
    )
    normalized_date = normalize_fact_fields(dated)
    assert (normalized_date["normalized_value"], normalized_date["normalized_unit"]) == (
        "2024-03-31",
        "DATE",
    )


def test_partial_explicit_period_is_not_combined_with_inferred_period():
    fact = Fact(
        document_id=PydanticObjectId(),
        evidence_chunk_ids=[PydanticObjectId()],
        subject="Example",
        predicate="revenue",
        raw_value="₹1 crore",
        raw_unit="INR",
        value_type="CURRENCY",
        geography="India",
        qualifiers={"period": "FY24"},
        period_start=date(2024, 1, 1),
    )
    result = normalize_fact_fields(fact)
    assert result["period_start"] == date(2024, 1, 1)
    assert result["period_end"] is None


@pytest.mark.parametrize(
    "raw",
    ["Revenue from Services", "revenue_from_services", "revenue from services"],
)
def test_predicate_formatting(raw):
    assert normalize_predicate(raw) == "revenue_from_services"


async def make_fact(**kwargs):
    document = await Document(
        filename=f"{PydanticObjectId()}.pdf",
        original_filename="report.pdf",
        content_hash=str(PydanticObjectId()),
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
    ).insert()
    chunk = await EvidenceChunk(
        document_id=document.id,
        page_number=1,
        block_index=0,
        text="Supported evidence",
    ).insert()
    values = {
        "subject": "Delhivery Limited",
        "predicate": "Revenue from Services",
        "raw_value": "₹126.6 crore",
        "value_type": "CURRENCY",
        "geography": "India",
        "qualifiers": {"period": "FY24"},
        "metadata": {"provider": "test"},
    }
    values.update(kwargs)
    fact = await Fact(
        document_id=document.id,
        evidence_chunk_ids=[chunk.id],
        **values,
    ).insert()
    return document, fact


async def test_service_is_idempotent_and_preserves_metadata():
    document, fact = await make_fact()
    first = await normalize_document_facts(document.id)
    assert (first.facts_total, first.facts_changed, first.values_normalized) == (1, 1, 1)
    normalized = await Fact.get(fact.id)
    assert normalized.normalized_subject == "delhivery"
    assert normalized.normalized_predicate == "revenue_from_services"
    assert normalized.normalized_value == 1_266_000_000
    assert normalized.normalized_unit == "INR"
    assert (normalized.period_start, normalized.period_end) == (
        date(2023, 4, 1),
        date(2024, 3, 31),
    )
    assert normalized.metadata["provider"] == "test"
    previous_updated_at = normalized.updated_at
    second = await normalize_document_facts(document.id)
    assert second.facts_changed == 0
    assert (await Fact.get(fact.id)).updated_at == previous_updated_at


async def test_unsupported_fact_stays_safely_unnormalized():
    _, fact = await make_fact(
        subject="the Company",
        raw_value="about €1.2 million",
        geography=None,
        qualifiers={"period": "FY24"},
    )
    result = normalize_fact_fields(fact)
    assert result["normalized_value"] is None
    assert result["normalized_subject"] is None
    assert result["period_start"] is None
    assert len(result["normalization"]["warnings"]) >= 3


async def test_normalization_apis_and_explainability(client):
    document, fact = await make_fact()
    response = await client.post(f"/api/documents/{document.id}/normalize-facts")
    assert response.status_code == 200
    assert response.json()["facts_changed"] == 1
    detail = await client.get(f"/api/facts/{fact.id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["normalized_value"] == 1_266_000_000
    assert payload["metadata"]["normalization"]["rules_applied"]
    single = await client.post(f"/api/facts/{fact.id}/normalize")
    assert single.status_code == 200 and single.json()["normalized_unit"] == "INR"
    assert (await client.post(f"/api/facts/{PydanticObjectId()}/normalize")).status_code == 404
    assert (
        await client.post(f"/api/documents/{PydanticObjectId()}/normalize-facts")
    ).status_code == 404
