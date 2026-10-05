"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Recipe = components["schemas"]["LoggingRecipeResponse"];
type Preflight = components["schemas"]["PreflightResponse"];
type Vehicle = components["schemas"]["Vehicle"];
type Acquisition = components["schemas"]["AcquisitionCreated"];
type Finalized = components["schemas"]["AcquisitionFinalized"];

type LivePoint = components["schemas"]["LiveTelemetryPoint"];
type LiveFinding = components["schemas"]["ProvisionalFindingResponse"];
type SignalQuality = components["schemas"]["LiveSignalQuality"];
type CollectorReport = components["schemas"]["CollectorReportedState"];
type Pipeline = components["schemas"]["AcquisitionPipelineMeasurement"];
type LiveSnapshot = components["schemas"]["AcquisitionLiveSnapshot"];

const syntheticSignals = {
  "engine.rpm": "supported",
  "vehicle.speed": "supported",
  "engine.throttle_position": "supported",
  "engine.boost_pressure": "supported",
  "engine.intake_air_temperature": "supported",
  "engine.oil_temperature": "supported",
  "engine.coolant_temperature": "supported",
  "fuel.high_pressure": "supported",
} as const;

export function LiveAcquisition({
  vehicleId,
  onRecordingChange,
}: {
  vehicleId?: string;
  onRecordingChange?: (recording: boolean) => void;
}) {
  const streamRef = useRef<EventSource | null>(null);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [scenario, setScenario] = useState("boost_drop");
  const [recipeKey, setRecipeKey] = useState("performance-pull");
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [error, setError] = useState(false);
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [acquisition, setAcquisition] = useState<Acquisition | null>(null);
  const [liveState, setLiveState] = useState("idle");
  const [points, setPoints] = useState<LivePoint[]>([]);
  const [chartSignal, setChartSignal] = useState("engine.rpm");
  const [latest, setLatest] = useState<Record<string, number>>({});
  const [findings, setFindings] = useState<LiveFinding[]>([]);
  const [collectorHealth, setCollectorHealth] = useState("not_reported");
  const [signalQuality, setSignalQuality] = useState<SignalQuality[]>([]);
  const [stopped, setStopped] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [collector, setCollector] = useState<CollectorReport | null>(null);
  const [finalized, setFinalized] = useState<Finalized | null>(null);
  const recipe = recipes.find((item) => item.key === recipeKey);
  const capabilityReport = finalized?.capability_report;

  useEffect(() => {
    if (!acquisition || stopped) return;
    const acquisitionId = acquisition.id;
    function connect() {
      streamRef.current?.close();
      const stream = new EventSource(
        `/api/domain/acquisitions/${acquisitionId}/live`,
      );
      streamRef.current = stream;
      stream.onerror = () => {
        if (streamRef.current === stream) setLiveState("disconnected");
      };
      stream.addEventListener("telemetry", (event) => {
        if (streamRef.current !== stream) return;
        const payload = JSON.parse(
          (event as MessageEvent<string>).data,
        ) as LiveSnapshot;
        setPoints(payload.points);
        setLiveState(payload.state);
        setFindings(payload.findings ?? []);
        setSignalQuality(payload.quality?.signals ?? []);
        setCollector(payload.quality?.collector ?? null);
        setPipeline(payload.quality?.pipeline ?? null);
        setCollectorHealth(
          payload.quality?.collector_health?.state ?? "not_reported",
        );
        setLatest(
          Object.fromEntries(
            payload.points.map((point) => [point.signal, point.value]),
          ),
        );
        if (["completed", "failed"].includes(payload.state)) stream.close();
      });
    }
    function disconnect() {
      streamRef.current?.close();
      streamRef.current = null;
      setLiveState("disconnected");
    }
    if (navigator.onLine) connect();
    else disconnect();
    window.addEventListener("offline", disconnect);
    window.addEventListener("online", connect);
    return () => {
      window.removeEventListener("offline", disconnect);
      window.removeEventListener("online", connect);
      streamRef.current?.close();
      streamRef.current = null;
    };
  }, [acquisition, stopped]);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      fetch("/api/domain/logging/recipes", { signal: controller.signal }).then(
        (response) => {
          if (!response.ok) throw new Error("Recipes are unavailable");
          return response.json() as Promise<Recipe[]>;
        },
      ),
      fetch("/api/domain/vehicles", { signal: controller.signal }).then(
        (response) => {
          if (!response.ok) throw new Error("Vehicles are unavailable");
          return response.json() as Promise<Vehicle[]>;
        },
      ),
    ]).then(
      ([items, vehicles]) => {
        setRecipes(items);
        setVehicle(
          (vehicleId
            ? vehicles.find((item) => item.id === vehicleId)
            : vehicles[0]) ?? null,
        );
      },
      () => !controller.signal.aborted && setError(true),
    );
    return () => controller.abort();
  }, [vehicleId]);

  async function attempt(action: () => Promise<void>) {
    try {
      await action();
    } catch {
      setError(true);
    }
  }

  async function runPreflight() {
    setError(false);
    const response = await fetch(
      `/api/domain/logging/recipes/${recipeKey}/preflight`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          adapter: "synthetic-live-v1",
          signals: {
            ...syntheticSignals,
            "engine.boost_pressure":
              scenario === "missing_recommended" ? "unsupported" : "supported",
          },
          maximum_requests_per_second: 70,
        }),
      },
    );
    if (!response.ok) {
      setError(true);
      return;
    }
    setPreflight((await response.json()) as Preflight);
  }

  async function startSynthetic() {
    if (!vehicle) {
      setError(true);
      return;
    }
    const created = await fetch("/api/domain/acquisitions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        vehicle_id: vehicle.id,
        recipe_key: recipeKey,
        adapter: "synthetic",
        source_id: "web-synthetic",
      }),
    });
    if (!created.ok) {
      setError(true);
      return;
    }
    const value = (await created.json()) as Acquisition;
    setAcquisition(value);
    setStopped(false);
    setFinalized(null);
    setError(false);
    onRecordingChange?.(true);
    setLiveState("active");
    const started = await fetch(
      `/api/domain/acquisitions/${value.id}/synthetic?scenario=${scenario}`,
      {
        method: "POST",
        headers: { authorization: `Bearer ${value.ingestion_token}` },
      },
    );
    if (!started.ok) {
      streamRef.current?.close();
      setError(true);
    }
  }

  async function stopAndFinalize() {
    if (!acquisition || finalizing) return;
    setError(false);
    setFinalizing(true);
    try {
      if (!stopped) {
        const response = await fetch(
          `/api/domain/acquisitions/${acquisition.id}/stop`,
          {
            method: "POST",
            headers: { authorization: `Bearer ${acquisition.ingestion_token}` },
          },
        );
        if (!response.ok) throw new Error("Stop unavailable");
        setStopped(true);
      }
      setLiveState("finalizing");
      const response = await fetch(
        `/api/domain/acquisitions/${acquisition.id}/finalize`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("Finalization unavailable");
      setFinalized((await response.json()) as Finalized);
      setLiveState("completed");
      onRecordingChange?.(false);
    } catch {
      setError(true);
      setLiveState("failed");
    } finally {
      setFinalizing(false);
    }
  }

  return (
    <section
      className="telemetry-card live-acquisition"
      aria-labelledby="live-heading"
    >
      <div className="section-label">
        STREAMING &amp; LIVE ACQUISITION · PHASE 4
      </div>
      <h2 id="live-heading">Plan a read-only acquisition</h2>
      <p>
        Choose a predefined objective, inspect its evidence requirements, then
        verify what a source can actually sample. Live feedback is provisional;
        persisted Phase 2/3 results are final.
      </p>
      <label htmlFor="recipe">Known objective</label>
      <select
        id="recipe"
        value={recipeKey}
        onChange={(event) => {
          setRecipeKey(event.target.value);
          setPreflight(null);
        }}
      >
        {recipes.map((item) => (
          <option key={item.key} value={item.key}>
            {item.name}
          </option>
        ))}
      </select>
      {recipe && (
        <div className="recipe-grid">
          <div>
            <strong>Recipe</strong>
            <span>
              {recipe.name} · v{recipe.version}
            </span>
          </div>
          <div>
            <strong>Minimum duration</strong>
            <span>{recipe.minimum_duration_seconds}s</span>
          </div>
          <div>
            <strong>Configuration</strong>
            <code>{recipe.configuration_hash.slice(0, 12)}</code>
          </div>
        </div>
      )}
      {recipe && (
        <ul className="requirements">
          {recipe.requirements.map((item) => (
            <li key={item.signal}>
              <span className={`importance ${item.importance}`}>
                {item.importance}
              </span>
              <strong>{item.signal}</strong>
              <small>
                {item.reason} · {item.preferred_hz} Hz preferred
              </small>
            </li>
          ))}
        </ul>
      )}
      <label htmlFor="synthetic-scenario">Synthetic scenario</label>
      <select
        id="synthetic-scenario"
        value={scenario}
        disabled={!!acquisition && !finalized}
        onChange={(event) => {
          setScenario(event.target.value);
          setPreflight(null);
        }}
      >
        <option value="boost_drop">Observed boost drop</option>
        <option value="missing_recommended">
          Missing recommended boost signal
        </option>
      </select>
      <button type="button" onClick={() => void attempt(runPreflight)}>
        Run synthetic device preflight
      </button>
      <button
        type="button"
        disabled={!vehicle || (!!acquisition && !finalized)}
        onClick={() => void attempt(startSynthetic)}
      >
        Start synthetic live acquisition
      </button>
      <button
        type="button"
        disabled={!acquisition || !!finalized || finalizing}
        onClick={() => void attempt(stopAndFinalize)}
      >
        {stopped ? "Retry finalization" : "Stop and finalize"}
      </button>
      <div className="readiness" aria-live="polite">
        <strong>Acquisition: {liveState}</strong>
        <span>Collector: {collectorHealth.replaceAll("_", " ")}</span>
        <span>
          Vehicle:{" "}
          {vehicle?.nickname ?? vehicle?.model ?? "No vehicle available"}
        </span>
        <span>
          RPM: {latest["engine.rpm"]?.toFixed(0) ?? "—"} · Speed:{" "}
          {latest["vehicle.speed"]?.toFixed(1) ?? "—"} m/s · Throttle:{" "}
          {latest["engine.throttle_position"]?.toFixed(1) ?? "—"}%
        </span>
        <span>
          Boost: {latest["engine.boost_pressure"]?.toFixed(0) ?? "unavailable"}{" "}
          Pa · IAT:{" "}
          {latest["engine.intake_air_temperature"]?.toFixed(1) ?? "unavailable"}{" "}
          K · Coolant:{" "}
          {latest["engine.coolant_temperature"]?.toFixed(1) ?? "unavailable"} K
          · Oil: {latest["engine.oil_temperature"]?.toFixed(1) ?? "unavailable"}{" "}
          K · Fuel pressure:{" "}
          {latest["fuel.high_pressure"]?.toFixed(0) ?? "unavailable"} Pa
        </span>
        <span>
          Live observations are provisional · up to 60 seconds / 2,000 points
          {collector &&
            ` · Collection elapsed: ${Math.max(
              0,
              (Date.parse(collector.received_at) -
                Date.parse(collector.collection_started_at)) /
                1000,
            ).toFixed(1)} s at last heartbeat`}
        </span>
      </div>
      <LiveSignalChart
        points={points}
        signal={chartSignal}
        onSignalChange={setChartSignal}
      />
      {error && (
        <p role="alert">
          {stopped
            ? "Finalization is temporarily unavailable. Stop was acknowledged; retry to retrieve canonical results."
            : "Acquisition planning is temporarily unavailable."}
        </p>
      )}
      {preflight && (
        <div className={`readiness ${preflight.readiness}`} role="status">
          <strong>{preflight.readiness.toUpperCase()}</strong>
          <span>{preflight.sampling_plan.length} signals planned</span>
          <div className="capability-matrix" aria-label="Capability matrix">
            {preflight.sampling_plan.map((item) => (
              <span key={item.signal}>
                {item.signal}: supported · {item.estimated_hz.toFixed(1)} Hz
                planned
              </span>
            ))}
          </div>
          <span>
            {preflight.unavailable_capabilities.length
              ? `Unavailable: ${preflight.unavailable_capabilities.join(", ")}`
              : "All requested capabilities available"}
          </span>
        </div>
      )}
      {signalQuality.length > 0 && (
        <div className="readiness" aria-label="Actual signal quality">
          <strong>Measured signal rates</strong>
          <span>
            Browser stream: {liveState};{" "}
            {collector
              ? `collector queue: ${collector.queue_observations} samples · spool: ${collector.spool_bytes} bytes · dropped: ${collector.dropped_observations}`
              : "collector drops and buffer: not reported by this stream."}
          </span>
          <span>
            {pipeline
              ? `Canonical persistence confirmed at ${pipeline.measured_at} · publisher-to-persistence latency: ${pipeline.publisher_to_persistence_seconds == null ? "unavailable" : `${(pipeline.publisher_to_persistence_seconds * 1000).toFixed(0)} ms`} · broker remaining at poll: ${pipeline.broker_consumer_lag ?? "unavailable"} messages`
              : "Broker/consumer checkpoint and transport latency: unavailable"}
          </span>
          {signalQuality.slice(0, 8).map((item) => (
            <span key={item.signal}>
              {item.signal}: {item.actual_hz.toFixed(1)} Hz actual /{" "}
              {item.target_hz.toFixed(1)} Hz target ·{" "}
              {(item.missing_ratio * 100).toFixed(1)}% missing
            </span>
          ))}
        </div>
      )}
      {findings.length > 0 && (
        <div className="readiness" aria-label="Provisional live findings">
          <strong>LIVE / PROVISIONAL</strong>
          {findings.map((finding) => (
            <span key={finding.id}>
              {finding.finding_type.replaceAll("_", " ")} ·{" "}
              {finding.reconciliation_status}
            </span>
          ))}
        </div>
      )}
      {finalized && (
        <div
          className="readiness completed"
          aria-label="Canonical final results"
        >
          <strong>FINAL CANONICAL RESULTS</strong>
          <span>✓ Telemetry persisted</span>
          <span>
            ✓ Phase 2 complete · {finalized.phase2.pull_count} pull(s)
          </span>
          <span>
            ✓ Phase 3 complete · {finalized.phase3.event_count} factual event(s)
          </span>
          <span>✓ Dataset capability assessment complete</span>
          <p>
            Observed duration:{" "}
            {capabilityReport?.duration_seconds ?? "Unavailable"} seconds ·
            Observations: {capabilityReport?.observation_count ?? "Unavailable"}{" "}
            · Gaps:{" "}
            {capabilityReport?.gaps_by_signal
              ? Object.values(capabilityReport.gaps_by_signal).reduce(
                  (total, item) => total + item.count,
                  0,
                )
              : "Unavailable"}{" "}
            · Recipe adherence:{" "}
            {capabilityReport?.recipe_adherence ? "Met" : "Not met"}
          </p>
          {capabilityReport?.capabilities?.length ? (
            <table>
              <caption>Post-log measured capabilities</caption>
              <thead>
                <tr>
                  <th>Analysis</th>
                  <th>Availability</th>
                  <th>Limitation</th>
                </tr>
              </thead>
              <tbody>
                {capabilityReport.capabilities.map((item) => (
                  <tr key={item.key}>
                    <th>{item.key.replaceAll("_", " ")}</th>
                    <td>{item.supported ? "Supported" : "Unavailable"}</td>
                    <td>
                      {item.unavailable_reason ?? "Measured source coverage"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Capability details are unavailable.</p>
          )}
          {capabilityReport?.signal_quality?.length ? (
            <table>
              <caption>Final observed signal quality</caption>
              <thead>
                <tr>
                  <th>Signal</th>
                  <th>Actual / target Hz</th>
                  <th>Missing</th>
                  <th>Jitter</th>
                </tr>
              </thead>
              <tbody>
                {capabilityReport.signal_quality.map((item) => (
                  <tr key={item.signal}>
                    <th>{item.signal}</th>
                    <td>
                      {item.actual_hz.toFixed(1)} / {item.target_hz.toFixed(1)}
                    </td>
                    <td>{(item.missing_ratio * 100).toFixed(1)}%</td>
                    <td>{item.jitter_ms?.toFixed(1) ?? "Unavailable"} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          <span>
            Reconciled: {finalized.reconciliation.confirmed ?? 0} confirmed ·{" "}
            {finalized.reconciliation.absent ?? 0} absent
          </span>
        </div>
      )}
      <p className="safety-note">
        Controlled acceleration testing belongs only on a dyno or lawful closed
        course. This platform observes; it never commands the driver or vehicle.
      </p>
    </section>
  );
}

function LiveSignalChart({
  points,
  signal,
  onSignalChange,
}: {
  points: LivePoint[];
  signal: string;
  onSignalChange: (signal: string) => void;
}) {
  const samples = points.filter((point) => point.signal === signal);
  const low = Math.min(...samples.map((point) => point.value));
  const high = Math.max(...samples.map((point) => point.value));
  const first = Date.parse(samples[0]?.observed_at ?? "");
  const last = Date.parse(samples.at(-1)?.observed_at ?? "");
  const paths: string[][] = [];
  samples.forEach((point, index) => {
    const at = Date.parse(point.observed_at);
    if (!index || at - Date.parse(samples[index - 1].observed_at) > 2000)
      paths.push([]);
    const x = 35 + ((at - first) / Math.max(1, last - first)) * 630;
    const y = 170 - ((point.value - low) / Math.max(1, high - low)) * 140;
    paths.at(-1)?.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  });
  return (
    <section aria-label="Provisional live chart">
      <label htmlFor="live-chart-signal">Live chart signal</label>
      <select
        id="live-chart-signal"
        value={signal}
        onChange={(event) => onSignalChange(event.target.value)}
      >
        {Object.keys(syntheticSignals).map((key) => (
          <option key={key} value={key}>
            {key}
          </option>
        ))}
      </select>
      {samples.length < 2 ? (
        <p role="status">Waiting for live samples for this signal.</p>
      ) : (
        <figure>
          <svg
            viewBox="0 0 700 200"
            role="img"
            aria-label={`${signal} provisional time-series chart`}
          >
            <title>
              {signal}: {low.toFixed(1)}–{high.toFixed(1)} {samples[0].unit}
            </title>
            <line x1="35" y1="180" x2="665" y2="180" stroke="currentColor" />
            {paths.map((path, index) => (
              <polyline
                key={index}
                points={path.join(" ")}
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
              />
            ))}
          </svg>
          <figcaption>
            {samples.length} observed points · {samples[0].unit} ·{" "}
            {((last - first) / 1000).toFixed(1)} seconds · gaps remain
            disconnected
          </figcaption>
          <details>
            <summary>Latest measured values</summary>
            <table>
              <thead>
                <tr>
                  <th>Observed time</th>
                  <th>Value ({samples[0].unit})</th>
                </tr>
              </thead>
              <tbody>
                {samples.slice(-10).map((point) => (
                  <tr key={point.observed_at}>
                    <td>{point.observed_at}</td>
                    <td>{point.value.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </figure>
      )}
    </section>
  );
}
