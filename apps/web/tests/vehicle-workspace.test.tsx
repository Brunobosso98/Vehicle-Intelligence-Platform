import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { VehicleWorkspace } from "../src/components/vehicle-workspace";

vi.mock("../src/components/telemetry-dashboard", () => ({
  TelemetryDashboard: ({ vehicleId }: { vehicleId: string }) => (
    <p>Telemetry vehicle {vehicleId}</p>
  ),
}));
vi.mock("../src/components/analytics-workspace", () => ({
  AnalyticsWorkspace: ({ vehicleId }: { vehicleId: string }) => (
    <p>Analytics vehicle {vehicleId}</p>
  ),
}));
vi.mock("../src/components/live-acquisition", () => ({
  LiveAcquisition: ({
    vehicleId,
    onRecordingChange,
  }: {
    vehicleId: string;
    onRecordingChange: (value: boolean) => void;
  }) => (
    <>
      <p>Live vehicle {vehicleId}</p>
      <button onClick={() => onRecordingChange(true)}>Begin acquisition</button>
      <button onClick={() => onRecordingChange(false)}>
        Finish acquisition
      </button>
    </>
  ),
}));
afterEach(() => vi.restoreAllMocks());

test("vehicle choice changes every panel and stays locked during acquisition", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify([
        {
          id: "a",
          manufacturer: "BMW",
          model: "335i",
          nickname: "First vehicle",
        },
        { id: "b", manufacturer: "BMW", model: "135i", nickname: null },
      ]),
    ),
  );
  render(<VehicleWorkspace />);
  expect(await screen.findByText("Telemetry vehicle a")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Vehicle"), {
    target: { value: "b" },
  });
  expect(screen.getByText("Telemetry vehicle b")).toBeVisible();
  expect(screen.getByText("Analytics vehicle b")).toBeVisible();
  expect(screen.getByText("Live vehicle b")).toBeVisible();
  fireEvent.click(screen.getByText("Begin acquisition"));
  expect(screen.getByLabelText("Vehicle")).toBeDisabled();
  fireEvent.click(screen.getByText("Finish acquisition"));
  expect(screen.getByLabelText("Vehicle")).toBeEnabled();
});

test("failed vehicle loading can retry into an explicit empty state", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response("{}", { status: 503 }))
    .mockResolvedValueOnce(new Response("[]", { status: 200 }));
  render(<VehicleWorkspace />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "temporarily unavailable",
  );
  fireEvent.click(screen.getByText("Retry vehicle loading"));
  expect(
    await screen.findByRole("option", { name: "No vehicle available" }),
  ).toBeVisible();
  expect(screen.getByLabelText("Vehicle")).toBeDisabled();
  expect(screen.queryByText(/Telemetry vehicle/)).not.toBeInTheDocument();
});
