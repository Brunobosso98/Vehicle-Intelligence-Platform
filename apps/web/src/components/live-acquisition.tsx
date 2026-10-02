"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Recipe = components["schemas"]["LoggingRecipeResponse"];
type Preflight = components["schemas"]["PreflightResponse"];
type Vehicle = components["schemas"]["Vehicle"];
type Acquisition = components["schemas"]["AcquisitionCreated"];

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

export function LiveAcquisition() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [recipeKey, setRecipeKey] = useState("performance-pull");
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [error, setError] = useState(false);
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [acquisition, setAcquisition] = useState<Acquisition | null>(null);
  const [liveState, setLiveState] = useState("idle");
  const [latest, setLatest] = useState<Record<string, number>>({});
  const recipe = recipes.find((item) => item.key === recipeKey);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      fetch("/api/domain/logging/recipes", { signal: controller.signal }).then(
        (response) => response.json() as Promise<Recipe[]>,
      ),
      fetch("/api/domain/vehicles", { signal: controller.signal }).then(
        (response) => response.json() as Promise<Vehicle[]>,
      ),
    ]).then(
      ([items, vehicles]) => {
        setRecipes(items);
        setVehicle(vehicles[0] ?? null);
      },
      () => !controller.signal.aborted && setError(true),
    );
    return () => controller.abort();
  }, []);

  async function runPreflight() {
    setError(false);
    const response = await fetch(
      `/api/domain/logging/recipes/${recipeKey}/preflight`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          adapter: "synthetic-live-v1",
          signals: syntheticSignals,
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
    setLiveState("active");
    const stream = new EventSource(`/api/domain/acquisitions/${value.id}/live`);
    stream.addEventListener("telemetry", (event) => {
      const payload = JSON.parse((event as MessageEvent<string>).data) as {
        state: string;
        points: { signal: string; value: number }[];
      };
      setLiveState(payload.state);
      setLatest(
        Object.fromEntries(
          payload.points.map((point) => [point.signal, point.value]),
        ),
      );
      if (["completed", "failed"].includes(payload.state)) stream.close();
    });
    const started = await fetch(
      `/api/domain/acquisitions/${value.id}/synthetic`,
      {
        method: "POST",
        headers: { authorization: `Bearer ${value.ingestion_token}` },
      },
    );
    if (!started.ok) {
      stream.close();
      setError(true);
    }
  }

  async function stopAndFinalize() {
    if (!acquisition) return;
    const stopped = await fetch(
      `/api/domain/acquisitions/${acquisition.id}/stop`,
      {
        method: "POST",
        headers: { authorization: `Bearer ${acquisition.ingestion_token}` },
      },
    );
    if (!stopped.ok) {
      setError(true);
      return;
    }
    setLiveState("finalizing");
    const finalized = await fetch(
      `/api/domain/acquisitions/${acquisition.id}/finalize`,
      { method: "POST" },
    );
    setLiveState(finalized.ok ? "completed" : "failed");
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
      <button type="button" onClick={() => void runPreflight()}>
        Run synthetic device preflight
      </button>
      <button
        type="button"
        disabled={!vehicle || liveState === "active"}
        onClick={() => void startSynthetic()}
      >
        Start synthetic live acquisition
      </button>
      <button
        type="button"
        disabled={!acquisition || liveState !== "active"}
        onClick={() => void stopAndFinalize()}
      >
        Stop and finalize
      </button>
      <div className="readiness" aria-live="polite">
        <strong>Acquisition: {liveState}</strong>
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
          K
        </span>
        <span>
          Live observations are provisional · rolling window 60 seconds
        </span>
      </div>
      {error && (
        <p role="alert">Acquisition planning is temporarily unavailable.</p>
      )}
      {preflight && (
        <div className={`readiness ${preflight.readiness}`} role="status">
          <strong>{preflight.readiness.toUpperCase()}</strong>
          <span>{preflight.sampling_plan.length} signals planned</span>
          <span>
            {preflight.unavailable_capabilities.length
              ? `Unavailable: ${preflight.unavailable_capabilities.join(", ")}`
              : "All requested capabilities available"}
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
