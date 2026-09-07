import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.evidence_chunk import EvidenceChunk
from app.models.fact import Fact
from app.models.fact_relation import FactRelation, FactRelationType
from app.normalization.entities import normalize_entity
from app.schemas.relations import (
    RelationComparisonSummary,
    RelationPageResponse,
    RelationResponse,
)
from app.services.documents import get_document_or_404
from app.services.fact_extractor import ExtractorError
from app.services.facts import serialize_facts
from app.services.relation_reasoner import FactRelationReasoner, get_relation_reasoner

NUMERIC_TYPES = {"CURRENCY", "PERCENTAGE", "NUMBER", "QUANTITY"}
APPROXIMATION_PATTERN = re.compile(
    r"(?:\b(?:about|approx(?:imately)?|around|nearly|rounded)\b|[~≈])",
    re.IGNORECASE,
)
CLEAR_STRING_OPPOSITES = {
    frozenset(pair)
    for pair in (
        ("active", "inactive"),
        ("approved", "rejected"),
        ("open", "closed"),
        ("present", "absent"),
        ("yes", "no"),
    )
}


@dataclass(frozen=True)
class Decision:
    relation_type: FactRelationType
    confidence: float
    explanation: str
    reasoning_details: dict[str, Any]


def _canonical(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _temporal_value(fact: Fact) -> tuple[Any, Any, Any]:
    return fact.period_start, fact.period_end, fact.as_of_date


def _dimension(left: str | None, right: str | None) -> str:
    if not left and not right:
        return "unspecified"
    if not left or not right:
        return "one_missing"
    return "same" if _canonical(left) == _canonical(right) else "different"


def _status_indicator(fact: Fact) -> str | None:
    text = " ".join(
        [
            str(key) for key in fact.qualifiers
        ]
        + [str(value) for value in fact.qualifiers.values()]
        + [fact.scope or ""]
    ).casefold()
    if re.search(r"\b(?:forecast|projected|projection|expected|guidance)\b", text):
        return "forecast"
    if re.search(r"\b(?:estimate|estimated|preliminary)\b", text):
        return "estimate"
    if re.search(r"\b(?:actual|reported|observed|audited)\b", text):
        return "actual"
    return None


def compare_context(fact_a: Fact, fact_b: Fact) -> dict[str, Any]:
    temporal_a = _temporal_value(fact_a)
    temporal_b = _temporal_value(fact_b)
    if temporal_a == temporal_b and any(temporal_a):
        temporal = "same_period" if fact_a.period_start or fact_a.period_end else "same_as_of_date"
    elif any(temporal_a) and any(temporal_b):
        temporal = "different_period"
    elif any(temporal_a) or any(temporal_b):
        temporal = "one_missing"
    else:
        temporal = "unspecified"

    geography = _dimension(fact_a.geography, fact_b.geography)
    scope = _dimension(fact_a.scope, fact_b.scope)
    status_a, status_b = _status_indicator(fact_a), _status_indicator(fact_b)
    if status_a and status_b:
        qualifiers = "same_status" if status_a == status_b else f"{status_a}_vs_{status_b}"
    elif status_a or status_b:
        qualifiers = "one_status_missing"
    elif fact_a.qualifiers or fact_b.qualifiers:
        qualifiers = (
            "same" if fact_a.qualifiers == fact_b.qualifiers else "ambiguous"
        )
    else:
        qualifiers = "unspecified"

    differences = []
    if temporal == "different_period":
        differences.append("temporal")
    if geography == "different":
        differences.append("geography")
    if scope == "different":
        differences.append("scope")
    if "_vs_" in qualifiers:
        differences.append("qualifiers")
    missing = []
    if temporal == "one_missing":
        missing.append("temporal")
    if geography == "one_missing":
        missing.append("geography")
    if scope == "one_missing":
        missing.append("scope")
    if qualifiers == "one_status_missing":
        missing.append("qualifiers")
    status = (
        "context_difference"
        if differences
        else "ambiguous_context"
        if qualifiers == "ambiguous"
        else "insufficient_context"
        if missing
        else "comparable"
    )
    return {
        "temporal": temporal,
        "scope": scope,
        "geography": geography,
        "qualifiers": qualifiers,
        "status": status,
        "differences": differences,
        "missing_dimensions": missing,
    }


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _has_rounding_indicator(fact: Fact) -> bool:
    text = " ".join(
        [str(fact.raw_value), fact.raw_unit or ""]
        + [str(key) for key in fact.qualifiers]
        + [str(value) for value in fact.qualifiers.values()]
    )
    return bool(APPROXIMATION_PATTERN.search(text))


def compare_values(fact_a: Fact, fact_b: Fact) -> dict[str, Any]:
    kind = (fact_a.value_type or "").upper()
    rounding = _has_rounding_indicator(fact_a) or _has_rounding_indicator(fact_b)
    details: dict[str, Any] = {
        "result": "ambiguous",
        "value_type": kind or None,
        "unit_equivalence": fact_a.normalized_unit == fact_b.normalized_unit,
        "tolerance_used": None,
        "absolute_difference": None,
        "relative_difference": None,
        "rounding_indicators_present": rounding,
        "exact": False,
    }

    if kind in {"STRING", "ENTITY"}:
        left = fact_a.normalized_value if fact_a.normalized_value is not None else fact_a.raw_value
        right = fact_b.normalized_value if fact_b.normalized_value is not None else fact_b.raw_value
        if not _canonical(left) or not _canonical(right):
            return details
        canonical_pair = frozenset((_canonical(left), _canonical(right)))
        details["exact"] = len(canonical_pair) == 1
        details["result"] = (
            "equivalent"
            if details["exact"]
            else "different"
            if kind == "STRING" and canonical_pair in CLEAR_STRING_OPPOSITES
            else "ambiguous"
        )
        details["tolerance_used"] = (
            "exact canonical opposite" if details["result"] == "different"
            else "canonical string equality"
        )
        return details

    if kind == "BOOLEAN":
        left = fact_a.normalized_value
        right = fact_b.normalized_value
        if not isinstance(left, bool) or not isinstance(right, bool):
            return details
        details["exact"] = left is right
        details["result"] = "equivalent" if left is right else "different"
        details["tolerance_used"] = "exact boolean equality"
        return details

    if kind == "DATE":
        left = fact_a.normalized_value
        right = fact_b.normalized_value
        if left is None or right is None:
            return details
        details["exact"] = left == right
        details["result"] = "equivalent" if left == right else "different"
        details["tolerance_used"] = "exact calendar date"
        return details

    if kind not in NUMERIC_TYPES:
        return details
    left, right = _decimal(fact_a.normalized_value), _decimal(fact_b.normalized_value)
    if left is None or right is None or not details["unit_equivalence"]:
        return details
    difference = abs(left - right)
    denominator = max(abs(left), abs(right))
    relative = difference / denominator if denominator else Decimal(0)
    details["absolute_difference"] = float(difference)
    details["relative_difference"] = float(relative)
    details["exact"] = difference == 0

    if kind == "CURRENCY":
        relative_tolerance = Decimal("0.005") if rounding else Decimal("0.001")
        equivalent = difference == 0 or relative <= relative_tolerance
        details["tolerance_used"] = f"currency relative <= {float(relative_tolerance):g}"
    elif kind == "PERCENTAGE":
        absolute_tolerance = Decimal("0.1")
        equivalent = difference <= absolute_tolerance
        details["tolerance_used"] = "percentage points <= 0.1"
    elif kind == "NUMBER":
        relative_tolerance = Decimal("0.01") if rounding else Decimal(0)
        equivalent = difference == 0 or (rounding and relative <= relative_tolerance)
        details["tolerance_used"] = (
            "count relative <= 0.01 with approximation marker" if rounding else "exact count"
        )
    else:
        relative_tolerance = Decimal("0.001")
        equivalent = difference == 0 or relative <= relative_tolerance
        details["tolerance_used"] = "same-unit quantity relative <= 0.001"
    details["result"] = "equivalent" if equivalent else "different"
    return details


def _compatible_types(fact_a: Fact, fact_b: Fact) -> bool:
    left, right = (fact_a.value_type or "").upper(), (fact_b.value_type or "").upper()
    return left == right or (
        {left, right} == {"NUMBER", "QUANTITY"}
        and fact_a.normalized_unit is not None
        and fact_a.normalized_unit == fact_b.normalized_unit
    )


def _scaled_representation(fact_a: Fact, fact_b: Fact) -> bool:
    if _canonical(fact_a.raw_value) == _canonical(fact_b.raw_value) and _canonical(
        fact_a.raw_unit
    ) == _canonical(fact_b.raw_unit):
        return False
    scale_sets = []
    for fact in (fact_a, fact_b):
        normalization = fact.metadata.get("normalization", {})
        rules = normalization.get("rules_applied", [])
        scale_sets.append(
            {
                token
                for rule in rules
                for token in ("thousand", "lakh", "lac", "million", "crore", "billion")
                if token in rule
            }
        )
    return scale_sets[0] != scale_sets[1] and bool(scale_sets[0] | scale_sets[1])


def deterministic_assessment(fact_a: Fact, fact_b: Fact) -> Decision | None:
    context = compare_context(fact_a, fact_b)
    base_details: dict[str, Any] = {
        "deterministic": True,
        "value_comparison": None,
        "temporal_compatibility": context["temporal"],
        "scope_compatibility": context["scope"],
        "geography_compatibility": context["geography"],
        "qualifier_compatibility": context["qualifiers"],
        "context": context,
        "unit_equivalence": None,
        "tolerance_used": None,
        "semantic_fallback_used": False,
        "warnings": [],
    }

    if fact_a.document_id == fact_b.document_id or fact_a.id == fact_b.id:
        return Decision(
            FactRelationType.UNRELATED,
            1.0,
            "Facts from the same source are excluded from cross-document comparison.",
            base_details,
        )
    if not fact_a.normalized_subject or not fact_b.normalized_subject:
        base_details["warnings"] = ["normalized subject is missing"]
        return Decision(
            FactRelationType.NEEDS_REVIEW,
            0.4,
            "The facts cannot be compared safely because subject normalization is incomplete.",
            base_details,
        )
    if fact_a.normalized_subject != fact_b.normalized_subject:
        return Decision(
            FactRelationType.UNRELATED,
            0.99,
            "The facts refer to different canonical subjects.",
            base_details,
        )
    if not _compatible_types(fact_a, fact_b):
        return Decision(
            FactRelationType.UNRELATED,
            0.98,
            "The facts use incompatible value types or canonical units.",
            base_details,
        )
    if not fact_a.normalized_predicate or not fact_b.normalized_predicate:
        base_details["warnings"] = ["normalized predicate is missing"]
        return Decision(
            FactRelationType.NEEDS_REVIEW,
            0.4,
            "The facts cannot be compared safely because predicate normalization is incomplete.",
            base_details,
        )
    if fact_a.normalized_predicate != fact_b.normalized_predicate:
        left = set(fact_a.normalized_predicate.split("_"))
        right = set(fact_b.normalized_predicate.split("_"))
        if not left & right:
            return Decision(
                FactRelationType.UNRELATED,
                0.95,
                "The normalized predicates describe different claims.",
                base_details,
            )
        return None

    value = compare_values(fact_a, fact_b)
    base_details["value_comparison"] = value
    base_details["unit_equivalence"] = value["unit_equivalence"]
    base_details["tolerance_used"] = value["tolerance_used"]
    result = value["result"]
    if context["status"] == "ambiguous_context":
        return None
    if result == "ambiguous":
        if (fact_a.value_type or "").upper() in {"STRING", "ENTITY"}:
            return None
        base_details["warnings"] = ["normalized values or compatible units are missing"]
        return Decision(
            FactRelationType.NEEDS_REVIEW,
            0.4,
            "Normalized values are insufficient for a safe deterministic comparison.",
            base_details,
        )
    if result == "equivalent":
        if context["status"] == "context_difference":
            return Decision(
                FactRelationType.UNRELATED,
                0.85,
                "The values align, but explicit context shows they are not the same claim.",
                base_details,
            )
        if context["status"] == "insufficient_context":
            base_details["warnings"] = ["one fact is missing comparable context"]
            return Decision(
                FactRelationType.NEEDS_REVIEW,
                0.5,
                "Equivalent values cannot be linked confidently because context is incomplete.",
                base_details,
            )
        if value["exact"] and _scaled_representation(fact_a, fact_b):
            return Decision(
                FactRelationType.RECONCILABLE,
                0.97,
                "Different displayed units resolve to the same canonical value.",
                base_details,
            )
        if value["rounding_indicators_present"] and not value["exact"]:
            return Decision(
                FactRelationType.RECONCILABLE,
                0.9,
                "The small value difference is explained by an explicit rounding indicator.",
                base_details,
            )
        return Decision(
            FactRelationType.CORROBORATES,
            0.99 if value["exact"] else 0.92,
            "The canonical values agree within the applicable typed tolerance.",
            base_details,
        )
    if context["status"] == "context_difference":
        dimensions = ", ".join(context["differences"])
        return Decision(
            FactRelationType.RECONCILABLE,
            0.88,
            f"The apparent value conflict is explained by explicit {dimensions} context.",
            base_details,
        )
    if context["status"] == "insufficient_context":
        base_details["warnings"] = ["one fact is missing comparable context"]
        return Decision(
            FactRelationType.NEEDS_REVIEW,
            0.45,
            "The values differ, but incomplete context prevents a justified contradiction.",
            base_details,
        )
    return Decision(
        FactRelationType.CONTRADICTS,
        0.95,
        "The facts describe the same contextual claim but have materially different values.",
        base_details,
    )


async def _semantic_payload(fact: Fact) -> dict[str, Any]:
    chunks = await EvidenceChunk.find({"_id": {"$in": fact.evidence_chunk_ids}}).to_list()
    evidence = [
        {"page": chunk.page_number, "text": chunk.text}
        for chunk in sorted(chunks, key=lambda item: (item.page_number, item.block_index))
        if chunk.document_id == fact.document_id
    ]
    return {
        "subject": fact.subject,
        "predicate": fact.predicate,
        "raw_value": fact.raw_value,
        "normalized_subject": fact.normalized_subject,
        "normalized_predicate": fact.normalized_predicate,
        "normalized_value": fact.normalized_value,
        "value_type": fact.value_type,
        "raw_unit": fact.raw_unit,
        "normalized_unit": fact.normalized_unit,
        "period_start": fact.period_start,
        "period_end": fact.period_end,
        "as_of_date": fact.as_of_date,
        "geography": fact.geography,
        "scope": fact.scope,
        "qualifiers": fact.qualifiers,
        "evidence": evidence,
    }


async def classify_pair(
    fact_a: Fact,
    fact_b: Fact,
    *,
    reasoner: FactRelationReasoner | None = None,
) -> Decision:
    deterministic = deterministic_assessment(fact_a, fact_b)
    if deterministic is not None:
        return deterministic
    checks = {
        "context": compare_context(fact_a, fact_b),
        "value_comparison": compare_values(fact_a, fact_b),
        "predicate_comparison": "semantically_ambiguous",
    }
    if reasoner is None:
        return Decision(
            FactRelationType.NEEDS_REVIEW,
            0.35,
            "Semantic comparability is ambiguous and no configured fallback was available.",
            {
                "deterministic": False,
                **checks,
                "semantic_fallback_used": False,
                "warnings": ["semantic fallback unavailable"],
            },
        )
    try:
        result = await reasoner.compare(
            await _semantic_payload(fact_a),
            await _semantic_payload(fact_b),
            checks,
        )
    except (ExtractorError, AppError):
        return Decision(
            FactRelationType.NEEDS_REVIEW,
            0.3,
            "Semantic fallback failed, so the relationship requires review.",
            {
                "deterministic": False,
                **checks,
                "semantic_fallback_used": True,
                "warnings": ["semantic fallback failed"],
            },
        )
    return Decision(
        result.relation_type,
        result.confidence,
        result.explanation,
        {
            "deterministic": False,
            **checks,
            "semantic_fallback_used": True,
            "context_dimensions": result.context_dimensions,
            "needs_review_reason": result.needs_review_reason,
            "warnings": [],
        },
    )


def _candidate_filter(fact: Fact) -> dict[str, Any] | None:
    subject_filter: dict[str, Any]
    if fact.normalized_subject:
        subject_filter = {"normalized_subject": fact.normalized_subject}
    elif fact.subject:
        subject_filter = {"subject": fact.subject}
    else:
        return None
    compatible_types = [fact.value_type]
    if fact.value_type == "NUMBER":
        compatible_types.append("QUANTITY")
    elif fact.value_type == "QUANTITY":
        compatible_types.append("NUMBER")
    return {
        **subject_filter,
        "document_id": {"$ne": fact.document_id},
        "value_type": {"$in": compatible_types},
    }


async def generate_candidates(document_id: PydanticObjectId) -> list[tuple[Fact, Fact]]:
    source_facts = await Fact.find(Fact.document_id == document_id).to_list()
    pairs: dict[tuple[str, str], tuple[Fact, Fact]] = {}
    for fact in source_facts:
        candidate_filter = _candidate_filter(fact)
        if candidate_filter is None:
            continue
        for candidate in await Fact.find(candidate_filter).to_list():
            first, second = sorted((fact, candidate), key=lambda item: str(item.id))
            pairs[(str(first.id), str(second.id))] = (first, second)
    return list(pairs.values())


async def compare_document_facts(
    document_id: PydanticObjectId,
    settings: Settings,
    *,
    reasoner: FactRelationReasoner | None = None,
) -> RelationComparisonSummary:
    await get_document_or_404(document_id)
    pairs = await generate_candidates(document_id)
    summary = RelationComparisonSummary(document_id=document_id, pairs_considered=len(pairs))
    reasoner_checked = reasoner is not None
    for fact_a, fact_b in pairs:
        existing = await FactRelation.find_one(
            FactRelation.fact_a_id == fact_a.id,
            FactRelation.fact_b_id == fact_b.id,
        )
        if existing is not None:
            summary.duplicates_skipped += 1
            continue
        assessment = deterministic_assessment(fact_a, fact_b)
        if assessment is None and not reasoner_checked:
            try:
                reasoner = get_relation_reasoner(settings)
            except AppError:
                reasoner = None
            reasoner_checked = True
        decision = assessment or await classify_pair(fact_a, fact_b, reasoner=reasoner)
        relation = FactRelation(
            fact_a_id=fact_a.id,
            fact_b_id=fact_b.id,
            relation_type=decision.relation_type,
            confidence=decision.confidence,
            explanation=decision.explanation,
            reasoning_details=decision.reasoning_details,
        )
        try:
            await relation.insert()
        except DuplicateKeyError:
            summary.duplicates_skipped += 1
            continue
        summary.relations_created += 1
        field = {
            FactRelationType.CORROBORATES: "corroborates",
            FactRelationType.CONTRADICTS: "contradicts",
            FactRelationType.RECONCILABLE: "reconcilable",
            FactRelationType.NEEDS_REVIEW: "needs_review",
            FactRelationType.UNRELATED: "unrelated",
        }[decision.relation_type]
        setattr(summary, field, getattr(summary, field) + 1)
    return summary


async def serialize_relations(relations: list[FactRelation]) -> list[RelationResponse]:
    if not relations:
        return []
    fact_ids = list(
        {fact_id for relation in relations for fact_id in (relation.fact_a_id, relation.fact_b_id)}
    )
    facts = await Fact.find({"_id": {"$in": fact_ids}}).to_list()
    serialized = await serialize_facts(facts)
    by_id = {item.id: item for item in serialized}
    responses = []
    for relation in relations:
        if relation.fact_a_id not in by_id or relation.fact_b_id not in by_id:
            continue
        responses.append(
            RelationResponse(
                **relation.model_dump(),
                fact_a=by_id[relation.fact_a_id],
                fact_b=by_id[relation.fact_b_id],
            )
        )
    return responses


async def list_relations(
    *,
    relation_type: FactRelationType | None,
    document_id: PydanticObjectId | None,
    subject: str | None,
    min_confidence: float | None,
    offset: int,
    limit: int,
) -> RelationPageResponse:
    filters: dict[str, Any] = {}
    if relation_type is not None:
        filters["relation_type"] = relation_type
    if min_confidence is not None:
        filters["confidence"] = {"$gte": min_confidence}
    fact_filter: dict[str, Any] = {}
    if document_id is not None:
        fact_filter["document_id"] = document_id
    if subject:
        normalized = normalize_entity(subject).value
        fact_filter["$or"] = [
            {"subject": subject},
            {"normalized_subject": normalized},
        ]
    if fact_filter:
        fact_ids = [fact.id for fact in await Fact.find(fact_filter).to_list()]
        filters["$or"] = [
            {"fact_a_id": {"$in": fact_ids}},
            {"fact_b_id": {"$in": fact_ids}},
        ]
    query = FactRelation.find(filters)
    total = await query.count()
    relations = await query.sort("-created_at", "+_id").skip(offset).limit(limit).to_list()
    return RelationPageResponse(
        items=await serialize_relations(relations),
        total=total,
        offset=offset,
        limit=limit,
    )


async def get_relation_or_404(relation_id: PydanticObjectId) -> RelationResponse:
    relation = await FactRelation.get(relation_id)
    if relation is None:
        raise AppError(status_code=404, code="relation_not_found", message="Relation not found")
    serialized = await serialize_relations([relation])
    if not serialized:
        raise AppError(status_code=404, code="relation_not_found", message="Relation not found")
    return serialized[0]
