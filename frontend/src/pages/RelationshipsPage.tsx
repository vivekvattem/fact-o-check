import { GitCompareArrows } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import type { RelationPage, RelationRecord, RelationType } from "../types/api";

const filters: { label: string; type?: RelationType }[] = [
  { label: "All" },
  { label: "Corroborated", type: "CORROBORATES" },
  { label: "Contradictions", type: "CONTRADICTS" },
  { label: "Reconciled", type: "RECONCILABLE" },
  { label: "Needs Review", type: "NEEDS_REVIEW" },
];

const summaryTypes = filters.slice(1) as { label: string; type: RelationType }[];

export function RelationshipsPage() {
  const [params, setParams] = useSearchParams();
  const query = params.toString();
  const [data, setData] = useState<RelationPage | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeType = params.get("relation_type") as RelationType | null;
  const activeFilter = filters.find(filter => filter.type === activeType) ?? filters[0];

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const options = Object.fromEntries(new URLSearchParams(query));
    Promise.all([
      api.relations.list(options),
      ...summaryTypes.map(item => api.relations.list({ relation_type: item.type, limit: "1" })),
    ]).then(([relations, ...summaries]) => {
      if (!active) return;
      setData(relations);
      setCounts(Object.fromEntries(
        summaryTypes.map((item, index) => [item.type, summaries[index].total]),
      ));
    }).catch(reason => {
      if (active) setError(
        reason instanceof Error ? reason.message : "Could not load relationships.",
      );
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [query]);

  const sourceFilter = params.get("document_id");
  const cards = useMemo(
    () => summaryTypes.map(item => ({ ...item, count: counts[item.type] ?? 0 })),
    [counts],
  );

  function selectFilter(type?: RelationType) {
    const updated = new URLSearchParams(params);
    if (type) updated.set("relation_type", type);
    else updated.delete("relation_type");
    updated.delete("offset");
    setParams(updated);
  }

  return <div className="page">
    <PageHeader eyebrow="Cross-document analysis" title="Relationships"
      description="Review where facts agree, conflict, or differ because of explicit context." />

    <section className="relationship-summary" aria-label="Relationship totals">
      {cards.map(card => <div className="panel relationship-metric" key={card.type}>
        <span>{card.label}</span><strong>{loading ? "—" : card.count}</strong>
      </div>)}
    </section>

    <div className="relationship-toolbar">
      <div className="tabs" role="tablist" aria-label="Relationship filters">
        {filters.map(filter => <button key={filter.label} type="button" role="tab"
          aria-selected={activeFilter.label === filter.label}
          className={activeFilter.label === filter.label ? "tab tab--active" : "tab"}
          onClick={() => selectFilter(filter.type)}>{filter.label}</button>)}
      </div>
      {sourceFilter && <button type="button" className="button button--ghost"
        onClick={() => {
          const next = new URLSearchParams(params);
          next.delete("document_id");
          setParams(next);
        }}>Clear document filter</button>}
    </div>

    {error && <div className="message message--error" role="alert">{error}</div>}
    <section
      className={`panel relationship-panel ${!loading && !data?.items.length ? "panel--empty" : ""}`}
      aria-busy={loading}
    >
      {loading ? <LoadingState label="Loading relationships…" /> :
        !error && data?.items.length ? <div className="relationship-list">
          {data.items.map(relation => <RelationCard relation={relation} key={relation.id} />)}
        </div> : !error && <EmptyState icon={GitCompareArrows}
          title="No relationships have been generated yet"
          description="Compare normalized facts from a document to create evidence-grounded relationships." />}
    </section>
  </div>;
}

function RelationCard({ relation }: { relation: RelationRecord }) {
  return <article className="relationship-card">
    <div className="relationship-card__heading">
      <div><span className="eyebrow">{relation.fact_a.subject}</span>
        <h2>{relation.fact_a.predicate}</h2></div>
      <RelationBadge type={relation.relation_type} />
    </div>
    <div className="relationship-values" aria-label="Compared values">
      <FactValue label="Fact A" fact={relation.fact_a} />
      <span className="relationship-versus" aria-hidden="true">vs</span>
      <FactValue label="Fact B" fact={relation.fact_b} />
    </div>
    <p className="relationship-explanation">
      {relation.explanation ?? "No explanation available."}
    </p>
    <footer>
      <span>{relation.confidence === null ? "Unknown" :
        `${Math.round(relation.confidence * 100)}%`} confidence</span>
      <Link to={`/relationships/${relation.id}`}>Inspect comparison</Link>
    </footer>
  </article>;
}

function FactValue({ label, fact }: { label: string; fact: RelationRecord["fact_a"] }) {
  return <div><span>{label}</span>
    <strong>{String(fact.raw_value)}{fact.raw_unit ? ` ${fact.raw_unit}` : ""}</strong>
    <small>{fact.source_document?.original_filename ?? "Unknown source"} · Page
      {fact.page_numbers.length === 1 ? "" : "s"} {fact.page_numbers.join(", ") || "—"}</small>
  </div>;
}

export function RelationBadge({ type }: { type: RelationType }) {
  return <span className={`relation-badge relation-badge--${type.toLowerCase()}`}>
    {type.replace("_", " ")}
  </span>;
}
