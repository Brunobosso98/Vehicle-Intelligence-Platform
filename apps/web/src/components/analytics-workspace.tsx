"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Pull = components["schemas"]["Pull"];
type Vehicle = components["schemas"]["Vehicle"];
type Configuration = components["schemas"]["VehicleConfiguration"];
type Result = components["schemas"]["AnalyticsResultResponse"];

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  if (!response.ok) throw new Error("Analytics request failed");
  return (await response.json()) as T;
}

export function AnalyticsWorkspace() {
  const [pulls, setPulls] = useState<Pull[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState("comparison");
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [configurations, setConfigurations] = useState<Configuration[]>([]);
  const [configurationId, setConfigurationId] = useState("");
  const [beforeConfigurationId, setBeforeConfigurationId] = useState("");
  const [afterConfigurationId, setAfterConfigurationId] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void request<Vehicle[]>("/api/domain/vehicles", {
      signal: controller.signal,
    })
      .then(async (vehicles) => {
        const current = vehicles[0];
        setVehicle(current ?? null);
        if (current) {
          const configs = await request<Configuration[]>(
            `/api/domain/vehicles/${current.id}/configurations`,
            { signal: controller.signal },
          );
          setConfigurations(configs);
          setConfigurationId(configs[0]?.id ?? "");
          setBeforeConfigurationId(configs[1]?.id ?? "");
          setAfterConfigurationId(configs[0]?.id ?? "");
          return request<Pull[]>(
            `/api/domain/pulls?vehicle_id=${current.id}&limit=20`,
            {
              signal: controller.signal,
            },
          );
        }
        return [];
      })
      .then(
        setPulls,
        () =>
          !controller.signal.aborted &&
          setError("Analytics data is unavailable."),
      );
    return () => controller.abort();
  }, []);

  async function analyze(kind: "compare" | "repeated") {
    setBusy(true);
    setError("");
    try {
      setResult(
        await request<Result>(
          `/api/domain/analytics/pulls/${kind === "compare" ? "compare" : "repeated"}`,
          {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ pull_ids: selected }),
          },
        ),
      );
      setView(kind === "compare" ? "comparison" : "repeated pulls");
    } catch {
      setError("The selected pulls could not be compared.");
    } finally {
      setBusy(false);
    }
  }

  async function history(kind: "baseline" | "trend" | "before-after") {
    if (!vehicle) return;
    setBusy(true);
    setError("");
    try {
      let url = `/api/domain/vehicles/${vehicle.id}/trends/boost`;
      let body: Record<string, unknown> = {};
      if (kind === "baseline") {
        url = `/api/domain/vehicles/${vehicle.id}/configurations/${configurationId}/baseline`;
      } else if (kind === "before-after") {
        const [beforePulls, afterPulls] = await Promise.all(
          [beforeConfigurationId, afterConfigurationId].map((configuration) =>
            request<Pull[]>(
              `/api/domain/pulls?${new URLSearchParams({
                vehicle_id: vehicle.id,
                configuration_id: configuration,
                limit: "20",
              })}`,
            ),
          ),
        );
        const beforeIds = beforePulls.map((pull) => pull.id);
        const afterIds = afterPulls.map((pull) => pull.id);
        const query = new URLSearchParams();
        afterIds.forEach((id) => query.append("after_pull_ids", id));
        url = `/api/domain/analytics/configurations/compare?${query}`;
        body = { pull_ids: beforeIds };
      }
      setResult(
        await request<Result>(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body),
        }),
      );
      setView(kind);
    } catch {
      setError(
        "Historical analytics are unavailable for the selected evidence.",
      );
    } finally {
      setBusy(false);
    }
  }

  const payload = result?.result as
    | {
        sufficiency?: string;
        common_rpm_range?: number[];
        limitations?: string[];
        sequence?: Array<Record<string, string | number | null>>;
        repeatability?: Record<
          string,
          { median?: number; mad?: number; iqr?: number }
        >;
        session_count?: number;
        pull_count?: number;
        excluded_pull_count?: number;
        envelopes?: Record<
          string,
          Array<{
            rpm_start: number;
            rpm_end: number;
            median?: number;
            p25?: number;
            p75?: number;
            unit?: string;
          }>
        >;
        segments_by_configuration?: Record<
          string,
          Array<{ observed_at: string; value: number; unit: string }>
        >;
        point_count?: number;
        sample_sizes?: { before: number; after: number };
        before?: { sufficiency?: string; pull_count?: number };
        after?: { sufficiency?: string; pull_count?: number };
        language?: string;
        profiles?: Array<{
          curves?: { boost?: Array<{ rpm_start: number; median?: number }> };
        }>;
      }
    | undefined;
  const curves =
    payload?.profiles?.map((profile) => profile.curves?.boost ?? []) ?? [];

  return (
    <section className="analytics-card" aria-labelledby="analytics-heading">
      <div className="section-label">AUTOMOTIVE ANALYTICS · PHASE 5</div>
      <h2 id="analytics-heading">Analytics workspace</h2>
      <nav aria-label="Analytics views" className="analytics-tabs">
        {[
          "Overview",
          "Sessions",
          "Pulls",
          "Events",
          "Analytics",
          "History",
        ].map((item) => (
          <span key={item}>{item}</span>
        ))}
      </nav>
      <p>
        Compare observed behavior only. Observed association is not root-cause
        diagnosis.
      </p>
      {pulls.length < 2 ? (
        <p role="status">
          Only one or no comparable pull is available. At least 2 are required
          for comparison.
        </p>
      ) : (
        <fieldset>
          <legend>Select 2–3 pulls</legend>
          {pulls.slice(0, 8).map((pull, index) => (
            <label key={pull.id} className="analytics-choice">
              <input
                type="checkbox"
                checked={selected.includes(pull.id)}
                disabled={!selected.includes(pull.id) && selected.length >= 3}
                onChange={() =>
                  setSelected((current) =>
                    current.includes(pull.id)
                      ? current.filter((id) => id !== pull.id)
                      : [...current, pull.id],
                  )
                }
              />
              Pull {index + 1} · {pull.min_rpm?.toFixed(0) ?? "—"}–
              {pull.max_rpm?.toFixed(0) ?? "—"} rpm
            </label>
          ))}
          <button
            disabled={selected.length < 2 || busy}
            onClick={() => void analyze("compare")}
          >
            {busy ? "Calculating…" : "Compare pulls"}
          </button>
          <button
            disabled={selected.length < 2 || busy}
            onClick={() => void analyze("repeated")}
          >
            Analyze repeated pulls
          </button>
        </fieldset>
      )}
      {error && <p role="alert">{error}</p>}
      {result && (
        <div className="analytics-result">
          <h3>
            {view === "comparison"
              ? "RPM-normalized comparison"
              : view === "repeated pulls"
                ? "Repeated-pull progression"
                : view === "baseline"
                  ? "Observed historical baseline"
                  : view === "trend"
                    ? "Configuration-segmented history"
                    : "Observed before/after difference"}
          </h3>
          <dl className="status-list">
            <div>
              <dt>Evidence</dt>
              <dd>{payload?.sufficiency ?? result.status}</dd>
            </div>
            <div>
              <dt>Common RPM</dt>
              <dd>
                {payload?.common_rpm_range?.join("–") ?? "No common window"}
              </dd>
            </div>
            <div>
              <dt>Algorithm</dt>
              <dd>{result.algorithm_version}</dd>
            </div>
            <div>
              <dt>Configuration hash</dt>
              <dd>
                <code>{result.configuration_hash.slice(0, 12)}…</code>
              </dd>
            </div>
          </dl>
          {payload?.limitations?.length ? (
            <p role="status">Limitations: {payload.limitations.join(", ")}</p>
          ) : null}
          {payload?.sequence?.length ? (
            <table>
              <caption>
                Thermal, boost, fuel and performance progression
              </caption>
              <thead>
                <tr>
                  <th>Pull</th>
                  <th>Start IAT (K)</th>
                  <th>Boost median (Pa)</th>
                  <th>Fuel minimum (Pa)</th>
                  <th>Speed median (m/s)</th>
                  <th>Events</th>
                </tr>
              </thead>
              <tbody>
                {payload.sequence.map((row) => (
                  <tr key={String(row.pull_id)}>
                    <th>{String(row.index)}</th>
                    <td>{String(row.start_iat ?? "Unavailable")}</td>
                    <td>{String(row.median_boost ?? "Unavailable")}</td>
                    <td>
                      {String(row.minimum_fuel_pressure ?? "Unavailable")}
                    </td>
                    <td>{String(row.median_speed ?? "Unavailable")}</td>
                    <td>{String(row.event_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {payload?.repeatability ? (
            <dl>
              {Object.entries(payload.repeatability).map(([metric, value]) => (
                <div key={metric}>
                  <dt>{metric.replaceAll("_", " ")} repeatability</dt>
                  <dd>
                    median {value.median ?? "unavailable"}; MAD{" "}
                    {value.mad ?? "unavailable"}; IQR{" "}
                    {value.iqr ?? "unavailable"}
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
          {view === "baseline" ? (
            <>
              <p>
                {payload?.session_count ?? 0} sessions ·{" "}
                {payload?.pull_count ?? 0} contributing pulls ·{" "}
                {payload?.excluded_pull_count ?? 0} excluded
              </p>
              <table>
                <caption>Observed boost RPM-bin envelope</caption>
                <thead>
                  <tr>
                    <th>RPM bin</th>
                    <th>P25</th>
                    <th>Median</th>
                    <th>P75</th>
                    <th>Unit</th>
                  </tr>
                </thead>
                <tbody>
                  {(payload?.envelopes?.boost ?? []).map((bin) => (
                    <tr key={bin.rpm_start}>
                      <th>
                        {bin.rpm_start}–{bin.rpm_end}
                      </th>
                      <td>{bin.p25 ?? "Unavailable"}</td>
                      <td>{bin.median ?? "Unavailable"}</td>
                      <td>{bin.p75 ?? "Unavailable"}</td>
                      <td>{bin.unit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
          {view === "trend" ? (
            <>
              {payload?.segments_by_configuration &&
                Object.entries(payload.segments_by_configuration).map(
                  ([configuration, points]) => (
                    <section key={configuration}>
                      <h4>Configuration {configuration}</h4>
                      <p>{points.length} historical observations</p>
                      <ol>
                        {points.map((point) => (
                          <li key={point.observed_at}>
                            {new Date(point.observed_at).toLocaleDateString()}:{" "}
                            {point.value} {point.unit}
                          </li>
                        ))}
                      </ol>
                    </section>
                  ),
                )}
              {!payload?.point_count ? (
                <p role="status">
                  Insufficient comparable history for this trend.
                </p>
              ) : null}
            </>
          ) : null}
          {view === "before-after" ? (
            <>
              <p>{payload?.language}</p>
              <dl>
                <div>
                  <dt>Before sample</dt>
                  <dd>
                    {payload?.sample_sizes?.before ?? 0} pulls (
                    {payload?.before?.sufficiency ?? "insufficient"})
                  </dd>
                </div>
                <div>
                  <dt>After sample</dt>
                  <dd>
                    {payload?.sample_sizes?.after ?? 0} pulls (
                    {payload?.after?.sufficiency ?? "insufficient"})
                  </dd>
                </div>
              </dl>
            </>
          ) : null}
          {curves.some((curve) =>
            curve.some((point) => point.median != null),
          ) ? (
            <svg
              viewBox="0 0 700 220"
              role="img"
              aria-label="Boost pressure by RPM; each pull uses a distinct dash pattern"
            >
              <title>Boost pressure by RPM-normalized bin</title>
              {curves.map((curve, curveIndex) => {
                const valid = curve.filter((point) => point.median != null);
                const values = valid.map((point) => point.median as number);
                const min = Math.min(...values),
                  max = Math.max(...values),
                  span = max - min || 1;
                return (
                  <polyline
                    key={curveIndex}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeDasharray={
                      curveIndex ? `${4 + curveIndex * 3} 4` : undefined
                    }
                    points={valid
                      .map(
                        (point, index) =>
                          `${40 + index * (620 / Math.max(valid.length - 1, 1))},${190 - (((point.median as number) - min) / span) * 150}`,
                      )
                      .join(" ")}
                  />
                );
              })}
            </svg>
          ) : (
            <p>
              No normalized boost curve is available; insufficient-data gaps are
              not interpolated.
            </p>
          )}
          <details>
            <summary>Analytics provenance</summary>
            <p>
              Run {result.id}; source fingerprint{" "}
              <code>{result.source_fingerprint}</code>; generated{" "}
              {new Date(result.generated_at).toLocaleString()}.
            </p>
          </details>
        </div>
      )}
      <div
        className="analytics-empty-grid"
        aria-label="Historical analytics availability"
      >
        <article>
          <h3>Repeated pulls</h3>
          <p>
            Select pulls and use “Analyze repeated pulls” to inspect thermal,
            repeatability, fuel-pressure and measured performance progression.
          </p>
        </article>
        <article>
          <h3>Observed baseline</h3>
          <label htmlFor="baseline-configuration">Vehicle configuration</label>
          <select
            id="baseline-configuration"
            value={configurationId}
            onChange={(event) => setConfigurationId(event.target.value)}
          >
            {configurations.map((configuration) => (
              <option key={configuration.id} value={configuration.id}>
                {configuration.description}
              </option>
            ))}
          </select>
          <button
            disabled={!configurationId || busy}
            onClick={() => void history("baseline")}
          >
            Build historical baseline
          </button>
          <button
            disabled={!vehicle || busy}
            onClick={() => void history("trend")}
          >
            View boost history
          </button>
          <p>
            Baselines and trends are isolated by configuration and appear only
            after three comparable sessions; contributor counts, versions and
            limitations remain part of provenance.
          </p>
        </article>
        <article>
          <h3>Configuration boundary</h3>
          <p>
            Before/after views report configuration sample counts and factual
            deltas only. They never claim that a modification caused a change.
          </p>
          <label htmlFor="before-configuration">Before configuration</label>
          <select
            id="before-configuration"
            value={beforeConfigurationId}
            disabled={busy}
            onChange={(event) => setBeforeConfigurationId(event.target.value)}
          >
            <option value="">Select configuration</option>
            {configurations.map((configuration) => (
              <option key={configuration.id} value={configuration.id}>
                {configuration.description}
              </option>
            ))}
          </select>
          <label htmlFor="after-configuration">After configuration</label>
          <select
            id="after-configuration"
            value={afterConfigurationId}
            disabled={busy}
            onChange={(event) => setAfterConfigurationId(event.target.value)}
          >
            <option value="">Select configuration</option>
            {configurations.map((configuration) => (
              <option key={configuration.id} value={configuration.id}>
                {configuration.description}
              </option>
            ))}
          </select>
          <button
            disabled={
              !beforeConfigurationId ||
              !afterConfigurationId ||
              beforeConfigurationId === afterConfigurationId ||
              busy
            }
            onClick={() => void history("before-after")}
          >
            Compare configurations
          </button>
        </article>
      </div>
    </section>
  );
}
