# Fact-O-Check

## Overview

Fact-O-Check is an evidence-grounded fact knowledge layer for PDFs. It is designed to extract structured facts, preserve document and page provenance, link every fact to exact source evidence, and compare facts across documents with explainable relationship classifications.

> Facts, not text chunks, are the primary unit of knowledge.

This repository contains the Phase 2 application: PDFs can be uploaded, parsed into evidence blocks, and explicitly converted into structured facts with inspectable provenance. Normalization and relationship reasoning are intentionally not implemented yet.

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

PyMuPDF performs local layout-block extraction during ingestion. A provider-independent fact extraction service consumes stored evidence only when explicitly requested. Future stages will add normalization, relationship reasoning, and retrieval.

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

`EvidenceChunk` records reference a document by `PydanticObjectId`; they do not embed the full document. Each chunk retains a PyMuPDF bounding box and ordering metadata so later phases can cite a page, reconstruct approximate reading order, and investigate layout or table extraction failures. Deleting a document cascades to its facts and evidence chunks.

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
test -e .env || cp .env.example .env
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

Phase 2 implemented. Phase 1 ingestion remains intact. Document Detail offers explicit fact extraction with progress, configuration errors, and complete/partial/failed summaries. Facts supports paginated browsing, exact filters, and detail views with source documents, page numbers, and original evidence text. Upload never triggers an LLM call.

## Fact extraction

> Fact extraction is probabilistic; evidence provenance is deterministic.

`FactExtractor` is an asynchronous protocol accepting bounded `EvidenceContext` windows and returning untrusted structured candidates. The workflow handles document eligibility, windowing, schema/provenance validation, deduplication, and persistence independently of the provider. Tests inject `FakeFactExtractor` and mock HTTP transport; no paid calls are required.

The OpenAI and OpenRouter adapters use the same OpenAI-compatible Chat Completions request and strict JSON Schema response format. Qualifiers travel as key/value text pairs because strict schemas disallow arbitrary object keys; the adapter converts them into the existing fact qualifiers dictionary. Refusals, truncation, malformed envelopes, HTTP failures, and timeouts produce safe error codes without returning provider bodies or logging API keys.

### Configuration

Add these values to the ignored `backend/.env` (start the backend from `backend/`):

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_HTTP_REFERER=
OPENROUTER_X_TITLE=Fact-O-Check
LLM_TIMEOUT_SECONDS=45
EXTRACTION_WINDOW_CHARS=12000
EXTRACTION_WINDOW_CHUNKS=20
EXTRACTION_MAX_WINDOWS=30
EXTRACTION_MAX_OUTPUT_TOKENS=4000
```

Set a real key locally to enable extraction. An empty key does not prevent startup; extraction returns HTTP 503 `llm_not_configured`. Unknown providers return HTTP 503 `llm_provider_unsupported`. The chosen model must support strict structured output. Evidence in each requested window is sent to the configured LLM provider; original PDFs are not sent. API storage is disabled with `store: false`.

### Providers

OpenAI uses `LLM_PROVIDER=openai`, `LLM_MODEL=<OpenAI model>`, and `LLM_API_KEY=<secret>`.

OpenRouter uses `LLM_PROVIDER=openrouter`, `LLM_MODEL=<OpenRouter model slug>`, and `OPENROUTER_API_KEY=<secret>`. OpenRouter is OpenAI-compatible, so it can switch among compatible models without changing the extraction pipeline. `OPENROUTER_BASE_URL` defaults to `https://openrouter.ai/api/v1`; `OPENROUTER_HTTP_REFERER` and `OPENROUTER_X_TITLE` are optional attribution headers, with the title defaulting to `Fact-O-Check`.

### Fact schema and validation

The existing `Fact` model retains document ID, evidence IDs, subject, predicate, raw/normalized value and unit, value type, period start/end, as-of date, geography, scope, qualifiers, confidence, metadata, and timestamps. Phase 2 candidates support NUMBER, PERCENTAGE, CURRENCY, DATE, BOOLEAN, STRING, ENTITY, and QUANTITY. All raw values, even numbers and booleans, are strings copied verbatim from evidence; normalized fields remain null.

