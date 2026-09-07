# Architecture notes

Phase 1 extends the established boundaries with an in-memory PDF ingestion service and a separate PyMuPDF layout parser. The HTTP layer validates multipart input and returns typed schemas; it does not expose Beanie documents directly.

The MongoDB collections are `documents`, `evidence_chunks`, `facts`, and `fact_relations`. Cross-collection provenance is represented with `PydanticObjectId` identifiers so evidence and documents stay independently addressable. Compound and single-field indexes cover the expected document, page, subject, predicate, relationship, and deduplication queries.

The `/health` endpoint reports that the API process is responding. The `/ready` endpoint separately pings MongoDB and returns a structured 503 error when the dependency is unavailable.

PDF bytes are size-limited while reading, hashed with SHA-256, and discarded after parsing. Evidence chunks preserve `document_id`, a 1-indexed page number, stable useful-block order, bounding box, source order, extraction method, and page dimensions. The unique document content-hash index provides the final race-safe deduplication guard.
