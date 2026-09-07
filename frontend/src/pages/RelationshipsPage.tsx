import { GitCompareArrows } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

const filters = ["All", "Corroborated", "Contradictions", "Reconciled", "Needs Review"];

export function RelationshipsPage() {
  const [activeFilter, setActiveFilter] = useState("All");

  return (
    <div className="page">
      <PageHeader
        eyebrow="Cross-document analysis"
        title="Relationships"
        description="Review where facts agree, conflict, or differ because of context such as period, scope, or unit."
      />
      <div className="tabs" role="tablist" aria-label="Relationship filters">
        {filters.map((filter) => (
          <button
            key={filter}
            type="button"
            role="tab"
            aria-selected={activeFilter === filter}
            className={activeFilter === filter ? "tab tab--active" : "tab"}
            onClick={() => setActiveFilter(filter)}
          >
            {filter}
          </button>
        ))}
      </div>
      <section className="panel panel--empty">
        <EmptyState
          icon={GitCompareArrows}
          title="No relationships to review"
          description="Fact comparisons and their evidence-grounded explanations will appear here in a later phase."
        />
      </section>
    </div>
  );
}