The prompt requests meaningful supported claims, explicit context, lower confidence for ambiguity, and no invented information or mathematical normalization. Ambiguous dates remain original labels in qualifiers rather than invented calendar dates. The workflow validates each candidate independently and requires every reference to occur in that exact window from the same document. The raw value must occur verbatim in a cited text fragment. Insert/save/replace hooks also reject missing, nonexistent, or foreign-document evidence. These checks establish provenance, not the semantic truth of the model's interpretation. Internal prompts and reasoning are not returned in fact APIs.

### Windowing and cost

Chunks are ordered by page, block index, then ID and greedily packed with adjacent content, including page boundaries, up to the configured text-character and chunk limits. There is no overlap or per-block call requirement. Oversized chunks are split into bounded fragments preserving the original chunk ID, page, and character offset; no text is silently truncated. Identical windows are removed within a run. Bounds apply to evidence text; IDs, JSON escaping, schema, and instructions add overhead, and character counts are not exact token counts.

Calls are sequential with no automatic retries. The default cap is 30 windows, 4,000 output tokens per call, 45 seconds per call, and a 180-second overall LLM budget per request. The summary reports skipped windows if budget/caps are reached; increase window or count limits for large documents, subject to the request budget. Explicit re-extraction calls the provider again and incurs usage; there is no persistent window cache or resumable queue yet. Logs report processed/failed windows, accepted/created facts, and duration without evidence text or credentials.

### Deduplication and failure behavior

Deduplication is within one document only. It compares exact subject, predicate, raw value, value type, raw unit, dates/period, geography, scope, and qualifiers, and requires overlapping evidence IDs. Different dates, scope, qualifiers, or disjoint evidence remain distinct. No semantic canonicalization or cross-document matching occurs.

Re-extraction conservatively merges: identical supported facts retain their IDs and confidence; distinct candidates are added. Existing facts are never erased by an empty result or failed window. Results from successful windows persist even if others fail. This preserves prior output but may retain stale or differently phrased interpretations; re-extraction is not replacement. A five-minute MongoDB lease excludes concurrent extraction/deletion across API workers and expires after a crash. Database failures use the existing 503 handler; prior successful writes remain available.

### APIs

- `POST /api/documents/{document_id}/extract-facts`: requires an existing PROCESSED document; returns status, windows processed/failed/skipped, facts produced/created/deduplicated, rejected candidates, safe failure codes, and duration. HTTP 200 summaries can be `completed`, `partial`, or `failed`; clients must inspect status. Missing documents return 404, ineligible/busy documents 409, missing LLM configuration 503.
- `GET /api/facts`: paginated `{items,total,offset,limit}` with optional exact `document_id`, `subject`, `predicate`, and `value_type` filters; default limit 50, maximum 100.
- `GET /api/facts/{fact_id}`: structured fact fields, source document, page numbers, evidence text, and confidence. Unknown facts return 404; invalid IDs/filters return 422.

### Current limitations

- OCR is not implemented yet, so image-only pages may produce no textual evidence.
- Original PDF files are not retained after in-memory processing.
- PyMuPDF block order is approximate for complex multi-column layouts and tables.
- Upload processing runs within the request lifecycle; a durable background job queue is deferred.
- Extraction depends on source layout and model interpretation; verbatim values and valid citations do not prove semantic correctness. Confidence is self-reported, not calibrated.
- Nonoverlapping window boundaries can split context. Large documents can hit caps, and skipped windows are not automatically resumed.
- Strict verbatim-value validation may reject otherwise useful paraphrases or values spanning fragments.
- No normalization, conversion, embeddings, vector/graph database, cross-document reasoning, RAG/chat, or deployment is implemented.
- Tests use MongoDB mocks and fake providers; real provider/account compatibility requires an optional live smoke test with a configured key.

## Roadmap

- Phase 1 — PDF ingestion and evidence (complete)
- Phase 2 — Fact extraction (implemented)
- Phase 3 — Normalization
- Phase 4 — Relationship reasoning
- Phase 5 — Required-case validation
- Phase 6 — UI polish and generalization
- Phase 7 — Deployment and demo
