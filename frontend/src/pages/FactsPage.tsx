import { ScanSearch } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import type { FactPage, FactRecord } from "../types/api";

function contextItems(fact: FactRecord) {
  return [
    fact.period_start && fact.period_end ? `${fact.period_start} → ${fact.period_end}` :
      fact.period_start ? `From ${fact.period_start}` : fact.period_end ? `To ${fact.period_end}` : null,
    fact.as_of_date && `As of ${fact.as_of_date}`,
    fact.geography,
    fact.scope,
    ...Object.entries(fact.qualifiers).map(([key, value]) => `${key}: ${String(value)}`),
  ].filter((item): item is string => Boolean(item));
}

export function FactsPage() {
  const [params, setParams] = useSearchParams();
  const query = params.toString();
  const [data, setData] = useState<FactPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const offset = Number(params.get("offset") ?? 0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api.facts.list(Object.fromEntries(new URLSearchParams(query)))
      .then(result => { if (active) setData(result); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Could not load facts."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [query]);

  function move(next: number) {
    const updated = new URLSearchParams(params);
    updated.set("offset", String(next));
    setParams(updated);
  }

  return <div className="page">
    <PageHeader eyebrow="Knowledge layer" title="Facts"
      description="Structured claims with original evidence and contextual qualifiers." />
    <form className="fact-filters panel" key={query} aria-label="Filter facts" onSubmit={event => {
      event.preventDefault();
      const values = new FormData(event.currentTarget);
      const updated = new URLSearchParams();
      for (const [key, value] of values) if (String(value).trim()) updated.set(key, String(value).trim());
      setParams(updated);
    }}>
      <label>Document ID<input className="input--mono" name="document_id"
        defaultValue={params.get("document_id") ?? ""} /></label>
      <label>Subject (exact)<input name="subject" defaultValue={params.get("subject") ?? ""} /></label>
      <label>Predicate (exact)<input name="predicate" defaultValue={params.get("predicate") ?? ""} /></label>
      <label>Value type<select name="value_type" defaultValue={params.get("value_type") ?? ""}>
        <option value="">All types</option>
        {["NUMBER", "PERCENTAGE", "CURRENCY", "DATE", "BOOLEAN", "STRING", "ENTITY", "QUANTITY"].map(
          type => <option key={type}>{type}</option>)}
      </select></label>
      <button className="button button--primary" type="submit">Filter</button>
      {query && <button className="button button--ghost" type="button"
        onClick={() => setParams(new URLSearchParams())}>Clear</button>}
    </form>
    {error && <div className="message message--error" role="alert">{error}</div>}
    <section className="panel table-panel" aria-busy={loading}>
      {loading ? <LoadingState label="Loading facts…" /> : !error && <>
        <div className="table-scroll"><table className="facts-table">
          <caption className="visually-hidden">Extracted structured facts</caption>
          <thead><tr>{["Fact", "Value", "Context", "Confidence", "Source"].map(
            name => <th scope="col" key={name}>{name}</th>)}</tr></thead>
          <tbody>{data?.items.map(fact => <tr key={fact.id}>
            <td data-label="Fact"><Link className="fact-link" to={`/facts/${fact.id}`}>
              <strong>{fact.subject}</strong><span>{fact.predicate}</span>
            </Link></td>
            <td data-label="Value"><div className="fact-value">
              <strong>{String(fact.raw_value)}{fact.raw_unit ? ` ${fact.raw_unit}` : ""}</strong>
              {fact.normalized_value !== null && <span>
                {String(fact.normalized_value)} {fact.normalized_unit}
              </span>}
            </div></td>
            <td data-label="Context"><div className="context-list">{contextItems(fact).length ?
              contextItems(fact).slice(0, 3).map((item, index) =>
                <span key={`${item}-${index}`}>{item}</span>) :
              <span className="context-empty">No added context</span>}</div></td>
            <td data-label="Confidence"><ConfidenceBadge value={fact.extraction_confidence} /></td>
            <td data-label="Source"><div className="source-cell"><Link to={`/documents/${fact.document_id}`}>
              {fact.source_document?.original_filename ?? "Source unavailable"}
            </Link><span>Page{fact.page_numbers.length === 1 ? "" : "s"} {fact.page_numbers.join(", ") || "—"}</span>
            </div></td>
          </tr>)}</tbody>
        </table></div>
        {data?.items.length === 0 && <EmptyState icon={ScanSearch} title="No facts found"
          description="Extract facts from a processed document or adjust the current filters."
          action={<Link className="button button--secondary" to="/documents">Browse documents</Link>} />}
        {(data?.total ?? 0) > 0 && <nav className="pagination table-pagination" aria-label="Facts pagination">
          <span>Showing {offset + 1}–{Math.min(offset + (data?.items.length ?? 0), data?.total ?? 0)} of {data?.total ?? 0}</span><div>
          <button type="button" className="button button--secondary" aria-label="Previous facts page"
            disabled={offset === 0} onClick={() => move(Math.max(0, offset - 50))}>Previous</button>
          <button type="button" className="button button--secondary" aria-label="Next facts page"
            disabled={offset + 50 >= (data?.total ?? 0)} onClick={() => move(offset + 50)}>Next</button>
        </div></nav>}
      </>}
    </section>
  </div>;
}

function ConfidenceBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="confidence confidence--unknown">Unknown</span>;
  const tone = value >= 0.8 ? "high" : value >= 0.55 ? "medium" : "low";
  return <span className={`confidence confidence--${tone}`} aria-label={`${Math.round(value * 100)} percent confidence`}>
    {Math.round(value * 100)}%
  </span>;
}
