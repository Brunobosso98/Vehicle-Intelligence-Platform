import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TelemetryDashboard } from "../src/components/telemetry-dashboard";

const vehicle = {
  id: "v",
  manufacturer: "BMW",
  model: "335i",
  generation: "F30",
  model_year: 2015,
  engine_code: "N55",
  nickname: "Reference",
  vin: null,
  transmission: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const session = {
  id: "s",
  vehicle_id: "v",
  configuration_id: null,
  source_type: "synthetic",
  source_reference: null,
  started_at: "2026-01-01T00:00:00Z",
  ended_at: null,
  source_timezone: "UTC",
  metadata: {},
  sample_count: 2,
  status: "completed",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const signals = [
  {
    key: "engine.rpm",
    name: "Engine speed",
    category: "engine",
    unit: "rpm",
    minimum: 0,
    maximum: 9000,
    aliases: ["rpm"],
  },
  {
    key: "vehicle.speed",
    name: "Vehicle speed",
    category: "vehicle",
    unit: "m/s",
    minimum: 0,
    maximum: 100,
    aliases: ["speed"],
  },
];
const window = {
  session_id: "s",
  points: [
    {
      sample_id: "a",
      observed_at: "2026-01-01T00:00:00Z",
      signal: "engine.rpm",
      value: 800,
      unit: "rpm",
      quality: "valid",
      sequence: 1,
    },
    {
      sample_id: "b",
      observed_at: "2026-01-01T00:00:01Z",
      signal: "engine.rpm",
      value: 1200,
      unit: "rpm",
      quality: "valid",
      sequence: 2,
    },
  ],
  returned: 2,
  truncated: false,
  start: "2026-01-01T00:00:00Z",
  end: "2026-01-01T00:00:01Z",
};
const segment = {
  id: "seg",
  session_id: "s",
  segment_type: "pull" as const,
  started_at: "2026-01-01T00:00:00Z",
  ended_at: "2026-01-01T00:00:05Z",
  duration_ms: 5000,
  confidence: 0.9,
  detector_name: "generic-v1",
  algorithm_version: "segmenter-v1",
  configuration_hash: "hash",
  quality_flags: [],
  metadata: {},
  created_at: "2026-01-01T00:01:00Z",
};
const pull = {
  ...segment,
  id: "pull-1",
  segment_id: "seg",
  vehicle_id: "v",
  configuration_id: null,
  detector_name: "generic-v1",
  algorithm_version: "pull-detector-v1",
  start_rpm: 2000,
  end_rpm: 5000,
  min_rpm: 2000,
  max_rpm: 5000,
  start_speed: 15,
  end_speed: 28,
  max_speed: 28,
  max_boost: 120000,
  average_boost: 100000,
  start_iat: 300,
  end_iat: 305,
  iat_delta: 5,
  max_oil_temperature: 370,
  max_coolant_temperature: 365,
  average_throttle: 92,
  max_throttle: 95,
  sample_count: 25,
  data_completeness: 1,
};
const response = (body: unknown, ok = true) => ({ ok, json: async () => body });
const detectedEvent = {
  id: "event-1",
  vehicle_id: "v",
  session_id: "s",
  segment_id: "seg",
  pull_id: "pull-1",
  analysis_run_id: "run-1",
  event_type: "boost_drop",
  category: "performance" as const,
  started_at: "2026-01-01T00:00:02Z",
  ended_at: "2026-01-01T00:00:04Z",
  duration_ms: 2000,
  severity: "moderate" as const,
  confidence: 0.9,
  algorithm_name: "pull-behavior-detector",
  algorithm_version: "1.0.0",
  configuration_hash: "hash",
  baseline_type: "same_session_pulls" as const,
  baseline_reference: { pull_count: 2 },
  evidence: { signal: "engine.boost_pressure" },
  quality_flags: [],
  created_at: "2026-01-01T00:01:00Z",
};

describe("telemetry dashboard", () => {
  it("renders loading, vehicle, session, chart and signal interaction", async () => {
    const fetcher = vi.fn((input: string) => {
      if (input.endsWith("/vehicles"))
        return Promise.resolve(response([vehicle]));
      if (input.endsWith("/signals")) return Promise.resolve(response(signals));
      if (input.includes("/segments"))
        return Promise.resolve(response([segment]));
      if (input.includes("/pulls"))
        return Promise.resolve(
          response([
            pull,
            { ...pull, id: "pull-2", quality_flags: ["missing_boost"] },
          ]),
        );
      if (input.includes("/events"))
        return Promise.resolve(response([detectedEvent]));
      if (input.includes("/telemetry"))
        return Promise.resolve(response(window));
      return Promise.resolve(response([session]));
    });
    vi.stubGlobal("fetch", fetcher);
    render(<TelemetryDashboard />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading vehicles");
    expect(await screen.findByText("Reference")).toBeInTheDocument();
    expect(
      await screen.findByRole("img", { name: /engine.rpm/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Derived session timeline")).toBeInTheDocument();
    expect(
      await screen.findByText("Structured factual evidence"),
    ).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Filter by event type"),
      "boost_drop",
    );
    await userEvent.selectOptions(screen.getByLabelText("Filter by category"), "performance");
    await userEvent.selectOptions(screen.getByLabelText("Filter by severity"), "moderate");
    await userEvent.selectOptions(screen.getByLabelText("Filter by pull"), "pull-1");
    await userEvent.click(screen.getByRole("button", { name: "Pull 2" }));
    const comparisons = screen.getAllByRole("checkbox", { name: "Compare" });
    await userEvent.click(comparisons[0]);
    await userEvent.click(comparisons[1]);
    expect(screen.getByRole("table")).toBeInTheDocument();
    await userEvent.click(comparisons[0]);
    await userEvent.selectOptions(
      screen.getByLabelText("Signal"),
      "vehicle.speed",
    );
    await waitFor(() =>
      expect(fetcher.mock.calls.length).toBeGreaterThanOrEqual(7),
    );
  });
  it("shows empty vehicle and empty session states", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(response([]))
        .mockResolvedValueOnce(response(signals)),
    );
    const first = render(<TelemetryDashboard />);
    expect(await screen.findByText(/No vehicles yet/)).toBeInTheDocument();
    first.unmount();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(response([vehicle]))
        .mockResolvedValueOnce(response(signals))
        .mockResolvedValueOnce(response([])),
    );
    render(<TelemetryDashboard />);
    expect(
      await screen.findByText(/No telemetry sessions/),
    ).toBeInTheDocument();
  });
  it("renders failure and retries", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error("outage"))
      .mockRejectedValueOnce(new Error("outage"))
      .mockResolvedValueOnce(response([]))
      .mockResolvedValueOnce(response(signals));
    vi.stubGlobal("fetch", fetcher);
    render(<TelemetryDashboard />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(fetcher.mock.calls.length).toBeGreaterThan(2));
  });
  it("sanitizes derived-data and telemetry request failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/vehicles"))
          return Promise.resolve(response([vehicle]));
        if (input.endsWith("/signals"))
          return Promise.resolve(response(signals));
        if (input.includes("sessions?"))
          return Promise.resolve(response([session]));
        return Promise.reject(new Error("private backend failure"));
      }),
    );
    render(<TelemetryDashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Telemetry could not be loaded",
    );
  });
});
