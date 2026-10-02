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
const response = (body: unknown, ok = true) => ({ ok, json: async () => body });

describe("telemetry dashboard", () => {
  it("renders loading, vehicle, session, chart and signal interaction", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(response([vehicle]))
      .mockResolvedValueOnce(response(signals))
      .mockResolvedValueOnce(response([session]))
      .mockResolvedValue(response(window));
    vi.stubGlobal("fetch", fetcher);
    render(<TelemetryDashboard />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading vehicles");
    expect(await screen.findByText("Reference")).toBeInTheDocument();
    expect(
      await screen.findByRole("img", { name: /engine.rpm/ }),
    ).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Signal"),
      "vehicle.speed",
    );
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(5));
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
});
