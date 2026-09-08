# Fact-O-Check

Fact-O-Check builds a structured fact knowledge layer over PDFs. It extracts numerical and semantic facts, grounds every fact in page-level evidence, normalizes values and context, and compares facts across documents to identify agreements, conflicts, contextual reconciliations, and cases requiring review.

> Facts, not text chunks, are the primary unit of knowledge.

Every fact remains traceable to its source document, page, and extracted evidence block.

## Problem Statement

Traditional PDF search and RAG retrieve passages, but they do not reliably represent individual factual claims. Fact-O-Check instead:

- extracts structured facts;
- preserves exact evidence provenance;
- normalizes values, units, time, and context;
- compares facts across documents; and
- explains why facts corroborate, contradict, reconcile, or need review.

## What Fact-O-Check Does

```text
PDF Upload
    → Evidence Extraction
    → Structured Fact Extraction
    → Deterministic Normalization
    → Cross-Document Comparison
    → Evidence-Grounded Relationship Explanation
```

Users can upload arbitrary PDFs through the React UI or FastAPI API. PyMuPDF extracts page-level layout blocks, while MongoDB and Beanie persist documents, evidence, facts, and relations. A provider-independent extractor supports OpenAI and OpenRouter through an OpenAI-compatible interface. Normalization is deterministic, relation reasoning is deterministic first, and an optional semantic fallback handles comparisons whose meaning cannot be resolved safely with local rules.

## Key Features

### Evidence-grounded facts

Every extracted fact stores or references:

- its document and 1-indexed page;
- one or more evidence chunks;
- block order and bounding-box provenance;
- the exact raw value and unit;
- subject, predicate, scope, geography, period, qualifiers, and confidence.

Candidate facts are schema-validated. Evidence references must belong to the same document and extraction window, and the raw value must occur verbatim in cited evidence.

> Fact extraction is probabilistic; evidence provenance is deterministic.

### Deterministic normalization

The normalization layer supports:

- INR and USD in base currency units;
- crore, million, lakh, thousand, and common report abbreviations such as `Cr`, `Mn`, `Bn`, and `K`;
- percentages, counts, typed quantities, booleans, and directly parseable dates;
- fiscal years, fiscal quarters, year-ended periods, and as-of dates; and
- conservative entity and predicate canonicalization.

There is no foreign-exchange or physical-unit conversion. Unsupported or ambiguous values remain explicit with normalization warnings rather than being guessed.

### Cross-document reasoning

Fact-O-Check uses five relationship labels:

- `CORROBORATES`
- `CONTRADICTS`
- `RECONCILABLE`
- `UNRELATED`
- `NEEDS_REVIEW`

> Deterministic checks decide clear numerical relationships; LLM reasoning is reserved for ambiguous semantic context.

Clear numerical relationships use normalized types, units, values, tolerances, and context without an LLM call. Semantic fallback is considered only when deterministic rules cannot safely resolve predicate wording or contextual meaning.

### Explainable relationships

Relation details expose Fact A and Fact B, their raw and normalized values, source documents and pages, evidence text, contextual differences, confidence, and safe structured reasoning metadata. Provider prompts and private reasoning are not persisted or returned.

## Architecture

```text
React + TypeScript + Vite
        |
        v
FastAPI REST API
        |
        +--> PDF Evidence Extraction (PyMuPDF)
        |
        +--> Fact Extraction
        |       |
        |       +--> OpenAI / OpenRouter provider adapter
        |
        +--> Deterministic Normalization
        |
        +--> Relation Candidate Generation
        |
        +--> Deterministic Reasoning
        |       |
        |       +--> Semantic fallback when ambiguous
        |
        v
MongoDB / Beanie
    - documents
    - evidence_chunks
    - facts
    - fact_relations
```

The API initializes MongoDB and Beanie during its FastAPI lifespan. Upload, extraction, normalization, and comparison are separate explicit operations. Uploading a PDF does not automatically invoke an LLM.

## Data Model

### `documents`

Stores uploaded-PDF metadata, content hash, file size, page count, processing status, and safe failure information. Duplicate detection uses the content hash.

### `evidence_chunks`

Stores page/block-level text with its document reference, page number, block index, bounding box, and layout metadata. Evidence is stored separately so multiple facts can cite the same source block.

