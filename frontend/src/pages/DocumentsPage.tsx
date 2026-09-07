import { AlertCircle, FileText, FileUp, Info, LoaderCircle, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import type { DocumentRecord } from "../types/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function uploadErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.name === "AbortError") return "The upload timed out.";
  return "The PDF could not be uploaded. Check the backend connection and try again.";
}

export function DocumentsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [duplicateNotice, setDuplicateNotice] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      setDocuments(await api.documents.list());
      setError(null);
    } catch {
      setError("Documents are unavailable. Check the backend connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  async function uploadFile(file: File) {
    setError(null);
    setNotice(null);
    setDuplicateNotice(false);

    if (file.size === 0) {
      setError("Choose a PDF that is not empty.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files can be uploaded.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    setUploading(true);
    try {
      const result = await api.documents.upload(file);
      setNotice(
        result.already_existed
          ? "This PDF already exists. Its original evidence was preserved."
          : `${result.document.original_filename} was processed successfully.`,
      );
      setDuplicateNotice(result.already_existed);
      await loadDocuments();
    } catch (uploadError) {
      setError(uploadErrorMessage(uploadError));
      await loadDocuments();
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const uploadButton = (
    <button
      className="button button--primary"
      type="button"
      disabled={uploading}
      onClick={() => inputRef.current?.click()}
    >
      {uploading ? <LoaderCircle className="spin" size={17} /> : <Upload size={17} />}
      {uploading ? "Processing PDF…" : "Upload PDF"}
    </button>
  );

  return (
    <div className="page">
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept="application/pdf,.pdf"
        aria-label="Choose a PDF to upload"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void uploadFile(file);
        }}
      />
      <PageHeader
        eyebrow="Source library"
        title="Documents"
        description="Upload PDFs and inspect the page-level evidence preserved for every source."
      />

      <section className="upload-panel panel" aria-labelledby="upload-heading">
        <div className="upload-panel__icon" aria-hidden="true"><FileUp size={22} /></div>
        <div className="upload-panel__copy">
          <h2 id="upload-heading">Add a source document</h2>
          <p>Upload a PDF to preserve ordered text evidence with page-level provenance.</p>
        </div>
        {uploadButton}
      </section>

      {error && (
        <div className="message message--error" role="alert">
          <AlertCircle size={17} />
          {error}
        </div>
      )}
      {notice && <div className={`message ${duplicateNotice ? "message--info" : "message--success"}`}
        role="status">
        <Info size={17} aria-hidden="true" />{notice}
      </div>}

      {loading ? (
        <section className="panel loading-panel"><LoadingState label="Loading documents…" /></section>
      ) : documents.length === 0 ? (
        <section className="panel panel--empty">
          <EmptyState
            icon={FileUp}
            title="No documents yet"
            description="Upload your first PDF to extract ordered text blocks with page and bounding-box provenance."
          />
        </section>
      ) : (
        <section className="panel document-list-panel">
          <div className="document-table-scroll">
            <table className="document-table">
              <caption className="visually-hidden">Uploaded source documents</caption>
              <thead>
                <tr>
                  <th scope="col">Document</th>
                  <th scope="col">Pages</th>
                  <th scope="col">Evidence</th>
                  <th scope="col">Status</th>
                  <th scope="col">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.id} className={document.status === "FAILED" ? "row--failed" : ""}>
                    <td data-label="Document">
                      <Link className="document-link" to={`/documents/${document.id}`}>
                        <span className="document-icon">
                          <FileText size={18} />
                        </span>
                        <span>
                          <strong>{document.original_filename}</strong>
                          <small>{document.content_hash.slice(0, 12)}…</small>
                          {document.error_message && <small className="document-error">
                            {document.error_message}
                          </small>}
                        </span>
                      </Link>
                    </td>
                    <td data-label="Pages"><span className="table-number">{document.page_count ?? "—"}</span></td>
                    <td data-label="Evidence"><span className="table-number">{document.evidence_chunk_count}</span></td>
                    <td data-label="Status">
                      <span
                        className={`document-status document-status--${document.status.toLowerCase()}`}
                      >
                        {document.status.replace("_", " ")}
                      </span>
                    </td>
                    <td data-label="Uploaded"><time dateTime={document.created_at}>
                      {formatDate(document.created_at)}
                    </time></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
