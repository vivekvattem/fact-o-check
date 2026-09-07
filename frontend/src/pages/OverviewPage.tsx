import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Files,
  GitMerge,
  ScanSearch,
  Server,
  ShieldQuestion,
} from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type ConnectionState = "checking" | "connected" | "unavailable";

const metrics = [
  { label: "Documents", value: 0, icon: Files, tone: "neutral" },
  { label: "Facts", value: 0, icon: ScanSearch, tone: "neutral" },
  { label: "Corroborated", value: 0, icon: CheckCircle2, tone: "positive" },
  { label: "Contradictions", value: 0, icon: AlertTriangle, tone: "negative" },
  { label: "Reconciled", value: 0, icon: GitMerge, tone: "info" },
  { label: "Needs review", value: 0, icon: ShieldQuestion, tone: "warning" },
] as const;

export function OverviewPage() {
  const [apiStatus, setApiStatus] = useState<ConnectionState>("checking");
  const [databaseStatus, setDatabaseStatus] = useState<ConnectionState>("checking");

  useEffect(() => {
    let active = true;

    async function checkConnections() {
      const healthResult = await Promise.allSettled([api.health(), api.ready()]);
      if (!active) return;
      setApiStatus(healthResult[0].status === "fulfilled" ? "connected" : "unavailable");
      setDatabaseStatus(healthResult[1].status === "fulfilled" ? "connected" : "unavailable");
    }

    void checkConnections();
    return () => {
      active = false;
    };
  }, []);

  const backendUnavailable = apiStatus === "unavailable";

  return (
    <div className="page">
      <PageHeader
        eyebrow="Knowledge workspace"
        title="Overview"
        description="A grounded view of every fact, its evidence, and how it relates across documents."
      />

      <section className="metrics-grid" aria-label="Knowledge metrics">
        {metrics.map(({ label, value, icon: Icon, tone }) => (
          <article className="metric-card" key={label}>
            <div className={`metric-card__icon metric-card__icon--${tone}`}>
              <Icon size={18} strokeWidth={1.8} />
            </div>
            <span>{label}</span>
            <strong>{value}</strong>
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
            <span className={`status-dot status-dot--${backendUnavailable ? "error" : "ok"}`} />
          </div>
          <StatusRow icon={Server} label="Backend API" status={apiStatus} />
          <StatusRow icon={Database} label="MongoDB" status={databaseStatus} />
        </article>

        <article className="panel principles-panel">
          <span className="eyebrow">Core principle</span>
          <blockquote>“Facts, not text chunks, are the primary unit of knowledge.”</blockquote>
          <p>Every future fact will retain a direct reference to the exact evidence it came from.</p>
        </article>
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

