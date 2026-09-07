# Architecture notes

Phase 0 establishes boundaries for the API, configuration, persistence models, domain services, and UI without implementing the document-processing pipeline.

The MongoDB collections are `documents`, `evidence_chunks`, `facts`, and `fact_relations`. Cross-collection provenance is represented with `PydanticObjectId` identifiers so evidence and documents stay independently addressable. Compound and single-field indexes cover the expected document, page, subject, predicate, relationship, and deduplication queries.

The `/health` endpoint reports that the API process is responding. The `/ready` endpoint separately pings MongoDB and returns a structured 503 error when the dependency is unavailable.

