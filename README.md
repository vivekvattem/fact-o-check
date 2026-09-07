# Fact-O-Check

## Overview

Fact-O-Check is an evidence-grounded fact knowledge layer for PDFs. It is designed to extract structured facts, preserve document and page provenance, link every fact to exact source evidence, and compare facts across documents with explainable relationship classifications.

> Facts, not text chunks, are the primary unit of knowledge.

This repository contains the Phase 1 application: PDFs can be uploaded, parsed into page-level evidence blocks, and inspected through the API and frontend. Fact extraction, normalization, and relationship reasoning are intentionally not implemented yet.

## Why this architecture

MongoDB was selected because facts have a stable core but heterogeneous contextual qualifiers. Flexible document schemas let the knowledge layer evolve as new fact types and domain-specific context appear without forcing every fact into one rigid shape.

Evidence is stored separately and referenced by identifier rather than duplicated inside facts. This keeps provenance explicit, avoids copies drifting out of sync, and allows multiple facts to point to the same source passage.

MongoDB is not being used as an excuse to skip validation: Beanie and Pydantic models enforce the stable structure, types, ranges, timestamps, enums, and identifiers at the application boundary.

## Architecture

```text
React
  ↓
FastAPI
  ↓
Beanie
  ↓
MongoDB
```

The backend uses a FastAPI lifespan to initialize and close a MongoDB/Beanie connection. Document models are registered in one place to prevent import cycles. The frontend is a strict TypeScript Vite application with React Router and a small typed API client.

PyMuPDF performs local layout-block extraction during ingestion. Future stages will add fact extraction, normalization, relationship reasoning, and retrieval; those stages are not implemented yet.

## Ingestion flow

1. `POST /api/documents` streams an uploaded file into bounded in-memory chunks and rejects empty, oversized, or non-PDF content.
2. The service computes a SHA-256 content hash and returns the existing document when that hash is already present.
3. A new `Document` moves through `UPLOADED` and `PROCESSING` states.
4. PyMuPDF parses the bytes page-by-page off the API event loop and extracts useful text blocks.
5. Evidence blocks are stored with the document identifier, 1-indexed page number, ordered block index, bounding box, source block number, and page dimensions.
6. The document becomes `PROCESSED` with its page count, or `FAILED` with a preserved error message when parsing fails.

Original PDF bytes are not persisted locally or in MongoDB. Phase 1 stores document metadata and extracted evidence only.

## Evidence and provenance

The provenance path is:

```text
Document → 1-indexed page → ordered EvidenceChunk
```

`EvidenceChunk` records reference a document by `PydanticObjectId`; they do not embed the full document. Each chunk retains a PyMuPDF bounding box and ordering metadata so later phases can cite a page, reconstruct approximate reading order, and investigate layout or table extraction failures. Deleting a document cascades to its evidence chunks.

Layout blocks are kept separate instead of merging a whole PDF into one text field. Whitespace is normalized within lines, line boundaries are preserved, non-text layout blocks are ignored, and isolated one-token fragments are filtered out. Blank pages are valid and simply produce no evidence chunks.

Duplicate detection is content-based rather than filename-based. Uploading the same bytes under a different filename returns the original document with `already_existed: true` and creates no additional evidence.

## Project structure

```text
fact-o-check/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   └── types/
│   └── .env.example
├── docs/
└── sample_data/
```

## Setup

### Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- MongoDB running locally, or a MongoDB Atlas connection string

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Use `GET /health` for process health and `GET /ready` to verify that MongoDB is reachable. Interactive API documentation is available at `/docs`.

Run backend checks with:

```bash
pytest
ruff check .
```

### MongoDB Atlas or local MongoDB

For local development, the example configuration expects MongoDB at `mongodb://localhost:27017` and uses the `fact_o_check` database.

For Atlas, copy `backend/.env.example` to `backend/.env`, replace `MONGODB_URI` with the Atlas connection string, and keep credentials only in that ignored `.env` file. Add the machine's IP address to the Atlas network access list and ensure the database user has access to the configured database.

`CORS_ORIGINS` accepts a comma-separated list when more than one frontend origin is needed.

`MAX_UPLOAD_SIZE_BYTES` sets the in-memory upload ceiling and defaults to 25 MiB.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The development UI is available at `http://localhost:5173`. `VITE_API_URL` controls the backend base URL.

Run frontend checks with:

```bash
npm run lint
npm run build
```

## Current phase

Phase 1 complete. The repository supports PDF upload, hash-based deduplication, lifecycle states, PyMuPDF layout extraction, evidence persistence and inspection, list/detail/delete APIs, and a functional document UI. The Overview document count now uses live API data.

### Current limitations

- OCR is not implemented yet, so image-only pages may produce no textual evidence.
- Original PDF files are not retained after in-memory processing.
- PyMuPDF block order is approximate for complex multi-column layouts and tables.
- Upload processing runs within the request lifecycle; a durable background job queue is deferred.
- Fact extraction, embeddings, normalization, and relationship reasoning remain out of scope for Phase 1.

## Roadmap

- Phase 1 — PDF ingestion and evidence (complete)
- Phase 2 — Fact extraction
- Phase 3 — Normalization
- Phase 4 — Relationship reasoning
- Phase 5 — Required-case validation
- Phase 6 — UI polish and generalization
- Phase 7 — Deployment and demo
