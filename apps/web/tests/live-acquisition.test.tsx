import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { LiveAcquisition } from "../src/components/live-acquisition";

afterEach(() => vi.restoreAllMocks());

const vehicle = {
  id: "00000000-0000-0000-0000-000000000001",
  manufacturer: "BMW",
  model: "335i",
  generation: "F30",
  model_year: 2015,
  engine_code: "N55",
  nickname: null,
  vin: null,
  transmission: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

test("shows recipe requirements and structured readiness", async () => {
  const recipe = {
    key: "performance-pull",
    name: "Performance Pull",
    description: "Factual acquisition",
    objective: "performance_pull",
    version: 1,
    configuration_hash: "a".repeat(64),
    vehicle_scope: "generic-obd-ii",
    minimum_duration_seconds: 15,
    supported_modes: ["synthetic"],
    notes: [],
    requirements: [
      {
        signal: "engine.rpm",
        importance: "required",
        reason: "anchors operating state",
        minimum_hz: 5,
        preferred_hz: 10,
        priority: "critical_for_recipe",
        missing_effect: ["pull_detection"],
      },
    ],
  };
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify([recipe]), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify([vehicle]), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          readiness: "ready",
          required_available: ["engine.rpm"],
          required_missing: [],
          recommended_available: [],
          optional_available: [],
          sampling_plan: [
            {
              signal: "engine.rpm",
              priority: "critical_for_recipe",
              target_hz: 10,
              estimated_hz: 10,
            },
          ],
          expected_capabilities: ["temporal_segmentation"],
          unavailable_capabilities: [],
          warnings: [],
        }),
        { status: 200 },
      ),
    );
  render(<LiveAcquisition />);
  expect(await screen.findByText("engine.rpm")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Known objective"), {
    target: { value: "performance-pull" },
  });
  fireEvent.click(screen.getByRole("button", { name: /preflight/i }));
  await waitFor(() => expect(screen.getByText("READY")).toBeInTheDocument());
  expect(screen.getByText(/lawful closed course/i)).toBeInTheDocument();
});

test("starts, streams, stops, and finalizes a synthetic acquisition", async () => {
  let telemetry: ((event: MessageEvent<string>) => void) | undefined;
  class FakeEventSource {
    addEventListener(_name: string, listener: EventListener) {
      telemetry = listener as (event: MessageEvent<string>) => void;
    }
    close = vi.fn();
  }
  vi.stubGlobal("EventSource", FakeEventSource);
  const recipe = {
    key: "performance-pull",
    name: "Performance Pull",
    description: "Factual",
    objective: "performance_pull",
    version: 1,
    configuration_hash: "a".repeat(64),
    vehicle_scope: "generic-obd-ii",
    minimum_duration_seconds: 15,
    supported_modes: ["synthetic"],
    notes: [],
    requirements: [],
  };
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify([recipe]), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify([vehicle]), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "00000000-0000-0000-0000-000000000002",
          driving_session_id: "00000000-0000-0000-0000-000000000003",
          state: "active",
          ingestion_token: "x".repeat(43),
          token_expires_at: "2026-01-01T01:00:00Z",
        }),
        { status: 201 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "started" }), { status: 202 }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ state: "stopping" }), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "00000000-0000-0000-0000-000000000002",
          state: "completed",
          phase2: { pull_count: 1 },
          phase3: { event_count: 1 },
          capability_report: {},
          reconciliation: { confirmed: 1, absent: 0 },
        }),
        { status: 200 },
      ),
    );
  render(<LiveAcquisition />);
  const start = await screen.findByRole("button", { name: /start synthetic/i });
  fireEvent.click(start);
  await waitFor(() =>
    expect(screen.getByText(/Acquisition: active/i)).toBeInTheDocument(),
  );
  telemetry?.(
    new MessageEvent("telemetry", {
      data: JSON.stringify({
        state: "active",
        quality: {
          signals: [
            {
              signal: "engine.rpm",
              target_hz: 10,
              actual_hz: 9.8,
              jitter_seconds: 0.01,
              stale_ratio: 0,
              missing_ratio: 0.02,
            },
          ],
        },
        findings: [
          {
            id: "finding-1",
            finding_type: "possible_pull",
            reconciliation_status: "pending",
          },
        ],
        points: [
          { signal: "engine.rpm", value: 3500 },
          { signal: "vehicle.speed", value: 25 },
        ],
      }),
    }),
  );
  expect(await screen.findByText(/RPM: 3500/)).toBeInTheDocument();
  expect(screen.getByText(/9.8 Hz actual/)).toBeInTheDocument();
  expect(screen.getByText(/possible pull · pending/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /stop and finalize/i }));
  await waitFor(() =>
    expect(screen.getByText(/Acquisition: completed/i)).toBeInTheDocument(),
  );
  expect(screen.getByText(/FINAL CANONICAL RESULTS/)).toBeInTheDocument();
  telemetry?.(
    new MessageEvent("telemetry", {
      data: JSON.stringify({ state: "completed", points: [] }),
    }),
  );
  vi.unstubAllGlobals();
});

test("shows a recoverable failure when acquisition creation is rejected", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(JSON.stringify([vehicle]), { status: 200 }),
    )
    .mockResolvedValueOnce(new Response("rejected", { status: 503 }));
  render(<LiveAcquisition />);
  fireEvent.click(
    await screen.findByRole("button", { name: /start synthetic/i }),
  );
  expect(
    await screen.findByText(/planning is temporarily unavailable/i),
  ).toBeInTheDocument();
});
