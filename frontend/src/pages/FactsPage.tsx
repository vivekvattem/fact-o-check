import { ScanSearch } from "lucide-react";

import { PageHeader } from "../components/PageHeader";

const columns = ["Subject", "Predicate", "Value", "Context", "Confidence", "Source"];

export function FactsPage() {
  return (
    <div className="page">
      <PageHeader
        eyebrow="Knowledge layer"
        title="Facts"
        description="Browse structured claims alongside their original evidence and contextual qualifiers."
      />
      <section className="panel table-panel">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
          </table>
        </div>
        <div className="table-empty">
          <div className="empty-state__icon" aria-hidden="true">
            <ScanSearch size={22} strokeWidth={1.8} />
          </div>
          <h2>No facts extracted</h2>
          <p>Structured facts will appear here once document processing is available.</p>
        </div>
      </section>
    </div>
  );
}

