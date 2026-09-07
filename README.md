# Fact-O-Check

## Overview

Fact-O-Check is an evidence-grounded fact knowledge layer for PDFs. It is designed to extract structured facts, preserve document and page provenance, link every fact to exact source evidence, and compare facts across documents with explainable relationship classifications.

> Facts, not text chunks, are the primary unit of knowledge.

This repository currently contains the Phase 0 application and architecture scaffold. PDF ingestion, extraction, normalization, and relationship reasoning are intentionally not implemented yet.

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

Future stages will add PDF ingestion, evidence extraction, fact extraction, normalization, relationship reasoning, and retrieval. None of those processing stages are implemented in Phase 0.

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

Phase 0 complete. The repository contains the modular backend foundation, MongoDB/Beanie schemas, health and readiness behavior, test scaffold, and the routed frontend dashboard. Processing buttons and data views are placeholders by design.

## Roadmap

- Phase 1 — PDF ingestion and evidence
- Phase 2 — Fact extraction
- Phase 3 — Normalization
- Phase 4 — Relationship reasoning
- Phase 5 — Required-case validation
- Phase 6 — UI polish and generalization
- Phase 7 — Deployment and demo

