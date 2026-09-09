import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";

export type ConnectionState = "connecting" | "waking" | "connected" | "unavailable";

export interface ReadinessOptions {
  retryIntervalMs?: number;
  maxWaitMs?: number;
}

const DEFAULT_RETRY_INTERVAL_MS = 3_000;
const DEFAULT_MAX_WAIT_MS = 48_000;

export function useBackendReadiness(options: ReadinessOptions = {}) {
  const retryIntervalMs = options.retryIntervalMs ?? DEFAULT_RETRY_INTERVAL_MS;
  const maxWaitMs = options.maxWaitMs ?? DEFAULT_MAX_WAIT_MS;
  const [status, setStatus] = useState<ConnectionState>("connecting");
  const [run, setRun] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;
    let activeRequest: AbortController | undefined;
    const startedAt = Date.now();

    setStatus("connecting");

    async function checkReadiness() {
      activeRequest = new AbortController();
      try {
        const response = await api.ready(activeRequest.signal);
        if (cancelled) return;
        if (response.status === "ready" && response.database === "connected") {
          setStatus("connected");
          return;
        }
      } catch {
        if (cancelled) return;
      } finally {
        activeRequest = undefined;
      }

      const elapsed = Date.now() - startedAt;
      if (elapsed >= maxWaitMs) {
        setStatus("unavailable");
        return;
      }
      setStatus("waking");
      retryTimer = window.setTimeout(
        () => void checkReadiness(),
        Math.min(retryIntervalMs, maxWaitMs - elapsed),
      );
    }

    void checkReadiness();
    return () => {
      cancelled = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      activeRequest?.abort();
    };
  }, [maxWaitMs, retryIntervalMs, run]);

  const retry = useCallback(() => setRun(current => current + 1), []);
  return {
    status,
    databaseStatus: status,
    retry,
    isChecking: status === "connecting" || status === "waking",
  };
}
