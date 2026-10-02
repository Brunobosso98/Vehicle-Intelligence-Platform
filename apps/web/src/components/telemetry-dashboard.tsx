"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Vehicle = components["schemas"]["Vehicle"];
type Session = components["schemas"]["DrivingSession"];
type Window = components["schemas"]["TelemetryWindow"];
type Signal = components["schemas"]["Signal"];

async function json<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { cache: "no-store", signal });
  if (!response.ok) throw new Error("request failed");
  return (await response.json()) as T;
}

export function TelemetryDashboard() {
  const [vehicles, setVehicles] = useState<Vehicle[] | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [catalog, setCatalog] = useState<Signal[]>([]);
  const [selected, setSelected] = useState("engine.rpm");
  const [window, setWindow] = useState<Window | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(async (signal: AbortSignal) => {
    setError(false);
    try {
      const [vehicleData, signalData] = await Promise.all([
        json<Vehicle[]>("/api/domain/vehicles", signal),
        json<Signal[]>("/api/domain/signals", signal),
      ]);
      setVehicles(vehicleData);
      setCatalog(signalData);
      if (vehicleData[0]) {
        const sessionData = await json<Session[]>(
          `/api/domain/sessions?vehicle_id=${vehicleData[0].id}`,
          signal,
        );
        setSessions(sessionData);
      }
    } catch {
      if (!signal.aborted) setError(true);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // Async fetch callbacks, rather than the effect body, publish remote state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [attempt, load]);

  useEffect(() => {
    const controller = new AbortController();
    if (sessions[0]) {
      void json<Window>(
        `/api/domain/sessions/${sessions[0].id}/telemetry?signal=${encodeURIComponent(selected)}&limit=2000`,
        controller.signal,
      ).then(setWindow, () => !controller.signal.aborted && setError(true));
    }
    return () => controller.abort();
  }, [sessions, selected]);

  const polyline = useMemo(() => {
    const points = window?.points ?? [];
    if (points.length < 2) return "";
    const values = points.map((point) => point.value);
    const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
    return points.map((point, index) => `${(index / (points.length - 1)) * 700},${180 - ((point.value - min) / span) * 150}`).join(" ");
  }, [window]);

  return (
    <section className="telemetry-card" aria-labelledby="telemetry-heading">
      <div className="section-label">VEHICLE &amp; TELEMETRY · PHASE 1</div>
      <h2 id="telemetry-heading">Telemetry timeline</h2>
      {vehicles === null && !error && <p role="status">Loading vehicles and signals…</p>}
      {error && <div role="alert"><p>Telemetry could not be loaded.</p><button onClick={() => setAttempt((value) => value + 1)}>Retry</button></div>}
      {vehicles?.length === 0 && <p>No vehicles yet. Create a vehicle and import a session through the API.</p>}
      {vehicles?.[0] && <>
        <h3>{vehicles[0].nickname ?? `${vehicles[0].manufacturer} ${vehicles[0].model}`}</h3>
        <p>{vehicles[0].generation} · {vehicles[0].model_year} · {vehicles[0].engine_code}</p>
        {sessions.length === 0 ? <p>No telemetry sessions are available.</p> : <>
          <dl className="status-list"><div><dt>Source</dt><dd>{sessions[0].source_type}</dd></div><div><dt>Samples</dt><dd>{sessions[0].sample_count}</dd></div><div><dt>Started</dt><dd>{sessions[0].started_at ? new Date(sessions[0].started_at).toLocaleString() : "—"}</dd></div></dl>
          <label htmlFor="signal">Signal</label>
          <select id="signal" value={selected} onChange={(event) => { setWindow(null); setSelected(event.target.value); }}>
            {catalog.map((signal) => <option key={signal.key} value={signal.key}>{signal.name} ({signal.unit})</option>)}
          </select>
          {window === null ? <p role="status">Loading telemetry…</p> : window.points.length === 0 ? <p>No points in this time window.</p> : <figure><svg viewBox="0 0 700 200" role="img" aria-label={`${selected} time-series chart`}><polyline points={polyline} fill="none" stroke="currentColor" strokeWidth="3" /></svg><figcaption>{window.returned} points · {window.points[0]?.unit}{window.truncated ? " · bounded response; narrow the window" : ""}</figcaption></figure>}
        </>}
      </>}
    </section>
  );
}
