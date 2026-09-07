import { GitCompareArrows, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { RelationComparisonSummary } from "../types/api";

export function CompareFactsButton({ documentId }: { documentId: string }) {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<RelationComparisonSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function compare() {
    setLoading(true);
    setError(null);
    setSummary(null);
    try {
      setSummary(await api.documents.compareFacts(documentId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Fact comparison failed.");
    } finally {
      setLoading(false);
    }
  }

  return <div className="extraction-controls">
    <button className="button button--primary" type="button" disabled={loading}
      onClick={() => void compare()}>
      {loading ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> :
        <GitCompareArrows size={16} aria-hidden="true" />}
      {loading ? "Comparing facts…" : "Compare Facts"}
    </button>
    <Link className="button button--secondary" to={`/relationships?document_id=${documentId}`}>
      View relationships
    </Link>
    {error && <div className="message message--error" role="alert">{error}</div>}
    {summary && <div className="message message--success" role="status">
      Compared {summary.pairs_considered} candidate pair{summary.pairs_considered === 1 ? "" : "s"};
      {" "}{summary.relations_created} relation{summary.relations_created === 1 ? "" : "s"} created
      and {summary.duplicates_skipped} duplicate{summary.duplicates_skipped === 1 ? "" : "s"} skipped.
    </div>}
  </div>;
}
