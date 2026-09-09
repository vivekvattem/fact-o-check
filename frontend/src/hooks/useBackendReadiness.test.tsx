import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { useBackendReadiness } from "./useBackendReadiness";

const readyResponse = { status: "ready", database: "connected" } as const;

describe("useBackendReadiness", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("starts in a neutral connecting state", () => {
    vi.spyOn(api, "ready").mockReturnValue(new Promise(() => undefined));
    const { result, unmount } = renderHook(() => useBackendReadiness());

    expect(result.current.status).toBe("connecting");
    expect(result.current.status).not.toBe("unavailable");
    unmount();
  });

  it("connects immediately when the backend is already ready", async () => {
    const ready = vi.spyOn(api, "ready").mockResolvedValue(readyResponse);
    const { result } = renderHook(() => useBackendReadiness());

    await act(async () => Promise.resolve());
    expect(result.current.status).toBe("connected");
    expect(result.current.databaseStatus).toBe("connected");
    expect(ready).toHaveBeenCalledTimes(1);
  });

  it("retries a failure, connects later, and stops retrying", async () => {
    const ready = vi.spyOn(api, "ready")
      .mockRejectedValueOnce(new Error("asleep"))
      .mockResolvedValue(readyResponse);
    const { result } = renderHook(() => useBackendReadiness({
      retryIntervalMs: 1_000,
      maxWaitMs: 5_000,
    }));

    await act(async () => Promise.resolve());
    expect(result.current.status).toBe("waking");

    await act(async () => vi.advanceTimersByTimeAsync(1_000));
    expect(result.current.status).toBe("connected");
    expect(result.current.databaseStatus).toBe("connected");
    expect(ready).toHaveBeenCalledTimes(2);

    await act(async () => vi.advanceTimersByTimeAsync(5_000));
    expect(ready).toHaveBeenCalledTimes(2);
  });

  it("becomes unavailable after the retry window", async () => {
    vi.spyOn(api, "ready").mockRejectedValue(new Error("offline"));
    const { result } = renderHook(() => useBackendReadiness({
      retryIntervalMs: 1_000,
      maxWaitMs: 2_500,
    }));

    await act(async () => Promise.resolve());
    await act(async () => vi.advanceTimersByTimeAsync(2_500));
    expect(result.current.status).toBe("unavailable");
    expect(result.current.databaseStatus).toBe("unavailable");
  });

  it("manual retry starts a fresh readiness check", async () => {
    const ready = vi.spyOn(api, "ready").mockRejectedValue(new Error("offline"));
    const { result } = renderHook(() => useBackendReadiness({
      retryIntervalMs: 1_000,
      maxWaitMs: 1_000,
    }));

    await act(async () => Promise.resolve());
    await act(async () => vi.advanceTimersByTimeAsync(1_000));
    expect(result.current.status).toBe("unavailable");

    ready.mockResolvedValue(readyResponse);
    await act(async () => result.current.retry());
    expect(result.current.status).toBe("connected");
    expect(ready).toHaveBeenCalledTimes(3);
  });
});
