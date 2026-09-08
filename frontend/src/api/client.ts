import type {
  ApiErrorResponse,
  DocumentRecord,
  DocumentUploadResponse,
  EvidencePage,
  HealthResponse,
  ReadyResponse,
  ExtractionSummary,
  FactPage,
  FactRecord,
  RelationComparisonSummary,
  RelationPage,
  RelationRecord,
  NormalizationSummary,
} from "../types/api";

const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 8_000): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
      signal: controller.signal,
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as ApiErrorResponse | null;
      throw new ApiError(
        payload?.error.message ?? `Request failed with status ${response.status}`,
        response.status,
        payload?.error.code ?? "request_failed",
      );
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  ready: () => request<ReadyResponse>("/ready"),
  facts: {
    list: (options: Record<string, string> = {}) =>
      request<FactPage>(`/api/facts?${new URLSearchParams(options).toString()}`),
    get: (factId: string) => request<FactRecord>(`/api/facts/${factId}`),
    normalize: (factId: string) =>
      request<FactRecord>(`/api/facts/${factId}/normalize`, { method: "POST" }),
  },
  relations: {
    list: (options: Record<string, string> = {}) =>
      request<RelationPage>(`/api/relations?${new URLSearchParams(options).toString()}`),
    get: (relationId: string) => request<RelationRecord>(`/api/relations/${relationId}`),
  },
  documents: {
    normalizeFacts: (documentId: string) => request<NormalizationSummary>(
      `/api/documents/${documentId}/normalize-facts`, { method: "POST" }, 200_000,
    ),
    extractFacts: (documentId: string) => request<ExtractionSummary>(
      `/api/documents/${documentId}/extract-facts`, { method: "POST" }, 200_000,
    ),
    compareFacts: (documentId: string) => request<RelationComparisonSummary>(
      `/api/documents/${documentId}/compare-facts`, { method: "POST" }, 200_000,
    ),
    list: () => request<DocumentRecord[]>("/api/documents"),
    get: (documentId: string) => request<DocumentRecord>(`/api/documents/${documentId}`),
    upload: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return request<DocumentUploadResponse>(
        "/api/documents",
        { method: "POST", body },
        60_000,
      );
    },
    evidence: (
      documentId: string,
      options: { page?: number; offset?: number; limit?: number } = {},
    ) => {
      const params = new URLSearchParams();
      if (options.page !== undefined) params.set("page", String(options.page));
      if (options.offset !== undefined) params.set("offset", String(options.offset));
      if (options.limit !== undefined) params.set("limit", String(options.limit));
      const query = params.size > 0 ? `?${params.toString()}` : "";
      return request<EvidencePage>(`/api/documents/${documentId}/evidence${query}`);
    },
    delete: (documentId: string) =>
      request<void>(`/api/documents/${documentId}`, { method: "DELETE" }),
  },
};
