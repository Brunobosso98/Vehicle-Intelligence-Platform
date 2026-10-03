"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Pull = components["schemas"]["Pull"];
type Vehicle = components["schemas"]["Vehicle"];
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

  useEffect(() => {
    const controller = new AbortController();
    void request<Vehicle[]>("/api/domain/vehicles", {
      signal: controller.signal,
    })
      .then((vehicles) =>
        vehicles[0]
          ? request<Pull[]>(
              `/api/domain/pulls?vehicle_id=${vehicles[0].id}&limit=20`,
              {
                signal: controller.signal,
              },
            )
          : [],
      )
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
              : "Repeated-pull progression"}
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
        </article>
      </div>
    </section>
  );
}
