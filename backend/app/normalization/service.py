import re
from typing import Any

from beanie import PydanticObjectId

from app.core.exceptions import AppError
from app.models.common import utc_now
from app.models.fact import Fact
from app.normalization.dates import normalize_temporal, parse_date_literal
from app.normalization.entities import normalize_entity
from app.normalization.predicates import normalize_predicate
from app.normalization.units import normalize_value
from app.schemas.facts import NormalizationSummary
from app.services.documents import get_document_or_404
from app.services.facts import document_fact_lease


def _context_text(fact: Fact) -> str:
    values = [fact.subject, fact.predicate, fact.scope, fact.geography]
    values.extend(
        f"{key.replace('_', ' ')}: {value}"
        for key, value in fact.qualifiers.items()
        if isinstance(value, (str, int))
    )
    if fact.value_type == "DATE" and fact.raw_value is not None:
        values.append(str(fact.raw_value))
    return " | ".join(value for value in values if value)


def _has_india_context(fact: Fact) -> bool:
    context = _context_text(fact).casefold()
    currency = f"{fact.raw_value or ''} {fact.raw_unit or ''}".casefold()
    return (
        "india" in context
        or "₹" in currency
        or "inr" in currency
        or bool(re.search(r"\brs\.?\b", currency))
    )


def normalize_fact_fields(fact: Fact) -> dict[str, Any]:
    entity = normalize_entity(fact.subject)
    predicate = normalize_predicate(fact.predicate)
    value = normalize_value(fact.raw_value, fact.value_type, fact.raw_unit)
    context = _context_text(fact)
    temporal = normalize_temporal(context, india_fy_context=_has_india_context(fact))

    if fact.value_type == "ENTITY" and isinstance(fact.raw_value, str):
        normalized_entity = normalize_entity(fact.raw_value)
        value.value = normalized_entity.value
        value.unit = "ENTITY" if normalized_entity.value else None
        value.rules = normalized_entity.rules
        value.warnings = normalized_entity.warnings
    elif fact.value_type == "DATE" and isinstance(fact.raw_value, str):
        parsed_date = parse_date_literal(fact.raw_value)
        if parsed_date:
            value.value = parsed_date.isoformat()
            value.unit = "DATE"
            value.rules = ["date_literal"]
            value.warnings = []

    rules = [*entity.rules, *(["predicate_snake_case"] if predicate else []), *value.rules]
    rules.extend(temporal.rules)
    warnings = [*entity.warnings, *value.warnings, *temporal.warnings]
    period_start = fact.period_start
    period_end = fact.period_end
    if period_start is None and period_end is None:
        period_start = temporal.period_start
        period_end = temporal.period_end
    return {
        "normalized_subject": entity.value,
        "normalized_predicate": predicate,
        "normalized_value": value.value,
        "normalized_unit": value.unit,
        "period_start": period_start,
        "period_end": period_end,
        "as_of_date": fact.as_of_date or temporal.as_of_date,
        "normalization": {
            "version": "phase3-v1",
            "rules_applied": list(dict.fromkeys(rules)),
            "warnings": list(dict.fromkeys(warnings)),
        },
    }


async def normalize_fact(fact: Fact) -> tuple[bool, bool, bool, bool]:
    result = normalize_fact_fields(fact)
    metadata = {**fact.metadata, "normalization": result.pop("normalization")}
    changes = {**result, "metadata": metadata}
    changed = any(getattr(fact, key) != value for key, value in changes.items())
    if changed:
        for key, value in changes.items():
            setattr(fact, key, value)
        fact.updated_at = utc_now()
        await fact.save()
    return (
        changed,
        result["normalized_value"] is not None,
        bool(result["period_start"] or result["period_end"] or result["as_of_date"]),
        bool(metadata["normalization"]["warnings"]),
    )


async def normalize_document_facts(document_id: PydanticObjectId) -> NormalizationSummary:
    await get_document_or_404(document_id)
    async with document_fact_lease(document_id):
        facts = await Fact.find(Fact.document_id == document_id).to_list()
        summary = NormalizationSummary(document_id=document_id, facts_total=len(facts))
        for fact in facts:
            changed, value, temporal, warnings = await normalize_fact(fact)
            summary.facts_changed += changed
            summary.values_normalized += value
            summary.temporal_contexts_normalized += temporal
            summary.facts_with_warnings += warnings
        return summary


async def normalize_fact_by_id(fact_id: PydanticObjectId) -> tuple[Fact, bool]:
    fact = await Fact.get(fact_id)
    if fact is None:
        raise AppError(status_code=404, code="fact_not_found", message="Fact not found")
    async with document_fact_lease(fact.document_id):
        changed, *_ = await normalize_fact(fact)
    return fact, changed
