# Fact-O-Check

Fact-O-Check builds a structured fact knowledge layer over PDFs. It extracts numerical and semantic facts, grounds every fact in source evidence, normalizes values and context, and compares claims across documents.

> Facts, not text chunks, are the primary unit of knowledge.

> Fact extraction is probabilistic; evidence provenance is deterministic.

```text
PDF
→ Evidence
→ Structured Facts
→ Normalization
→ Cross-document Comparison
→ Evidence-grounded Explanation
```

## Live Demo

- **Frontend:** https://fact-o-check-nine.vercel.app
- **Backend API:** https://fact-o-check.onrender.com
- **API Documentation:** https://fact-o-check.onrender.com/docs

The frontend is deployed on Vercel, the FastAPI backend is deployed on Render, and the production database uses MongoDB Atlas.

## Demo Video

▶️ **[Watch the Fact-O-Check Demo](https://youtu.be/j19lh4kUtAw)**

The demo is under 3 minutes and shows the end-to-end Fact-O-Check workflow, including evidence-grounded facts, normalization, cross-document comparison, corroboration, reconciliation, and review handling.

## What It Does

Traditional PDF search and RAG retrieve passages. Fact-O-Check instead:

- extracts structured claims;
- keeps source provenance;
- normalizes units, time, and context;
- compares facts across documents; and
- explains agreements, contextual differences, contradictions, and ambiguous cases.

## Pipeline

Fact-O-Check turns uploaded PDFs into evidence-backed structured facts, normalizes them, compares them across documents, and explains how those facts relate.

```mermaid
flowchart LR
    A[PDF Upload] --> B[Evidence Extraction]
    B --> C[Structured Fact Extraction]
    C --> D[Deterministic Normalization]
    D --> E[Candidate Matching]
    E --> F[Cross-document Reasoning]
    F --> G[Relation + Explanation]

    F -. ambiguous semantic cases .-> H[LLM Semantic Fallback]
    H --> G
```

## Core Features

- Arbitrary PDF upload
- PyMuPDF page/block evidence extraction
- Page-level provenance and bounding-box/spatial metadata
- Structured fact extraction
- OpenRouter/OpenAI-compatible provider abstraction
- MongoDB and Beanie persistence
- Deterministic normalization
- INR/USD normalization
- Crore, lakh, million, and report-scale handling
- Percentage normalization
- Fiscal-period and date normalization
- Conservative entity and predicate normalization
- Cross-document candidate generation
- Deterministic-first reasoning with optional semantic fallback
- Evidence-grounded explanations
- Source-document filtering and grouping
- `NEEDS_REVIEW` workflow
- Polished React, TypeScript, and Vite frontend

Relationship labels:

- `CORROBORATES`
- `CONTRADICTS`
- `RECONCILABLE`
- `UNRELATED`
- `NEEDS_REVIEW`

## Verified Assignment Cases

### Corroboration

- **RBI Annual Report FY2024/25:** real GDP growth = `6.5%`
- **IMF India Article IV:** FY2024/25 GDP growth = `6.5%`
- **Result:** `CORROBORATES`

The facts describe a compatible metric for the same fiscal period, their normalized percentages agree, and their evidence provenance was validated.

### Reconciled through context

- **Economic Survey 2024-25:** GDP growth = `6.4%`; first advance estimate
- **IMF India Article IV:** GDP growth = `6.5%`; later expectation/data vintage
- **Result:** `RECONCILABLE`

A naive value-only comparison could call this a contradiction. Estimate status and data-vintage context explain the apparent difference.

### Contradiction

No defensible contradiction was found in the validated starter evidence. The system checked period, scope, units, rounding, estimate/actual context, and data vintage, and intentionally did not manufacture a contradiction.

The Delhivery 59% versus 60% female-workforce case is not a defensible contradiction: the increase from 3,519 to 5,594 is approximately 58.97%, so rounding precision can explain the reported values.

### Real failure

In the verified Delhivery case, `₹1,266Mn` was incorrectly associated with “Revenue from services” even though the value belonged to EBITDA.

Evidence provenance remained valid, but metric/value association failed because PDF reading order differed from the visual layout. Bounding-box context is now passed to extraction, and ambiguous outputs may remain `NEEDS_REVIEW`. The issue is not fully solved; stronger table and layout reconstruction remains future work.

## Architecture

```text
React + TypeScript + Vite frontend
                 |
                 v
          FastAPI REST API
           /            \
          v              v
PyMuPDF + domain      OpenRouter / OpenAI-compatible
services              provider (extraction + fallback)
          \              /
           v            v
           MongoDB + Beanie
           - documents
           - evidence_chunks
           - facts
           - fact_relations
```

The frontend invokes explicit upload, extraction, normalization, and comparison operations through FastAPI. Domain services validate provenance and apply deterministic logic; provider calls are limited to structured extraction and ambiguous semantic fallback. Beanie persists documents, evidence chunks, facts, and cross-document relations in MongoDB.

## Setup & Run

Requirements: Python 3.11+, Node.js/npm, MongoDB, and an OpenAI or OpenRouter key for live extraction or semantic fallback.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Local URLs:

- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs

## Environment Variables

Only variable names are documented; never commit secret values.

Backend:

- `APP_ENV`
- `APP_NAME`
- `API_PREFIX`
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `CORS_ORIGINS`
- `MAX_UPLOAD_SIZE_BYTES`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `OPENROUTER_API_KEY`
- `OPENROUTER_HTTP_REFERER`
- `OPENROUTER_X_TITLE`
- `LLM_TIMEOUT_SECONDS`
- `EXTRACTION_WINDOW_CHARS`
- `EXTRACTION_WINDOW_CHUNKS`
- `EXTRACTION_MAX_WINDOWS`
- `EXTRACTION_MAX_OUTPUT_TOKENS`

Frontend:

- `VITE_API_BASE_URL`

Current production provider configuration:

```text
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4.1-nano
```

## Deployment

### MongoDB Atlas

- **Production database:** `fact_o_check`

### Render Backend

- **URL:** https://fact-o-check.onrender.com
- **Root directory:** `backend`
- **Build command:** `pip install .`
- **Start command:** `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health:** https://fact-o-check.onrender.com/health
- **Ready:** https://fact-o-check.onrender.com/ready
- **Docs:** https://fact-o-check.onrender.com/docs

### Vercel Frontend

- **URL:** https://fact-o-check-nine.vercel.app
- **Root directory:** `frontend`
- **Framework:** Vite
- **Build command:** `npm run build`
- **Output directory:** `dist`
- **Production API:** `VITE_API_BASE_URL=https://fact-o-check.onrender.com`

## API Overview

Health:

- `GET /health`
- `GET /ready`

Documents:

- `POST /api/documents`
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `DELETE /api/documents/{document_id}`
- `GET /api/documents/{document_id}/evidence`
- `POST /api/documents/{document_id}/extract-facts`
- `POST /api/documents/{document_id}/normalize-facts`
- `POST /api/documents/{document_id}/compare-facts`

Facts:

- `GET /api/facts`
- `GET /api/facts/{fact_id}`
- `POST /api/facts/{fact_id}/normalize`

Relations:

- `GET /api/relations`
- `GET /api/relations/{relation_id}`

## Demo Flow

The final demonstration is designed to fit within three minutes:

1. Show Home and explain: Upload → Evidence → Facts → Normalize → Compare → Explain.
2. Open a processed document.
3. Open a fact and show its raw value, normalized value, source, page, and evidence.
4. Open **Relationships → Corroborated** and show RBI 6.5% versus IMF 6.5%.
5. Open **Relationships → Reconciled** and show Economic Survey 6.4% versus IMF 6.5%.
6. Show **Needs Review** and the Delhivery failure.
7. Show **Contradictions = 0** and explain that no unsupported contradiction was forced.
8. Close with: “Facts, not text chunks, are the primary unit of knowledge.”

## Testing

Latest validated checkpoints:

- 139 backend tests passed during India validation.
- Later targeted provider and debug suites passed.
- Ruff passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.

```bash
cd backend
pytest
ruff check .

cd ../frontend
npm run lint
npm run build
```

## Limitations & Next Steps

Current limitations:

- No OCR; image-only pages may produce no evidence text.
- Complex tables and multi-column layouts can break label/value association.
- LLM extraction remains probabilistic.
- Conservative matching may miss valid relations.
- No foreign-exchange conversion.
- No physical-unit conversion.
- Sparse context produces `NEEDS_REVIEW`.
- Extraction is synchronous and can be slow.
- Large documents may require many provider calls.
- Provider quota or credit limits can cause partial extraction.
- No contradiction is guaranteed to exist in a dataset.
- Original PDF bytes are parsed in memory but are not persisted after ingestion.

Next steps:

- Stronger table and layout reconstruction
- OCR or multimodal fallback
- Semantic entity resolution
- Richer data-vintage modeling
- Asynchronous/background extraction
- Resumable extraction
- Persistent object/PDF storage
- Broader evaluation datasets
- Dedicated human-review workflow
- Better provider quota and retry handling

## Additional Notes

- Starter datasets were used only for validation.
- Production logic contains no filename-specific rules or hard-coded expected relation labels.
- Classifications come from persisted extracted facts.
- Deterministic paths reduce LLM usage and cost.
- Unclear evidence defaults toward `NEEDS_REVIEW` instead of an unsupported conclusion.
- Confidence metadata assists review and does not represent absolute certainty.
