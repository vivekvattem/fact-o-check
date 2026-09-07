import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
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
  return <div className="page">
    <Link className="back-link" to="/facts">← Back to facts</Link>
    {error ? <div className="message message--error" role="alert">{error}</div> : !fact ?
      <p>Loading fact…</p> : <>
        <header className="document-detail-header"><div><span className="eyebrow">Structured fact</span>
          <h1>{fact.subject}</h1><h2>{fact.predicate}: {String(fact.raw_value)}</h2></div></header>
        <p><Link to={`/documents/${fact.document_id}`}>
          {fact.source_document?.original_filename ?? "Source unavailable"}
        </Link> · Pages {fact.page_numbers.join(", ")} · Confidence {fact.extraction_confidence === null ?
          "unknown" : `${Math.round(fact.extraction_confidence * 100)}%`}</p>
        <button className="button button--primary" type="button" disabled={normalizing}
          onClick={() => void normalize()}>{normalizing ? "Normalizing…" : "Normalize fact"}</button>
        <dl className="fact-fields">
          <FactField label="Raw subject" value={fact.subject} />
          <FactField label="Canonical subject" value={fact.normalized_subject} />
          <FactField label="Raw predicate" value={fact.predicate} />
          <FactField label="Canonical predicate" value={fact.normalized_predicate} />
          <FactField label="Raw value" value={fact.raw_value} unit={fact.raw_unit} />
          <FactField label="Normalized value" value={fact.normalized_value}
            unit={fact.normalized_unit} />
          <FactField label="Period" value={fact.period_start || fact.period_end ?
            `${fact.period_start ?? "?"} → ${fact.period_end ?? "?"}` : null} />
          <FactField label="As of" value={fact.as_of_date} />
          <FactField label="Geography" value={fact.geography} />
          <FactField label="Scope" value={fact.scope} />
          <FactField label="Qualifiers" value={fact.qualifiers} />
        </dl>
        {normalization && <section className="normalization-notes">
          <h2>Normalization</h2>
          <p>Rules: {normalization.rules_applied?.join(", ") || "None applied"}</p>
          {normalization.warnings && normalization.warnings.length > 0 && <div
            className="message message--error" role="status">
            <strong>Normalization warnings</strong>
            <ul>{normalization.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>
          </div>}
        </section>}
        <section className="evidence-section"><h2>Supporting evidence</h2>
          <div className="evidence-list">{fact.evidence.map(chunk =>
            <article className="evidence-card" key={chunk.id}>
              <div className="evidence-card__meta">Page {chunk.page_number} · Block {chunk.block_index + 1}</div>
              <p>{chunk.text}</p>
            </article>)}</div>
        </section>
      </>}
  </div>;
}

function FactField({ label, value, unit }: {
  label: string; value: unknown; unit?: string | null;
}) {
  const display = value === null || value === undefined ? "—" :
    typeof value === "object" ? JSON.stringify(value) : String(value);
  return <div><dt>{label}</dt><dd>{display}{unit ? ` ${unit}` : ""}</dd></div>;
}
