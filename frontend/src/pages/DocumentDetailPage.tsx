import {
  ArrowLeft,
  Box,
  ChevronLeft,
  ChevronRight,
  FileText,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import { CompareFactsButton } from "../components/CompareFactsButton";
import { ExtractFactsButton } from "../components/ExtractFactsButton";
import { LoadingState } from "../components/LoadingState";
import { DocumentWorkflow } from "../components/DocumentWorkflow";
import type { DocumentRecord, EvidencePage } from "../types/api";

const PAGE_SIZE = 20;

function formatBytes(bytes: number | null) {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentDetailPage() {
  const { documentId = "" } = useParams();
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [evidence, setEvidence] = useState<EvidencePage | null>(null);
  const [selectedPage, setSelectedPage] = useState<number | undefined>();
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.documents.get(documentId),
      api.documents.evidence(documentId, {
        page: selectedPage,
        offset,
        limit: PAGE_SIZE,
      }),
    ])
      .then(([documentResult, evidenceResult]) => {
        if (!active) return;
        setDocument(documentResult);
        setEvidence(evidenceResult);
      })
      .catch(() => {
        if (active) setError("This document or its evidence could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [documentId, offset, selectedPage]);

  const pages = useMemo(
    () => Array.from({ length: document?.page_count ?? 0 }, (_, index) => index + 1),
    [document?.page_count],
  );

  if (loading && document === null) {
    return (
      <div className="page loading-panel detail-loading">
        <LoadingState label="Loading document and evidence…" />
      </div>
    );
  }

  if (error || !document || !evidence) {
    return (
      <div className="page">
        <Link className="back-link" to="/documents">
          <ArrowLeft size={16} /> Back to documents
        </Link>
        <div className="message message--error" role="alert">
          {error ?? "Document not found."}
        </div>
      </div>
    );
  }

  const shownFrom = evidence.total === 0 ? 0 : evidence.offset + 1;
  const shownTo = Math.min(evidence.offset + evidence.items.length, evidence.total);

  return (
    <div className="page">
      <Link className="back-link" to="/documents">
        <ArrowLeft size={16} /> Back to documents
      </Link>

      <header className="document-detail-header">
        <div className="document-detail-title">
          <span className="document-icon document-icon--large">
            <FileText size={22} />
          </span>
          <div>
            <span className="eyebrow">Evidence source</span>
            <h1>{document.original_filename}</h1>
          </div>
        </div>
        <span className={`document-status document-status--${document.status.toLowerCase()}`}>
          {document.status}
        </span>
      </header>

      {document.error_message && (
        <div className="message message--error" role="alert">
          {document.error_message}
        </div>
      )}

      <section className="detail-section" aria-labelledby="metadata-heading">
        <div className="section-heading">
          <div><span className="eyebrow">Document record</span><h2 id="metadata-heading">Metadata</h2></div>
        </div>
        <div className="metadata-grid">
          <Metadata label="Pages" value={String(document.page_count ?? "—")} />
          <Metadata label="Evidence blocks" value={String(document.evidence_chunk_count)} />
          <Metadata label="File size" value={formatBytes(document.file_size_bytes)} />
          <Metadata label="SHA-256" value={`${document.content_hash.slice(0, 16)}…`} />
        </div>
      </section>

      <DocumentWorkflow key={documentId} document={document} revision={revision} onChange={() => setRevision(value => value + 1)} />
      <section className="detail-section action-panel panel" aria-labelledby="actions-heading">
        <div>
          <span className="eyebrow">Knowledge actions</span>
          <h2 id="actions-heading">Fact extraction</h2>
          <p>Create structured facts from this document’s stored evidence.</p>
        </div>
        <ExtractFactsButton key={documentId} documentId={documentId} status={document.status} onComplete={() => setRevision(value => value + 1)} />
      </section>

      <section className="detail-section action-panel panel" aria-labelledby="comparison-heading">
        <div>
          <span className="eyebrow">Cross-document reasoning</span>
          <h2 id="comparison-heading">Fact comparison</h2>
          <p>Compare this document’s normalized facts with likely matches from other sources.</p>
        </div>
        <CompareFactsButton key={`compare-${documentId}`} documentId={documentId} onComplete={() => setRevision(value => value + 1)} />
      </section>

      <section className="evidence-section detail-section" aria-labelledby="evidence-heading">
        <div className="evidence-toolbar">
          <div>
            <span className="eyebrow">Extracted content</span>
            <h2 id="evidence-heading">Evidence blocks</h2>
            <p className="section-description">Inspect the exact page content available to extraction.</p>
          </div>
          <label className="page-filter">
            <span>Page</span>
            <select
              value={selectedPage ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                setSelectedPage(value ? Number(value) : undefined);
                setOffset(0);
              }}
            >
              <option value="">All pages</option>
              {pages.map((page) => (
                <option key={page} value={page}>
                  {page}
                </option>
              ))}
            </select>
          </label>
        </div>

        {loading ? (
          <div className="evidence-empty">
            <LoadingState label="Loading evidence…" compact />
          </div>
        ) : evidence.items.length === 0 ? (
          <div className="evidence-empty">
            No textual evidence was extracted{selectedPage ? ` from page ${selectedPage}` : ""}.
          </div>
        ) : (
          <div className="evidence-list">
            {evidence.items.map((chunk) => (
              <article className="evidence-card" key={chunk.id}>
                <div className="evidence-card__meta">
                  <span>Page {chunk.page_number}</span>
                  <span>Block {chunk.block_index + 1}</span>
                  {chunk.bbox && (
                    <span title={chunk.bbox.map((value) => value.toFixed(1)).join(", ")}>
                      <Box size={13} /> Bounding box
                    </span>
                  )}
                </div>
                <p>{chunk.text}</p>
              </article>
            ))}
          </div>
        )}

        <nav className="pagination" aria-label="Evidence pagination">
          <span>
            Showing {shownFrom}–{shownTo} of {evidence.total}
          </span>
          <div>
            <button
              className="pagination-button"
              type="button"
              aria-label="Previous evidence page"
              disabled={offset === 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              className="pagination-button"
              type="button"
              aria-label="Next evidence page"
              disabled={offset + PAGE_SIZE >= evidence.total || loading}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </nav>
      </section>
    </div>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
