import { useEffect, useState } from "react";
import { Check, GitCompareArrows, ScanSearch, Upload, WandSparkles } from "lucide-react";
import { api } from "../api/client";
import type { DocumentRecord, NormalizationSummary } from "../types/api";

export function DocumentWorkflow({ document, revision, onChange }: {
  document: DocumentRecord; revision: number; onChange: () => void;
}) {
  const [counts, setCounts] = useState<{ facts: number | null; relations: number | null }>({ facts: null, relations: null });
  const [summary, setSummary] = useState<NormalizationSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    void Promise.allSettled([
      api.facts.list({ document_id: document.id, limit: "1" }),
      api.relations.list({ document_id: document.id, limit: "1" }),
    ]).then(([facts, relations]) => {
      if (active) setCounts({ facts: facts.status === "fulfilled" ? facts.value.total : null,
        relations: relations.status === "fulfilled" ? relations.value.total : null });
    });
    return () => { active = false; };
  }, [document.id, revision]);
  async function normalize() {
    setBusy(true); setError(null);
    try { setSummary(await api.documents.normalizeFacts(document.id)); onChange(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not normalize facts."); }
    finally { setBusy(false); }
  }
  const steps = [
    { title: "Upload", status: document.status === "PROCESSED" ? "Evidence available" : document.status.toLowerCase(),
      state: document.status === "FAILED" ? "error" : document.status === "PROCESSED" ? "complete" : "active", icon: Upload },
    { title: "Extract", status: counts.facts === null ? "Count unavailable" : `${counts.facts} saved facts`,
      state: (counts.facts ?? 0) > 0 ? "complete" : document.status === "PROCESSED" ? "active" : "pending", icon: ScanSearch },
    { title: "Normalize", status: summary ? `${summary.values_normalized} canonical values` : "Prepare values for comparison",
      state: summary ? "complete" : (counts.facts ?? 0) > 0 ? "active" : "pending", icon: WandSparkles },
    { title: "Compare", status: counts.relations === null ? "Count unavailable" : `${counts.relations} saved relationships`,
      state: (counts.relations ?? 0) > 0 ? "complete" : (counts.facts ?? 0) > 0 ? "active" : "pending", icon: GitCompareArrows },
  ];
  return <section className="panel workflow-panel" aria-label="Document workflow">
    <ol className="workflow-steps">{steps.map(({ title, status, state, icon: Icon }, index) => <li
      className={`workflow-step workflow-step--${state}`} key={title} aria-label={`${title}: ${status}`}>
      <span className="workflow-number" aria-hidden="true">{state === "complete" ? <Check size={13} /> : index + 1}</span>
      <div><strong><Icon className="workflow-icon" size={15} aria-hidden="true" />{title}</strong><small>{status}</small></div>
    </li>)}</ol>
    <div className="workflow-normalize"><p>Normalize stored facts before comparing sources. Comparison also refreshes normalization automatically.</p>
      <button type="button" className="button button--secondary" disabled={busy || counts.facts === 0 || counts.facts === null}
        onClick={() => void normalize()}><WandSparkles size={16} aria-hidden="true" />{busy ? "Normalizing…" : "Normalize facts"}</button>
    </div>
    {error && <p className="message message--error" role="alert">{error}</p>}
    {summary && <p className="message message--success" role="status">Normalization checked {summary.facts_total} facts; {summary.facts_changed} updated. {summary.facts_with_warnings} contain warnings to inspect.</p>}
  </section>;
}
