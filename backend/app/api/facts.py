from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Query

from app.core.exceptions import AppError
from app.models.fact import Fact
from app.normalization.service import normalize_fact_by_id
from app.schemas.facts import FactPageResponse, FactResponse, ValueType
from app.services.facts import serialize_facts

router = APIRouter(prefix="/facts", tags=["facts"])


@router.post("/{fact_id}/normalize", response_model=FactResponse)
async def normalize_fact(fact_id: PydanticObjectId) -> FactResponse:
    fact, _ = await normalize_fact_by_id(fact_id)
    return (await serialize_facts([fact]))[0]


@router.get("", response_model=FactPageResponse)
async def list_facts(
    document_id: PydanticObjectId | None = None,
    subject: Annotated[str | None, Query(max_length=512)] = None,
    predicate: Annotated[str | None, Query(max_length=512)] = None,
    value_type: ValueType | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> FactPageResponse:
    filters = {
        key: value
        for key, value in {
            "document_id": document_id,
            "subject": subject,
            "predicate": predicate,
            "value_type": value_type,
        }.items()
        if value is not None
    }
    query = Fact.find(filters)
    total = await query.count()
    facts = await query.sort("-created_at", "+_id").skip(offset).limit(limit).to_list()
    return FactPageResponse(
        items=await serialize_facts(facts), total=total, offset=offset, limit=limit
    )


@router.get("/{fact_id}", response_model=FactResponse)
async def get_fact(fact_id: PydanticObjectId) -> FactResponse:
    fact = await Fact.get(fact_id)
    if fact is None:
        raise AppError(status_code=404, code="fact_not_found", message="Fact not found")
    return (await serialize_facts([fact]))[0]
