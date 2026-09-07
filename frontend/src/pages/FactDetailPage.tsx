import { AlertTriangle, ArrowLeft, CheckCircle2, FileText, WandSparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import { LoadingState } from "../components/LoadingState";
import type { FactRecord } from "../types/api";

export function FactDetailPage() {
  const { factId = "" } = useParams();
  const [fact, setFact] = useState<FactRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [normalizing, setNormalizing] = useState(false);
  useEffect(() => {
    let active = true;
    setFact(null);
    setError(null);
    api.facts.get(factId).then(result => { if (active) setFact(result); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Could not load fact."); });
    return () => { active = false; };
  }, [factId]);
  const normalization = fact?.metadata.normalization as {
    rules_applied?: string[]; warnings?: string[];
  } | undefined;
  async function normalize() {
    setNormalizing(true);
    setError(null);
    try {
      setFact(await api.facts.normalize(factId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not normalize fact.");
    } finally {
      setNormalizing(false);
    }
  }
  if (!fact && !error) return <div className="page detail-loading"><LoadingState label="Loading fact…" /></div>;

  return <div className="page fact-detail">
    <Link className="back-link" to="/facts"><ArrowLeft size={16} /> Back to facts</Link>
    {error && <div className="message message--error" role="alert">{error}</div>}
    {fact && <>
      <header className="fact-detail__header">
        <div><span className="eyebrow">Structured fact</span><h1>{fact.subject}</h1>
          <p>{fact.predicate}</p></div>
        <button className="button button--primary" type="button" disabled={normalizing}
          onClick={() => void normalize()}><WandSparkles size={16} aria-hidden="true" />
          {normalizing ? "Normalizing…" : "Normalize fact"}</button>
      </header>

      <section className="fact-detail__grid" aria-label="Raw and normalized fact">
        <article className="panel fact-section">
          <div className="section-heading"><div><span className="eyebrow">Original extraction</span>
            <h2>Raw Fact</h2></div></div>
          <dl className="detail-list">
            <FactField label="Subject" value={fact.subject} />
            <FactField label="Predicate" value={fact.predicate} />
            <FactField label="Value" value={fact.raw_value} unit={fact.raw_unit} emphasis />
            <FactField label="Value type" value={fact.value_type} />
          </dl>
        </article>
        <article className="panel fact-section fact-section--normalized">
          <div className="section-heading"><div><span className="eyebrow">Canonical representation</span>
            <h2>Normalized Fact</h2></div>{fact.normalized_value !== null &&
              <CheckCircle2 size={18} className="normalized-check" aria-label="Normalized" />}</div>
          <dl className="detail-list">
            <FactField label="Subject" value={fact.normalized_subject} />
            <FactField label="Predicate" value={fact.normalized_predicate} />
            <FactField label="Value" value={fact.normalized_value}
              unit={fact.normalized_unit} emphasis />
          </dl>
          {fact.normalized_value === null && <p className="muted-copy">No canonical value is stored yet.</p>}
        </article>
      </section>

      {normalization && <section className="normalization-notes" aria-labelledby="normalization-heading">
        <h2 id="normalization-heading">Normalization details</h2>
        <div className="rule-list">{normalization.rules_applied?.map(rule =>
          <span className="rule-chip" key={rule}>{rule.replaceAll("_", " ")}</span>)}</div>
        {normalization.warnings && normalization.warnings.length > 0 && <div
          className="message message--warning normalization-warning" role="status">
          <AlertTriangle size={17} aria-hidden="true" /><div><strong>Review normalization</strong>
          <ul>{normalization.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></div>
        </div>}
      </section>}

      <section className="panel fact-section" aria-labelledby="context-heading">
        <div className="section-heading"><div><span className="eyebrow">Dimensions</span>
          <h2 id="context-heading">Context</h2></div></div>
        <dl className="context-grid">
          <FactField label="Period" value={fact.period_start || fact.period_end ?
            `${fact.period_start ?? "?"} → ${fact.period_end ?? "?"}` : null} />
          <FactField label="As of" value={fact.as_of_date} />
          <FactField label="Geography" value={fact.geography} />
          <FactField label="Scope" value={fact.scope} />
          <FactField label="Qualifiers" value={fact.qualifiers} />
          <FactField label="Confidence" value={fact.extraction_confidence === null ? null :
            `${Math.round(fact.extraction_confidence * 100)}%`} />
        </dl>
      </section>

      <section className="panel source-panel" aria-labelledby="source-heading">
        <div className="source-panel__icon" aria-hidden="true"><FileText size={20} /></div>
        <div><span className="eyebrow">Provenance</span><h2 id="source-heading">Source</h2>
          <Link to={`/documents/${fact.document_id}`}>
            {fact.source_document?.original_filename ?? "Source unavailable"}
          </Link><p>Page{fact.page_numbers.length === 1 ? "" : "s"} {fact.page_numbers.join(", ") || "—"}</p>
        </div>
      </section>

      <section className="evidence-section detail-section" aria-labelledby="fact-evidence-heading">
        <div className="section-heading"><div><span className="eyebrow">Verifiable provenance</span>
          <h2 id="fact-evidence-heading">Evidence</h2></div>
          <span className="count-badge">{fact.evidence.length} block{fact.evidence.length === 1 ? "" : "s"}</span>
        </div>
        <div className="evidence-list">{fact.evidence.map(chunk =>
          <article className="evidence-card" key={chunk.id}>
            <div className="evidence-card__meta"><span>Page {chunk.page_number}</span>
              <span>Block {chunk.block_index + 1}</span></div><p>{chunk.text}</p>
          </article>)}</div>
      </section>
    </>}
  </div>;
}

function FactField({ label, value, unit, emphasis }: {
  label: string; value: unknown; unit?: string | null; emphasis?: boolean;
}) {
  const display = value === null || value === undefined ? "—" :
    typeof value === "object" ? JSON.stringify(value) : String(value);
  return <div><dt>{label}</dt><dd className={emphasis ? "detail-value--emphasis" : undefined}>
    {display}{unit ? ` ${unit}` : ""}</dd></div>;
}
