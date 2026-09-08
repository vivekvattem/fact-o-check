import { LoaderCircle, ScanSearch } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { DocumentStatus, ExtractionSummary } from "../types/api";

export function ExtractFactsButton({ documentId, status, onComplete }: {
  documentId: string; status: DocumentStatus; onComplete?: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<ExtractionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function extract() {
    setLoading(true);
    setError(null);
    setSummary(null);
    try {
      setSummary(await api.documents.extractFacts(documentId));
      onComplete?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Fact extraction failed.");
    } finally {
      setLoading(false);
    }
  }

  return <div className="extraction-controls">
    <button type="button" className="button button--primary" onClick={() => void extract()}
      disabled={loading || status !== "PROCESSED"}>
      {loading ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> :
        <ScanSearch size={16} aria-hidden="true" />}
      {loading ? "Extracting facts…" : "Extract Facts"}
    </button>
    <Link className="button button--secondary" to={`/facts?document_id=${documentId}`}>
      View document facts
    </Link>
    {error && <div className="message message--error" role="alert">{error}</div>}
    {summary && <div className={`message ${summary.status !== "completed" ? "message--warning" : "message--success"}`}
      role="status">
      Extraction {summary.status}: {summary.facts_created} new facts,
      {" "}{summary.facts_deduplicated} duplicates skipped.
      {" "}{summary.windows_processed}/{summary.windows_total} windows processed
      in {summary.duration_seconds}s. {summary.windows_failed} failed,
      {" "}{summary.windows_skipped} skipped, {summary.candidates_rejected} candidates rejected.
      {summary.facts_produced === 0 && " No supported facts were produced."}
      {summary.failures.map(f => <p key={f.window}>Window {f.window}: {f.code}</p>)}
    </div>}
  </div>;
}
