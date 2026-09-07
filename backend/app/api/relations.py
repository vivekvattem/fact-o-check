from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Query

from app.models.fact_relation import FactRelationType
from app.schemas.relations import RelationPageResponse, RelationResponse
from app.services.relations import get_relation_or_404, list_relations

router = APIRouter(prefix="/relations", tags=["relations"])


@router.get("", response_model=RelationPageResponse)
async def get_relations(
    relation_type: FactRelationType | None = None,
    document_id: PydanticObjectId | None = None,
    subject: Annotated[str | None, Query(max_length=512)] = None,
    min_confidence: Annotated[float | None, Query(ge=0, le=1)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RelationPageResponse:
    return await list_relations(
        relation_type=relation_type,
        document_id=document_id,
        subject=subject,
        min_confidence=min_confidence,
        offset=offset,
        limit=limit,
    )


@router.get("/{relation_id}", response_model=RelationResponse)
async def get_relation(relation_id: PydanticObjectId) -> RelationResponse:
    return await get_relation_or_404(relation_id)
