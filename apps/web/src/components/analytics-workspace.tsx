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

  useEffect(() => {
    const controller = new AbortController();
    void request<Vehicle[]>("/api/domain/vehicles", { signal: controller.signal })
      .then((vehicles) =>
        vehicles[0]
          ? request<Pull[]>(`/api/domain/pulls?vehicle_id=${vehicles[0].id}&limit=20`, {
              signal: controller.signal,
            })
          : [],
      )
      .then(setPulls, () => !controller.signal.aborted && setError("Analytics data is unavailable."));
    return () => controller.abort();
  }, []);

  async function compare() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await request<Result>("/api/domain/analytics/pulls/compare", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ pull_ids: selected }),
        }),
      );
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
        profiles?: Array<{ curves?: { boost?: Array<{ rpm_start: number; median?: number }> } }>;
      }
    | undefined;
  const curves = payload?.profiles?.map((profile) => profile.curves?.boost ?? []) ?? [];

  return (
    <section className="analytics-card" aria-labelledby="analytics-heading">
      <div className="section-label">AUTOMOTIVE ANALYTICS · PHASE 5</div>
      <h2 id="analytics-heading">Analytics workspace</h2>
      <nav aria-label="Analytics views" className="analytics-tabs">
        {['Overview', 'Sessions', 'Pulls', 'Events', 'Analytics', 'History'].map((item) => <span key={item}>{item}</span>)}
      </nav>
      <p>Compare observed behavior only. Observed association is not root-cause diagnosis.</p>
      {pulls.length < 2 ? (
        <p role="status">Only one or no comparable pull is available. At least 2 are required for comparison.</p>
      ) : (
        <fieldset>
          <legend>Select 2–3 pulls</legend>
          {pulls.slice(0, 8).map((pull, index) => (
            <label key={pull.id} className="analytics-choice">
              <input type="checkbox" checked={selected.includes(pull.id)} disabled={!selected.includes(pull.id) && selected.length >= 3}
                onChange={() => setSelected((current) => current.includes(pull.id) ? current.filter((id) => id !== pull.id) : [...current, pull.id])} />
              Pull {index + 1} · {pull.min_rpm?.toFixed(0) ?? "—"}–{pull.max_rpm?.toFixed(0) ?? "—"} rpm
            </label>
          ))}
          <button disabled={selected.length < 2 || busy} onClick={() => void compare()}>{busy ? "Calculating…" : "Compare pulls"}</button>
        </fieldset>
      )}
      {error && <p role="alert">{error}</p>}
      {result && (
        <div className="analytics-result">
          <h3>RPM-normalized comparison</h3>
          <dl className="status-list">
            <div><dt>Evidence</dt><dd>{payload?.sufficiency ?? result.status}</dd></div>
            <div><dt>Common RPM</dt><dd>{payload?.common_rpm_range?.join("–") ?? "No common window"}</dd></div>
            <div><dt>Algorithm</dt><dd>{result.algorithm_version}</dd></div>
            <div><dt>Configuration hash</dt><dd><code>{result.configuration_hash.slice(0, 12)}…</code></dd></div>
          </dl>
          {payload?.limitations?.length ? <p role="status">Limitations: {payload.limitations.join(", ")}</p> : null}
          {curves.some((curve) => curve.some((point) => point.median != null)) ? (
            <svg viewBox="0 0 700 220" role="img" aria-label="Boost pressure by RPM; each pull uses a distinct dash pattern">
              <title>Boost pressure by RPM-normalized bin</title>
              {curves.map((curve, curveIndex) => {
                const valid = curve.filter((point) => point.median != null);
                const values = valid.map((point) => point.median as number);
                const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
                return <polyline key={curveIndex} fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray={curveIndex ? `${4 + curveIndex * 3} 4` : undefined}
                  points={valid.map((point, index) => `${40 + index * (620 / Math.max(valid.length - 1, 1))},${190 - (((point.median as number) - min) / span) * 150}`).join(" ")} />;
              })}
            </svg>
          ) : <p>No normalized boost curve is available; insufficient-data gaps are not interpolated.</p>}
          <details><summary>Analytics provenance</summary><p>Run {result.id}; source fingerprint <code>{result.source_fingerprint}</code>; generated {new Date(result.generated_at).toLocaleString()}.</p></details>
        </div>
      )}
      <div className="analytics-empty-grid">
        <article><h3>Repeated pulls</h3><p>Thermal progression, repeatability, fuel pressure and acceleration remain factual measurements.</p></article>
        <article><h3>Observed baseline</h3><p>Vehicle/configuration history appears only after three comparable sessions.</p></article>
        <article><h3>Configuration boundary</h3><p>Before/after differences do not establish that a modification caused a change.</p></article>
      </div>
    </section>
  );
}
