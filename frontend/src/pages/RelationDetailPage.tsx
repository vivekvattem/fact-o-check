import { ArrowLeft, Box } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import { LoadingState } from "../components/LoadingState";
import { ContextDetails } from "../components/ContextDetails";
import type { FactRecord, RelationRecord } from "../types/api";
import { RelationBadge } from "./RelationshipsPage";

export function RelationDetailPage() {
  const { relationId = "" } = useParams();
  const [relation, setRelation] = useState<RelationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setRelation(null);
    setError(null);
    api.relations.get(relationId).then(result => { if (active) setRelation(result); })
      .catch(reason => {
        if (active) setError(
          reason instanceof Error ? reason.message : "Could not load relationship.",
        );
      });
    return () => { active = false; };
  }, [relationId]);

  if (!relation && !error) {
    return <div className="page detail-loading">
      <LoadingState label="Loading relationship…" />
    </div>;
  }
  return <div className="page relation-detail">
    <Link className="back-link" to="/relationships">
      <ArrowLeft size={16} /> Back to relationships
    </Link>
    {error && <div className="message message--error" role="alert">{error}</div>}
    {relation && <>
      <header className="relation-detail__header">
        <div><span className="eyebrow">Cross-document comparison</span>
          <h1>{relation.fact_a.subject}</h1><p>{relation.fact_a.predicate}</p></div>
      </header>
      <section className="relation-comparison-workspace" aria-label="Compared facts and relationship">
        <FactPanel label="Fact A" fact={relation.fact_a} />
        <aside className="relation-center" aria-labelledby="relation-heading">
          <span className="relation-center__line" aria-hidden="true" />
          <span className="eyebrow">Assessment</span>
          <h2 id="relation-heading"><RelationBadge type={relation.relation_type} /></h2>
          <strong>{relation.confidence === null ? "Unknown" :
            `${Math.round(relation.confidence * 100)}%`} confidence</strong>
          <p>{relation.explanation ?? "No explanation available."}</p>
        </aside>
        <FactPanel label="Fact B" fact={relation.fact_b} />
      </section>
      <section className="panel fact-section relation-decision" aria-labelledby="checks-heading">
        <div className="section-heading"><div><span className="eyebrow">Evidence-based assessment</span>
          <h2 id="checks-heading">Comparison checks</h2></div></div>
        {relation.relation_type === "NEEDS_REVIEW" && <aside className="review-guidance">
          <strong>A closer look is needed</strong>
          <p>Check each source’s metric label, period, geography, and scope. Missing context may explain the difference.</p>
          {relation.reasoning_details.needs_review_reason != null && <ContextDetails value={relation.reasoning_details.needs_review_reason} />}
        </aside>}
        <div className="reasoning-grid">
          <section><h3>Context compatibility</h3><ContextDetails value={relation.reasoning_details.context} /></section>
          <section><h3>Value comparison</h3><ContextDetails value={relation.reasoning_details.value_comparison} /></section>
        </div>
        <details className="reasoning-disclosure"><summary>All comparison checks</summary>
          <ContextDetails value={relation.reasoning_details} />
        </details>
      </section>
    </>}
  </div>;
}

function FactPanel({ label, fact }: { label: string; fact: FactRecord }) {
  return <article className="panel fact-section relation-fact">
    <span className="eyebrow">{label}</span><h2>{fact.subject}</h2>
    <p className="relation-fact__predicate">{fact.predicate}</p>
    <dl className="detail-list">
      <Field label="Raw value" value={`${String(fact.raw_value)}${fact.raw_unit ? ` ${fact.raw_unit}` : ""}`} />
      <Field label="Normalized" value={fact.normalized_value === null ? null :
        `${String(fact.normalized_value)} ${fact.normalized_unit ?? ""}`} />
      <Field label="Period" value={fact.period_start || fact.period_end ?
        `${fact.period_start ?? "?"} → ${fact.period_end ?? "?"}` : null} />
      <Field label="As of" value={fact.as_of_date} />
      <Field label="Geography" value={fact.geography} />
      <Field label="Scope" value={fact.scope} />
      <div><dt>Source</dt><dd><Link to={`/documents/${fact.document_id}`}>{fact.source_document?.original_filename ?? "Inspect source document"}</Link></dd></div>
      <Field label="Pages" value={fact.page_numbers.join(", ") || null} />
    </dl>
    <Link className="relation-fact__link" to={`/facts/${fact.id}`}>Inspect full fact &amp; context</Link>
    <div className="relation-evidence"><h3>Evidence</h3>
      <p className="muted-copy">Linked source text · inspect labels and context to verify the claim.</p>
      {fact.evidence.length === 0 && <p className="muted-copy">No source evidence is available for this fact.</p>}
      {fact.evidence.map(chunk => <blockquote key={chunk.id}>
        <span>Page {chunk.page_number} · Block {chunk.block_index + 1}
          {chunk.bbox && <> · <Box size={10} aria-hidden="true" /> spatial provenance</>}</span>{chunk.text}
      </blockquote>)}
    </div>
  </article>;
}

function Field({ label, value }: { label: string; value: unknown }) {
  return <div><dt>{label}</dt><dd>{display(value)}</dd></div>;
}

function display(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
