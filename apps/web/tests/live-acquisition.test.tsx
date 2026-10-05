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

test.each([false, true])(
  "shows recipe readiness with missing boost: %s",
  async (degraded) => {
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
            readiness: degraded ? "degraded" : "ready",
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
            unavailable_capabilities: degraded ? ["boost_analysis"] : [],
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
    if (degraded)
      fireEvent.change(screen.getByLabelText("Synthetic scenario"), {
        target: { value: "missing_recommended" },
      });
    fireEvent.click(screen.getByRole("button", { name: /preflight/i }));
    await waitFor(() =>
      expect(
        screen.getByText(degraded ? "DEGRADED" : "READY"),
      ).toBeInTheDocument(),
    );
    const payload = JSON.parse(String(vi.mocked(fetch).mock.calls[2][1]?.body));
    expect(payload.signals["engine.boost_pressure"]).toBe(
      degraded ? "unsupported" : "supported",
    );
    expect(screen.getByText(/lawful closed course/i)).toBeInTheDocument();
  },
);

test.each([false, true])(
  "finalizes with a recoverable dependency failure: %s",
  async (retry) => {
    let telemetry: ((event: MessageEvent<string>) => void) | undefined;
    const streams: FakeEventSource[] = [];
    class FakeEventSource {
      constructor() {
        streams.push(this);
      }
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
        retry
          ? new Response("unavailable", { status: 503 })
          : new Response(
              JSON.stringify({
                id: "00000000-0000-0000-0000-000000000002",
                state: "completed",
                phase2: { pull_count: 1 },
                phase3: { event_count: 1 },
                capability_report: {
                  duration_seconds: 30,
                  observation_count: 120,
                  gaps_by_signal: {
                    "engine.rpm": { count: 2, maximum_seconds: 1.5 },
                  },
                  recipe_adherence: true,
                  capabilities: [
                    { key: "pull_detection", supported: true },
                    {
                      key: "fuel_analysis",
                      supported: false,
                      unavailable_reason: "Missing measured rail pressure",
                    },
                  ],
                  signal_quality: [
                    {
                      signal: "engine.rpm",
                      actual_hz: 10,
                      target_hz: 10,
                      missing_ratio: 0,
                      jitter_ms: 0,
                    },
                    {
                      signal: "vehicle.speed",
                      actual_hz: 5,
                      target_hz: 5,
                      missing_ratio: 0,
                    },
                  ],
                },
                reconciliation: { confirmed: 1, absent: 0 },
              }),
              { status: 200 },
            ),
      );
    if (retry) {
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "00000000-0000-0000-0000-000000000002",
            state: "completed",
            phase2: { pull_count: 1 },
            phase3: { event_count: 1 },
            capability_report: {
              capabilities: [
                {
                  key: "fuel_analysis",
                  supported: false,
                  unavailable_reason: "Missing measured rail pressure",
                },
              ],
              signal_quality: [
                {
                  signal: "engine.rpm",
                  actual_hz: 10,
                  target_hz: 10,
                  missing_ratio: 0,
                },
              ],
            },
            reconciliation: { confirmed: 1, absent: 0 },
          }),
        ),
      );
    }
    render(<LiveAcquisition />);
    const start = await screen.findByRole("button", {
      name: /start synthetic/i,
    });
    fireEvent.click(start);
    await waitFor(() =>
      expect(screen.getByText(/Acquisition: active/i)).toBeInTheDocument(),
    );
    const interruptedTelemetry = telemetry;
    fireEvent(window, new Event("offline"));
    expect(streams[0].close).toHaveBeenCalled();
    expect(screen.getByText(/Acquisition: disconnected/i)).toBeInTheDocument();
    interruptedTelemetry?.(
      new MessageEvent("telemetry", {
        data: JSON.stringify({ state: "active", points: [] }),
      }),
    );
    expect(screen.getByText(/Acquisition: disconnected/i)).toBeInTheDocument();
    fireEvent(window, new Event("online"));
    expect(streams).toHaveLength(2);
    expect(streams[0].close).toHaveBeenCalledTimes(1);
    telemetry?.(
      new MessageEvent("telemetry", {
        data: JSON.stringify({
          state: "active",
          quality: {
            pipeline: {
              measured_at: "2026-01-01T00:00:10Z",
              publisher_to_persistence_seconds: 0.04,
              broker_consumer_lag: 3,
              persistence_state: "observations_committed",
            },
            collector: {
              adapter_state: "connected",
              collection_started_at: "2026-01-01T00:00:00Z",
              received_at: "2026-01-01T00:00:10Z",
              last_sample_received_at: "2026-01-01T00:00:10Z",
              queue_observations: 3,
              spool_bytes: 120,
              dropped_observations: 2,
              spool_capacity_bytes: 1000,
              spool_capacity_state: "normal",
              sampling_plan: [],
            },
            collector_health: { state: "connected", heartbeat_age_seconds: 0 },
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
            {
              signal: "engine.rpm",
              value: 3000,
              unit: "rpm",
              observed_at: "2026-01-01T00:00:00Z",
            },
            {
              signal: "engine.rpm",
              value: 3200,
              unit: "rpm",
              observed_at: "2026-01-01T00:00:01Z",
            },
            {
              signal: "engine.rpm",
              value: 3500,
              unit: "rpm",
              observed_at: "2026-01-01T00:00:10Z",
            },
            {
              signal: "vehicle.speed",
              value: 25,
              unit: "m/s",
              observed_at: "2026-01-01T00:00:10Z",
            },
          ],
        }),
      }),
    );
    expect(await screen.findByText(/RPM: 3500/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /collector queue: 3 samples · spool: 120 bytes · dropped: 2/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Collection elapsed: 10.0 s/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /publisher-to-persistence latency: 40 ms · broker remaining at poll: 3 messages/,
      ),
    ).toBeInTheDocument();
    const chart = screen.getByRole("img", { name: /engine.rpm provisional/ });
    expect(chart.querySelectorAll("polyline")).toHaveLength(2);
    expect(screen.getByText(/3 observed points/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Live chart signal"), {
      target: { value: "fuel.high_pressure" },
    });
    expect(screen.getByText(/Waiting for live samples/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Live chart signal"), {
      target: { value: "engine.rpm" },
    });
    expect(screen.getByText(/9.8 Hz actual/)).toBeInTheDocument();
    expect(screen.getByText(/possible pull · pending/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /stop and finalize/i }));
    if (retry) {
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "temporarily unavailable",
      );
      fireEvent.click(
        screen.getByRole("button", { name: /retry finalization/i }),
      );
    }
    await waitFor(() =>
      expect(screen.getByText(/Acquisition: completed/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/FINAL CANONICAL RESULTS/)).toBeInTheDocument();
    expect(
      vi
        .mocked(fetch)
        .mock.calls.filter(([url]) => String(url).endsWith("/stop")),
    ).toHaveLength(1);
    expect(
      vi
        .mocked(fetch)
        .mock.calls.filter(([url]) => String(url).endsWith("/finalize")),
    ).toHaveLength(retry ? 2 : 1);
    telemetry?.(
      new MessageEvent("telemetry", {
        data: JSON.stringify({ state: "completed", points: [] }),
      }),
    );
    vi.unstubAllGlobals();
    expect(
      screen.getByRole("table", { name: "Post-log measured capabilities" }),
    ).toHaveTextContent("Missing measured rail pressure");
    expect(
      screen.getByRole("table", { name: "Final observed signal quality" }),
    ).toHaveTextContent("10.0 / 10.0");
  },
);

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

test("network failure during preflight produces an explicit recoverable state", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([])))
    .mockResolvedValueOnce(new Response(JSON.stringify([vehicle])))
    .mockRejectedValueOnce(new Error("private network details"));
  render(<LiveAcquisition />);
  fireEvent.click(await screen.findByRole("button", { name: /preflight/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "temporarily unavailable",
  );
  expect(screen.queryByText("private network details")).not.toBeInTheDocument();
});

test("rejects an HTTP failure during initial loading without treating errors as recipes", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "unavailable" }), { status: 503 }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify([vehicle]), { status: 200 }),
    );
  render(<LiveAcquisition />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "temporarily unavailable",
  );
  expect(screen.queryByText("anchors operating state")).not.toBeInTheDocument();
});