### `facts`

Stores structured claims containing subject, predicate, raw and normalized values and units, value type, temporal context, geography, scope, qualifiers, confidence, extraction metadata, and evidence references.

### `fact_relations`

Links two cross-document facts with a relationship label, confidence, explanation, candidate-match information, deterministic value checks, and structured context metadata.

## Approach

### Stage 1 — Evidence first

PDFs are converted into stable, ordered page/block evidence before factual interpretation. This creates a source layer that can be inspected independently of model output.

### Stage 2 — Structured extraction

The configured LLM receives bounded evidence windows and returns typed fact candidates constrained by strict JSON Schema. Pydantic and provenance validation run before persistence.

### Stage 3 — Deterministic normalization

Numbers, currencies, percentages, units, entities, predicates, and temporal context are normalized conservatively. Raw extracted fields remain available for comparison and audit.

### Stage 4 — Candidate matching

Only likely comparable cross-document facts are evaluated. Matching uses compatible value types and units, canonical subjects, safe common reporting phrases, and a conservative token-similarity threshold.

### Stage 5 — Deterministic-first reasoning

Typed tolerances and explicit period, scope, geography, and reporting-status checks resolve clear numerical relationships locally.

### Stage 6 — Semantic fallback

Provider-independent LLM reasoning is available only when deterministic rules cannot safely resolve semantic context. Invalid or failed fallback output becomes `NEEDS_REVIEW`.

### Stage 7 — Evidence-grounded explanation

Every persisted relation links back to both structured facts and their PDF evidence. The system prefers `NEEDS_REVIEW` over an unsupported conclusion.

## Verified Assignment Cases

Validation used persisted starter evidence and the same production extraction, normalization, and relation schemas. No filename-specific rule or expected label was added.

### Case 1 — Corroboration

- **RBI Annual Report FY2024/25:** real GDP growth of `6.5 per cent`.
- **IMF India Article IV:** expected real GDP growth of `6.5 percent` for 2024/25.
- **Result:** `CORROBORATES`.

Both facts are stored on page 1 of their scoped evidence documents. They normalize to `6.5 PERCENT` for the same fiscal period, subject, and compatible GDP-growth metric. Both facts have valid persisted evidence references.

### Case 2 — Reconciled through context

- **Economic Survey 2024-25:** real GDP growth of `6.4 per cent` for FY25, identified as the first advance estimate.
- **IMF India Article IV:** expected real GDP growth of `6.5 percent` for 2024/25.
- **Result:** `RECONCILABLE`.

Both facts are stored on page 1 of their scoped evidence documents. A value-only comparison could treat the difference as conflict, but the explicit estimate-versus-expectation context and data vintage explain the apparent mismatch.

### Case 3 — Contradiction not found

No defensible contradiction was found in the validated starter evidence. Candidates were checked for matching period, scope, units, geography, rounding, estimate status, and data vintage. The system did not manufacture a conflict; incomplete and ambiguous candidates remained `NEEDS_REVIEW` or were not related.

The Delhivery Annual Report says female-worker headcount increased by both 60% in a summary statement and 59% in detailed evidence. The detailed counts rise from 3,519 to 5,594, which is approximately 58.97%. The persisted 60% fact and 59% evidence can therefore reflect different rounding precision, and they were not labeled `CONTRADICTS`.

### Case 4 — Real failure

On Delhivery Annual Report page 5, extraction associated `₹1,266Mn` with `Revenue from services`, although the page layout places that value under EBITDA. Provenance validation succeeded—the cited value and evidence block were real—but the spatial table association was wrong. This shows that PDF text reading order does not always preserve the visual relationship between a metric label and value.

Current mitigation passes bounding-box coordinates into extraction, keeps source evidence inspectable, and allows ambiguous comparisons to remain `NEEDS_REVIEW`. The failure is not fully solved. Stronger table/layout reconstruction, multimodal or table-aware extraction, and an OCR/layout fallback are future improvements.

## Why Not Force a Contradiction?

Correctness matters more than satisfying a label count. Fact-O-Check returns `NEEDS_REVIEW` or no contradiction when the evidence does not support a genuine same-period, same-scope conflict. This is conservative reasoning rather than fabricated certainty.

## Demo Flow

The following path fits a three-minute evaluator demo:

