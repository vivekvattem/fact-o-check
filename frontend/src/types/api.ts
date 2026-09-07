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
