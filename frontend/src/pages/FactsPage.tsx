import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { FactPage, FactRecord } from "../types/api";

function contextSummary(fact: FactRecord) {
  return [fact.period_start && `From ${fact.period_start}`, fact.period_end && `To ${fact.period_end}`,
    fact.as_of_date && `As of ${fact.as_of_date}`, fact.geography, fact.scope,
    ...Object.entries(fact.qualifiers).map(([key, value]) => `${key}: ${String(value)}`)]
    .filter(Boolean).join(" · ") || "—";
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
    <form className="fact-filters" key={query} onSubmit={event => {
      event.preventDefault();
      const values = new FormData(event.currentTarget);
      const updated = new URLSearchParams();
      for (const [key, value] of values) if (String(value).trim()) updated.set(key, String(value).trim());
      setParams(updated);
    }}>
      <label>Document ID<input name="document_id" defaultValue={params.get("document_id") ?? ""} /></label>
      <label>Subject (exact)<input name="subject" defaultValue={params.get("subject") ?? ""} /></label>
      <label>Predicate (exact)<input name="predicate" defaultValue={params.get("predicate") ?? ""} /></label>
      <label>Value type<select name="value_type" defaultValue={params.get("value_type") ?? ""}>
        <option value="">All types</option>
        {["NUMBER", "PERCENTAGE", "CURRENCY", "DATE", "BOOLEAN", "STRING", "ENTITY", "QUANTITY"].map(
          type => <option key={type}>{type}</option>)}
      </select></label>
      <button className="button button--primary" type="submit">Filter</button>
    </form>
    {error && <div className="message message--error" role="alert">{error}</div>}
    <section className="panel table-panel" aria-busy={loading}>
      {loading ? <div className="table-empty">Loading facts…</div> : !error && <>
        <div className="table-scroll"><table>
          <thead><tr>{["Subject", "Predicate", "Raw value", "Context", "Confidence", "Source"].map(
            name => <th key={name}>{name}</th>)}</tr></thead>
          <tbody>{data?.items.map(fact => <tr key={fact.id}>
            <td><Link to={`/facts/${fact.id}`}>{fact.subject}</Link></td>
            <td>{fact.predicate}</td><td>{String(fact.raw_value)}</td>
            <td>{contextSummary(fact)}</td>
            <td>{fact.extraction_confidence === null ? "—" : `${Math.round(fact.extraction_confidence * 100)}%`}</td>
            <td><Link to={`/documents/${fact.document_id}`}>
              {fact.source_document?.original_filename ?? "Source unavailable"}
            </Link><div>Pages {fact.page_numbers.join(", ") || "—"}</div></td>
          </tr>)}</tbody>
        </table></div>
        {data?.items.length === 0 && <div className="table-empty">
          <h2>No facts found</h2><p>Extract facts from a processed document or adjust your filters.</p>
          <Link to="/documents">Browse documents</Link>
        </div>}
        <div className="pagination"><span>{data?.total ?? 0} facts</span><div>
          <button className="button" disabled={offset === 0} onClick={() => move(Math.max(0, offset - 50))}>Previous</button>
          <button className="button" disabled={offset + 50 >= (data?.total ?? 0)} onClick={() => move(offset + 50)}>Next</button>
        </div></div>
      </>}
    </section>
  </div>;
}
