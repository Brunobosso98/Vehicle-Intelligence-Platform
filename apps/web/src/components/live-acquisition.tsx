"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Recipe = components["schemas"]["LoggingRecipeResponse"];
type Preflight = components["schemas"]["PreflightResponse"];

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
  const recipe = recipes.find((item) => item.key === recipeKey);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/domain/logging/recipes", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("recipes unavailable");
        return response.json() as Promise<Recipe[]>;
      })
      .then(setRecipes, () => !controller.signal.aborted && setError(true));
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
