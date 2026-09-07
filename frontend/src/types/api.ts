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
