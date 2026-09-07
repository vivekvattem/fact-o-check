import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import { LoadingState } from "../components/LoadingState";
import type { FactRecord, RelationRecord } from "../types/api";
import { RelationBadge } from "./RelationshipsPage";

export function RelationDetailPage() {
  const { relationId = "" } = useParams();
  const [relation, setRelation] = useState<RelationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
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
        <RelationBadge type={relation.relation_type} />
      </header>
      <section className="relation-facts" aria-label="Compared facts">
        <FactPanel label="Fact A" fact={relation.fact_a} />
        <FactPanel label="Fact B" fact={relation.fact_b} />
      </section>
      <section className="panel fact-section relation-decision" aria-labelledby="relation-heading">
        <div className="section-heading"><div><span className="eyebrow">Decision</span>
          <h2 id="relation-heading">Relation</h2></div>
          <strong>{relation.confidence === null ? "Unknown" :
            `${Math.round(relation.confidence * 100)}%`} confidence</strong></div>
        <p>{relation.explanation ?? "No explanation available."}</p>
        <dl className="reasoning-grid">
          {Object.entries(relation.reasoning_details).map(([key, value]) => <div key={key}>
            <dt>{key.replaceAll("_", " ")}</dt><dd>{display(value)}</dd>
          </div>)}
        </dl>
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
      <Field label="Source" value={fact.source_document?.original_filename} />
      <Field label="Pages" value={fact.page_numbers.join(", ") || null} />
    </dl>
    <div className="relation-evidence"><h3>Evidence</h3>
      {fact.evidence.map(chunk => <blockquote key={chunk.id}>
        <span>Page {chunk.page_number}</span>{chunk.text}
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
