export interface HealthResponse {
  status: "ok";
}

export interface ReadyResponse {
  status: "ready";
  database: "connected";
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export type DocumentStatus = "UPLOADED" | "PROCESSING" | "PROCESSED" | "FAILED";

export interface DocumentRecord {
  id: string;
  original_filename: string;
  content_hash: string;
  mime_type: string;
  file_size_bytes: number | null;
  page_count: number | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  evidence_chunk_count: number;
}

export interface DocumentUploadResponse {
  document: DocumentRecord;
  already_existed: boolean;
}

export interface EvidenceChunk {
  id: string;
  document_id: string;
  page_number: number;
  block_index: number;
  text: string;
  bbox: number[] | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface EvidencePage {
  items: EvidenceChunk[];
  total: number;
  offset: number;
  limit: number;
  page: number | null;
}

export interface FactRecord {
  id: string;
  document_id: string;
  evidence_chunk_ids: string[];
  subject: string;
  predicate: string;
  normalized_subject: string | null;
  normalized_predicate: string | null;
  raw_value: unknown;
  normalized_value: unknown | null;
  value_type: string | null;
  raw_unit: string | null;
  normalized_unit: string | null;
  period_start: string | null;
  period_end: string | null;
  as_of_date: string | null;
  geography: string | null;
  scope: string | null;
  qualifiers: Record<string, unknown>;
  extraction_confidence: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  source_document: { id: string; original_filename: string } | null;
  page_numbers: number[];
  evidence: EvidenceChunk[];
}

export interface FactPage {
  items: FactRecord[];
  total: number;
  offset: number;
  limit: number;
}

export interface ExtractionSummary {
  document_id: string;
  status: "completed" | "partial" | "failed";
  windows_total: number;
  windows_processed: number;
  windows_failed: number;
  windows_skipped: number;
  facts_produced: number;
  facts_created: number;
  facts_deduplicated: number;
  candidates_rejected: number;
  duration_seconds: number;
  failures: { window: number; code: string }[];
}

export interface NormalizationSummary {
  document_id: string;
  facts_total: number;
  facts_changed: number;
  values_normalized: number;
  temporal_contexts_normalized: number;
  facts_with_warnings: number;
}

export type RelationType =
  | "CORROBORATES"
  | "CONTRADICTS"
  | "RECONCILABLE"
  | "UNRELATED"
  | "NEEDS_REVIEW";

export interface RelationRecord {
  id: string;
  fact_a_id: string;
  fact_b_id: string;
  relation_type: RelationType;
  confidence: number | null;
  explanation: string | null;
  reasoning_details: Record<string, unknown>;
  created_at: string;
  fact_a: FactRecord;
  fact_b: FactRecord;
}

export interface RelationPage {
  items: RelationRecord[];
  total: number;
  offset: number;
  limit: number;
}

export interface RelationComparisonSummary {
  document_id: string;
  pairs_considered: number;
  relations_created: number;
  duplicates_skipped: number;
  corroborates: number;
  contradicts: number;
  reconcilable: number;
  needs_review: number;
  unrelated: number;
}
