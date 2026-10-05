"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";
import { AnalyticsWorkspace } from "./analytics-workspace";
import { LiveAcquisition } from "./live-acquisition";
import { TelemetryDashboard } from "./telemetry-dashboard";

type Vehicle = components["schemas"]["Vehicle"];

export function VehicleWorkspace() {
  const [vehicles, setVehicles] = useState<Vehicle[] | null>(null);
  const [vehicleId, setVehicleId] = useState("");
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/domain/vehicles", {
      signal: controller.signal,
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Vehicles unavailable");
        const items = (await response.json()) as Vehicle[];
        setVehicles(items);
        setVehicleId((selected) =>
          items.some((item) => item.id === selected)
            ? selected
            : (items[0]?.id ?? ""),
        );
        setError(false);
      })
      .catch(() => !controller.signal.aborted && setError(true));
    return () => controller.abort();
  }, [attempt]);
  return (
    <>
      <section className="telemetry-card" aria-label="Vehicle selection">
        <label htmlFor="workspace-vehicle">Vehicle</label>
        <select
          id="workspace-vehicle"
          value={vehicleId}
          disabled={recording || !vehicles?.length}
          onChange={(event) => setVehicleId(event.target.value)}
        >
          {!vehicles?.length && (
            <option value="">
              {vehicles === null ? "Loading vehicles…" : "No vehicle available"}
            </option>
          )}
          {vehicles?.map((vehicle) => (
            <option key={vehicle.id} value={vehicle.id}>
              {vehicle.nickname ?? `${vehicle.manufacturer} ${vehicle.model}`}
            </option>
          ))}
        </select>
        {recording && (
          <p role="status">
            Finalize the current acquisition before changing vehicle.
          </p>
        )}
        {error && (
          <div role="alert">
            Vehicles are temporarily unavailable.
            <button
              type="button"
              onClick={() => setAttempt((value) => value + 1)}
            >
              Retry vehicle loading
            </button>
          </div>
        )}
      </section>
      {vehicles?.length && !error ? (
        <div key={vehicleId}>
          <LiveAcquisition
            vehicleId={vehicleId || undefined}
            onRecordingChange={setRecording}
          />
          <TelemetryDashboard vehicleId={vehicleId || undefined} />
          <AnalyticsWorkspace vehicleId={vehicleId || undefined} />
        </div>
      ) : null}
    </>
  );
}