1. Open Fact-O-Check and select **Documents**.
2. Upload a PDF, or select a persisted starter document.
3. Open **Document Detail** and show the Upload → Extract → Normalize → Compare workflow.
4. Extract facts, normalize them, and compare them with persisted facts from other sources.
5. Open **Facts** and inspect a structured fact, its normalized fields, page, and evidence.
6. Open **Relationships**, filter **Corroborated**, and inspect the RBI/IMF 6.5% GDP pair.
7. Filter **Reconciled** and inspect the Economic Survey 6.4% versus IMF 6.5% GDP pair.
8. Show that **Contradictions** honestly displays zero for the validated data.
9. Open **Needs Review** to inspect comparisons with missing or ambiguous context.
10. Open **Relation Detail** and show both source documents, pages, evidence panels, contextual checks, and explanation.

## Setup & Run

### Prerequisites

- Python 3.11 or newer
- Node.js and npm; the repository does not pin a Node version
- MongoDB running locally or a MongoDB Atlas connection string
- an OpenAI or OpenRouter API key for live extraction and semantic fallback
- optional Docker for a separately managed MongoDB instance; this repository does not include Docker or Compose configuration

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# Configure MongoDB and one LLM provider in .env.
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`, Swagger UI is at `http://localhost:8000/docs`, process health is available at `/health`, and database readiness is available at `/ready`.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend development server runs at `http://localhost:5173` and uses `VITE_API_BASE_URL` for the backend origin.

## Environment Variables

Only variable names are shown here; keep credentials in ignored local `.env` files.

Backend application and database:

- `APP_ENV`
- `APP_NAME`
- `API_PREFIX`
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `CORS_ORIGINS`
- `MAX_UPLOAD_SIZE_BYTES`

LLM and extraction:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY` — OpenAI credential
- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_HTTP_REFERER`
- `OPENROUTER_X_TITLE`
- `LLM_TIMEOUT_SECONDS`
- `EXTRACTION_WINDOW_CHARS`
- `EXTRACTION_WINDOW_CHUNKS`
- `EXTRACTION_MAX_WINDOWS`
- `EXTRACTION_MAX_OUTPUT_TOKENS`

Frontend:

- `VITE_API_BASE_URL`

## API Overview

### Health

- `GET /health`
- `GET /ready`

### Documents

- `POST /api/documents`
- `GET /api/documents`
- `GET /api/documents/{id}`
- `DELETE /api/documents/{id}`
- `GET /api/documents/{id}/evidence`
- `POST /api/documents/{id}/extract-facts`
- `POST /api/documents/{id}/normalize-facts`
- `POST /api/documents/{id}/compare-facts`

### Facts

- `GET /api/facts`
- `GET /api/facts/{id}`
- `POST /api/facts/{id}/normalize`

### Relations

- `GET /api/relations`
- `GET /api/relations/{id}`

## Testing

The latest verified checkpoint has 142 passing backend tests. The frontend lint and production build checks also pass.

```bash
cd backend
pytest
ruff check .

cd ../frontend
npm run lint
npm run build
```

Provider tests use fakes or mocked HTTP transports and do not make paid API calls.

## Project Structure

```text
fact-o-check/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── normalization/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── frontend/
│   └── src/
├── docs/
├── sample_data/
└── README.md
```

## Deployment

Deployment is configured as three independent services: MongoDB Atlas for persistence, a Render Web Service for the FastAPI backend, and a Vercel project for the Vite frontend. No live service URLs or credentials are committed.

### MongoDB Atlas

Create an Atlas cluster, database user, and network-access rule that permits the Render service to connect. Set `MONGODB_URI` to the Atlas `mongodb+srv://` connection string and set `MONGODB_DB_NAME` to the target database. The URI and database name are read entirely from the environment; never place the Atlas password in a committed file.

### Render Backend

Create a Python Web Service with these settings:

