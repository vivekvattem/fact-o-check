from datetime import date

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.document import Document, DocumentStatus
from app.models.fact import Fact
from app.models.fact_relation import FactRelation, FactRelationType


def test_document_status_enum_validation() -> None:
    document = Document(
        filename="report.pdf",
        original_filename="report.pdf",
        content_hash="abc123",
        mime_type="application/pdf",
        status="PROCESSING",
    )

    assert document.status is DocumentStatus.PROCESSING

    with pytest.raises(ValidationError):
        Document(
            filename="report.pdf",
            original_filename="report.pdf",
            content_hash="abc123",
            mime_type="application/pdf",
            status="UNKNOWN",
        )


def test_fact_supports_heterogeneous_values_and_qualifiers() -> None:
    fact = Fact(
        document_id=PydanticObjectId(),
        subject="Example Co",
        predicate="revenue",
        raw_value="$1.2B",
        normalized_value=1_200_000_000,
        qualifiers={"basis": "reported", "segments": ["domestic", "international"]},
    )

    assert fact.normalized_value == 1_200_000_000
    assert fact.qualifiers["segments"] == ["domestic", "international"]


def test_fact_rejects_inverted_period() -> None:
    with pytest.raises(ValidationError, match="period_end"):
        Fact(
            document_id=PydanticObjectId(),
            subject="Example Co",
            predicate="revenue",
            period_start=date(2025, 12, 31),
            period_end=date(2025, 1, 1),
        )


def test_fact_relation_enum_and_validation() -> None:
    first_id = PydanticObjectId()
    second_id = PydanticObjectId()
    relation = FactRelation(
        fact_a_id=first_id,
        fact_b_id=second_id,
        relation_type="CORROBORATES",
        confidence=0.9,
    )

    assert relation.relation_type is FactRelationType.CORROBORATES
    assert str(relation.fact_a_id) < str(relation.fact_b_id)

    reversed_relation = FactRelation(
        fact_a_id=second_id,
        fact_b_id=first_id,
        relation_type="CORROBORATES",
    )
    assert reversed_relation.fact_a_id == relation.fact_a_id
    assert reversed_relation.fact_b_id == relation.fact_b_id

    with pytest.raises(ValidationError, match="itself"):
        FactRelation(
            fact_a_id=first_id,
            fact_b_id=first_id,
            relation_type=FactRelationType.UNRELATED,
        )
