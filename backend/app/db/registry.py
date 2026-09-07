from beanie import Document as BeanieDocument

from app.models.document import Document
from app.models.evidence_chunk import EvidenceChunk
from app.models.fact import Fact
from app.models.fact_relation import FactRelation

DOCUMENT_MODELS: list[type[BeanieDocument]] = [
    Document,
    EvidenceChunk,
    Fact,
    FactRelation,
]

