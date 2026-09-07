import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { FactRecord } from "../types/api";

export function FactDetailPage() {
  const { factId = "" } = useParams();
  const [fact, setFact] = useState<FactRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    setFact(null);
    setError(null);
    api.facts.get(factId).then(result => { if (active) setFact(result); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Could not load fact."); });
    return () => { active = false; };
  }, [factId]);
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
        <dl className="fact-fields">{Object.entries(fact).filter(([key]) =>
          !["evidence", "source_document"].includes(key)).map(([key, value]) =>
          <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value === null ? "—" :
            typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>
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
