import { FileUp, Upload } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function DocumentsPage() {
  const uploadButton = (
    <button className="button button--primary" type="button">
      <Upload size={17} />
      Upload PDF
    </button>
  );

  return (
    <div className="page">
      <PageHeader
        eyebrow="Source library"
        title="Documents"
        description="Manage the source PDFs that form your evidence-backed knowledge base."
        action={uploadButton}
      />
      <section className="panel panel--empty">
        <EmptyState
          icon={FileUp}
          title="No documents yet"
          description="Upload your first PDF to begin building an evidence-grounded fact layer. Ingestion arrives in Phase 1."
          action={uploadButton}
        />
      </section>
    </div>
  );
}