- **Root Directory:** `backend`
- **Build Command:** `pip install .`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`

Set these environment variables in Render:

- `APP_ENV=production`
- `APP_NAME`
- `API_PREFIX`
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `CORS_ORIGINS` — comma-separated explicit origins, such as the production Vercel origin and `http://localhost:5173` when local frontend access is required; `*` is rejected
- `MAX_UPLOAD_SIZE_BYTES`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY` when using OpenAI, or `OPENROUTER_API_KEY` when using OpenRouter
- `OPENROUTER_BASE_URL`, `OPENROUTER_HTTP_REFERER`, and `OPENROUTER_X_TITLE` when applicable
- the `LLM_TIMEOUT_SECONDS` and `EXTRACTION_*` limits when overriding their defaults

Render supplies `PORT`; the start command binds Uvicorn to that port on `0.0.0.0`. Use `/health` for process health and `/ready` when database readiness must also be confirmed.

### Vercel Frontend

Create a Vite project with these settings:

- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variable:** `VITE_API_BASE_URL=https://<render-backend>`

`frontend/vercel.json` rewrites browser requests to `index.html`, so `/`, `/overview`, document and fact detail routes, and relationship routes can be opened or refreshed directly without a Vercel 404. The Vite development fallback remains `http://localhost:8000`.

### Deployment limitations

- Original PDF bytes are parsed in memory and are not retained after ingestion. Document metadata plus extracted evidence, facts, and relationships persist in MongoDB, but reopening the original PDF requires future object storage.
- Upload, fact extraction, normalization, and comparison run synchronously in request workflows. Large documents can approach host or client request timeouts; this release does not add background queues.
- Uploads remain bounded by `MAX_UPLOAD_SIZE_BYTES`, provider calls by `LLM_TIMEOUT_SECONDS`, and extraction work by the `EXTRACTION_*` limits.
- OCR and durable source-file storage are not implemented.

### Production checklist

- [ ] MongoDB Atlas is reachable from Render.
- [ ] Backend `GET /health` succeeds.
- [ ] Backend `GET /ready` confirms the database connection.
- [ ] The Vercel frontend loads with the Render API base URL.
- [ ] The frontend can list documents.
- [ ] A bounded PDF upload succeeds.
- [ ] Fact extraction works with the configured provider.
- [ ] Normalization works.
- [ ] Cross-document comparison works.
- [ ] Relationships load with evidence provenance.
- [ ] Direct route refreshes resolve to the SPA.
- [ ] Browser responses, logs, and committed files expose no secrets.

## Limitations & Next Steps

Current limitations:

- OCR is not implemented, so image-only pages may produce no evidence text.
- Complex tables and multi-column reading order can break label/value association.
- Broad semantic entity resolution is not implemented.
- Conservative candidate matching can miss valid relationships.
- Foreign-exchange and physical-unit conversion are not implemented.
- LLM extraction remains probabilistic, and confidence is not calibrated.
- A dataset is not guaranteed to contain a defensible contradiction.
- Sparse context intentionally produces `NEEDS_REVIEW`.
- Original PDF bytes are not persisted after ingestion; only metadata and extracted evidence are stored.
- Upload, extraction, normalization, and comparison run synchronously in request workflows rather than durable background jobs.

Next steps include stronger table and layout reconstruction, OCR or multimodal fallback, semantic entity resolution, explicit data-vintage modeling, asynchronous job processing, object storage for source PDFs, a richer evaluation dataset, and a dedicated human-review workflow.

## Additional Notes

- Starter data was used for validation, not production hard-coding.
- There are no filename-specific production rules or hard-coded expected relationship labels in production logic.
- Relationship classifications come from persisted extracted facts.
- The OpenAI/OpenRouter abstraction allows provider changes without changing the extraction workflow.
- Deterministic normalization and reasoning paths minimize LLM calls and cost.
- Confidence and reasoning metadata support review; they do not imply absolute certainty.

## Tech Stack

- **Frontend:** React, TypeScript, Vite, React Router, Lucide React
- **Backend:** FastAPI, Python, PyMuPDF, Beanie, Pydantic
- **Database:** MongoDB
- **AI:** provider-independent OpenAI/OpenRouter-compatible structured extraction and semantic reasoning
- **Testing and quality:** pytest, Ruff, ESLint, TypeScript, and Vite build tooling

## Demo Video

**TODO:** [Demo video — add link before submission]

## Live Demo

Deployment pending.

Once deployed, this section can list the frontend, API, and API documentation URLs.

## GitHub / Development

Development used incremental, meaningful commits covering the application scaffold, PDF evidence ingestion, structured fact extraction, deterministic normalization, cross-document relation reasoning, real-data validation, and frontend polish.
