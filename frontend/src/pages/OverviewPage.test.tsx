import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { OverviewPage } from "./OverviewPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it("shows wake-up states and loads dashboard data after readiness succeeds", async () => {
  vi.useFakeTimers();
  const ready = vi.spyOn(api, "ready")
    .mockRejectedValueOnce(new Error("asleep"))
    .mockResolvedValue({ status: "ready", database: "connected" });
  const documents = vi.spyOn(api.documents, "list").mockResolvedValue([]);
  const facts = vi.spyOn(api.facts, "list").mockResolvedValue({
    items: [], total: 4, offset: 0, limit: 1,
  });
  const relations = vi.spyOn(api.relations, "list").mockResolvedValue({
    items: [], total: 3, offset: 0, limit: 1,
  });

  render(<MemoryRouter><OverviewPage /></MemoryRouter>);
  expect(screen.getByText("Connecting…")).toBeTruthy();
  expect(screen.queryByText("Unavailable")).toBeNull();

  await act(async () => Promise.resolve());
  expect(screen.getByText("Waking backend…")).toBeTruthy();

  await act(async () => vi.advanceTimersByTimeAsync(3_000));
  await act(async () => Promise.resolve());

  expect(screen.getAllByText("Connected")).toHaveLength(2);
  expect(ready).toHaveBeenCalledTimes(2);
  expect(documents).toHaveBeenCalledTimes(1);
  expect(facts).toHaveBeenCalledTimes(1);
  expect(relations).toHaveBeenCalledTimes(5);
});

it("shows unavailable after the retry window and supports manual recovery", async () => {
  vi.useFakeTimers();
  const ready = vi.spyOn(api, "ready").mockRejectedValue(new Error("offline"));
  vi.spyOn(api.documents, "list").mockResolvedValue([]);
  vi.spyOn(api.facts, "list").mockResolvedValue({
    items: [], total: 0, offset: 0, limit: 1,
  });
  vi.spyOn(api.relations, "list").mockResolvedValue({
    items: [], total: 0, offset: 0, limit: 1,
  });

  render(<MemoryRouter><OverviewPage /></MemoryRouter>);
  await act(async () => Promise.resolve());
  await act(async () => vi.advanceTimersByTimeAsync(48_000));

  expect(screen.getAllByText("Unavailable")).toHaveLength(2);
  expect(screen.getByText("Retry connection")).toBeTruthy();

  ready.mockResolvedValue({ status: "ready", database: "connected" });
  await act(async () => fireEvent.click(screen.getByText("Retry connection")));
  await act(async () => Promise.resolve());

  expect(screen.getAllByText("Connected")).toHaveLength(2);
});
