import {
  ArrowRight,
  Database,
  GitCompareArrows,
  ClipboardCheck,
  Files,
  ScanSearch,
  Server,
  Upload,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { DocumentRecord } from "../types/api";

type ConnectionState = "checking" | "connected" | "unavailable";

export function OverviewPage() {
  const [apiStatus, setApiStatus] = useState<ConnectionState>("checking");
  const [databaseStatus, setDatabaseStatus] = useState<ConnectionState>("checking");
  const [documentCount, setDocumentCount] = useState<number | null>(null);
  const [factCount, setFactCount] = useState<number | null>(null);
  const [relationCount, setRelationCount] = useState<number | null>(null);
  const [breakdown, setBreakdown] = useState<(number | null)[]>([null, null, null, null]);
  const [recentDocuments, setRecentDocuments] = useState<DocumentRecord[]>([]);

  useEffect(() => {
    let active = true;

    async function checkConnections() {
      const healthResult = await Promise.allSettled([
        api.health(),
        api.ready(),
        api.documents.list(),
        api.facts.list({ limit: "1" }),
        api.relations.list({ limit: "1" }),
        ...["CORROBORATES", "RECONCILABLE", "CONTRADICTS", "NEEDS_REVIEW"].map(
          relation_type => api.relations.list({ relation_type, limit: "1" }),
        ),
      ]);
      if (!active) return;
      setApiStatus(healthResult[0].status === "fulfilled" ? "connected" : "unavailable");
      setDatabaseStatus(healthResult[1].status === "fulfilled" ? "connected" : "unavailable");
      if (healthResult[2].status === "fulfilled") {
        setDocumentCount(healthResult[2].value.length);
        setRecentDocuments(healthResult[2].value.slice(0, 3));
      }
      if (healthResult[3].status === "fulfilled") setFactCount(healthResult[3].value.total);
      if (healthResult[4].status === "fulfilled") setRelationCount(healthResult[4].value.total);
      setBreakdown(healthResult.slice(5).map(result =>
        result.status === "fulfilled" && "total" in result.value ? result.value.total : null));
    }

    void checkConnections();
    return () => {
      active = false;
    };
  }, []);

  const systemStatus = [apiStatus, databaseStatus].includes("unavailable") ? "error" :
    [apiStatus, databaseStatus].includes("checking") ? "checking" : "ok";
  const metrics = [
    { label: "Documents", value: documentCount, icon: Files, hint: "Sources in your library" },
    { label: "Facts", value: factCount, icon: ScanSearch, hint: "Extracted knowledge records" },
    { label: "Relationships", value: relationCount, icon: GitCompareArrows, hint: "Persisted comparisons" },
    { label: "Needs Review", value: breakdown[3], icon: ClipboardCheck, hint: "Comparisons needing context" },
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow="Knowledge workspace"
        title="Overview"
        description="A grounded view of every fact, its evidence, and how it relates across documents."
      />

      <section className="metrics-grid" aria-label="Knowledge metrics">
        {metrics.map(({ label, value, icon: Icon, hint }) => (
          <article className="metric-card" key={label}>
            <div className="metric-card__icon">
              <Icon size={18} strokeWidth={1.8} />
            </div>
            <div className="metric-card__copy"><span>{label}</span><small>{hint}</small></div>
            <strong>{value ?? "—"}</strong>
          </article>
        ))}
      </section>

      <section className="overview-grid">
        <article className="panel status-panel">
          <div className="panel__header">
            <div>
              <span className="eyebrow">System status</span>
              <h2>Connections</h2>
            </div>
            <span className={`status-dot status-dot--${systemStatus}`}
              aria-label={systemStatus === "error" ? "Connection issue" : systemStatus === "checking" ? "Checking connections" : "Systems available"} />
          </div>
          <StatusRow icon={Server} label="Backend API" status={apiStatus} />
          <StatusRow icon={Database} label="MongoDB" status={databaseStatus} />
          <div className="readiness-note"><strong>Extraction & reasoning</strong>
            <span>Provider availability is checked when you run an action.</span></div>
        </article>

        <article className="panel principles-panel">
          <span className="eyebrow">Core principle</span>
          <blockquote>“Facts, not text chunks, are the primary unit of knowledge.”</blockquote>
          <p>Every fact retains a direct reference to the exact evidence it came from.</p>
        </article>
      </section>
      <section className="panel overview-relations" aria-label="Relationship breakdown">
        <div className="section-heading"><div><span className="eyebrow">Across your sources</span>
          <h2>Agreements, differences, and open questions</h2></div></div>
        <div className="relationship-summary">
          {["Corroborated", "Reconciled", "Contradictions", "Needs Review"].map((label, index) =>
            <Link className="relationship-metric" key={label}
              to={`/relationships?relation_type=${["CORROBORATES", "RECONCILABLE", "CONTRADICTS", "NEEDS_REVIEW"][index]}`}>
              <span>{label}</span><strong>{breakdown[index] ?? "—"}</strong>
            </Link>)}
        </div>
        <p className="muted-copy">Counts reflect saved comparisons. A missing count means the data could not be loaded.</p>
      </section>
      <section className="overview-lower-grid" aria-label="Workspace activity and next actions">
        <article className="overview-recent">
          <div className="section-heading"><div><span className="eyebrow">Latest sources</span>
            <h2>Recent documents</h2></div><Link to="/documents">View all</Link></div>
          {recentDocuments.length ? <div className="recent-document-list">
            {recentDocuments.map(document => <Link to={`/documents/${document.id}`} key={document.id}>
              <span className="document-icon"><Files size={16} /></span>
              <span><strong>{document.original_filename}</strong>
                <small>{document.page_count ?? "—"} pages · {document.evidence_chunk_count} evidence blocks</small></span>
              <ArrowRight size={15} aria-hidden="true" />
            </Link>)}
          </div> : <p className="overview-inline-empty">No source documents yet.</p>}
        </article>
        <aside className="overview-next">
          <span className="eyebrow">Next action</span>
          <h2>{recentDocuments.length ? "Continue your review" : "Add your first source"}</h2>
          <p>{recentDocuments.length
            ? "Inspect extracted evidence or open relationships that need context."
            : "Upload a PDF to begin building an evidence-backed fact layer."}</p>
          <div>
            <Link className="button button--primary" to="/documents"><Upload size={15} />
              {recentDocuments.length ? "Open documents" : "Upload a PDF"}</Link>
            {recentDocuments.length > 0 && <Link className="button button--secondary" to="/relationships?relation_type=NEEDS_REVIEW">Review relations</Link>}
          </div>
        </aside>
      </section>
    </div>
  );
}

interface StatusRowProps {
  icon: typeof Server;
  label: string;
  status: ConnectionState;
}

function StatusRow({ icon: Icon, label, status }: StatusRowProps) {
  const text =
    status === "checking"
      ? "Checking…"
      : status === "connected"
        ? `${label === "Backend API" ? "API" : "Database"} connected`
        : label === "Backend API"
          ? "Backend unavailable"
          : "Database unavailable";

  return (
    <div className="status-row">
      <div className="status-row__label">
        <Icon size={18} strokeWidth={1.8} />
        <span>{label}</span>
      </div>
      <span className={`connection connection--${status}`}>
        <i />
        {text}
      </span>
    </div>
  );
}
