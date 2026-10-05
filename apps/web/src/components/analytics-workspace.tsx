"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Pull = components["schemas"]["Pull"];
type Vehicle = components["schemas"]["Vehicle"];
type Configuration = components["schemas"]["VehicleConfiguration"];
type Result = components["schemas"]["AnalyticsResultResponse"];

type NormalizedBin = {
  rpm_start: number;
  rpm_end?: number;
  median?: number | null;
  sample_count?: number;
  unit?: string;
};
type Profile = {
  curves?: Record<string, NormalizedBin[]>;
  event_markers?: Array<{ id: string; event_type: string; rpm: number }>;
  metrics?: Record<string, { median: number; unit: string } | null>;
};
const curveLabels: Record<string, { label: string; unit: string }> = {
  boost: { label: "Boost pressure", unit: "Pa" },
  iat: { label: "Intake air temperature", unit: "K" },
  fuel: { label: "Fuel pressure", unit: "Pa" },
  speed: { label: "Vehicle speed", unit: "m/s" },
  throttle: { label: "Throttle position", unit: "%" },
  acceleration: { label: "Observed acceleration", unit: "m/s²" },
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  if (!response.ok) throw new Error("Analytics request failed");
  return (await response.json()) as T;
}

export function AnalyticsWorkspace({ vehicleId }: { vehicleId?: string }) {
  const [pulls, setPulls] = useState<Pull[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState("comparison");
  const [curveMetric, setCurveMetric] = useState("boost");
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
        const current = vehicleId
          ? vehicles.find((item) => item.id === vehicleId)
          : vehicles[0];
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
  }, [vehicleId]);

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

  async function sessionAnalysis(compare: boolean) {
    const sessions = [
      ...new Set(
        pulls
          .filter((pull) => selected.includes(pull.id))
          .map((pull) => pull.session_id),
      ),
    ];
    if (!sessions.length) return;
    setBusy(true);
    setError("");
    try {
      const parameters = new URLSearchParams();
      sessions.forEach((id) => parameters.append("session_ids", id));
      setResult(
        await request<Result>(
          compare
            ? `/api/domain/analytics/sessions/compare?${parameters}`
            : `/api/domain/sessions/${sessions[0]}/analytics`,
          {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({}),
          },
        ),
      );
      setView(compare ? "cross-session comparison" : "session summary");
    } catch {
      setError("Session analytics are temporarily unavailable.");
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
        session_summary?: {
          duration_seconds?: number;
          telemetry_observation_count?: number;
          event_count?: number;
          segment_counts?: Record<string, number>;
          limitations?: string[];
        };
        metric_deltas?: Record<
          string,
          | {
              absolute?: number | null;
              relative?: number | null;
              unit?: string;
            }
          | Array<{ absolute?: number | null; relative?: number | null }>
        >;
        current_pull_comparison?: {
          boost_bins?: Array<{
            rpm_start: number;
            rpm_end: number;
            observed?: number;
            historical_median?: number;
            absolute_delta?: number;
          }>;
        };
        date_range?: string[];
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
        profiles?: Profile[];
        comparison?: { profiles?: Profile[] };
      }
    | undefined;
  const profiles = payload?.profiles ?? payload?.comparison?.profiles ?? [];

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
      <div className="analytics-tabs">
        <button
          disabled={busy || !selected.length}
          onClick={() => void sessionAnalysis(false)}
        >
          Summarize selected session
        </button>
        <button
          disabled={
            busy ||
            new Set(
              pulls
                .filter((pull) => selected.includes(pull.id))
                .map((pull) => pull.session_id),
            ).size < 2
          }
          onClick={() => void sessionAnalysis(true)}
        >
          Compare selected sessions
        </button>
      </div>
      {result && (
        <div className="analytics-result">
          <h3>
            {view === "comparison"
              ? "RPM-normalized comparison"
              : view === "repeated pulls"
                ? "Repeated-pull progression"
                : view === "session summary"
                  ? "Session summary"
                  : view === "cross-session comparison"
                    ? "Cross-session comparison"
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
          {view === "comparison" && payload?.metric_deltas ? (
            <table>
              <caption>
                Measured differences from the first selected pull
              </caption>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Pull</th>
                  <th>Absolute delta</th>
                  <th>Relative delta</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(payload.metric_deltas).flatMap(
                  ([metric, deltas]) =>
                    Array.isArray(deltas)
                      ? deltas.map((delta, index) => (
                          <tr key={`${metric}-${index}`}>
                            <th>{metric}</th>
                            <td>Pull {index + 1}</td>
                            <td>
                              {delta.absolute?.toFixed(2) ??
                                "Insufficient evidence"}
                            </td>
                            <td>
                              {delta.relative == null
                                ? "Unavailable"
                                : `${(delta.relative * 100).toFixed(2)}%`}
                            </td>
                            <td>
                              {curveLabels[metric]?.unit ?? "Unavailable"}
                            </td>
                          </tr>
                        ))
                      : [],
                )}
              </tbody>
            </table>
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
                  <th>End IAT (K)</th>
                  <th>Boost median (Pa)</th>
                  <th>Fuel minimum (Pa)</th>
                  <th>Speed median (m/s)</th>
                  <th>Acceleration median (m/s²)</th>
                  <th>Events</th>
                </tr>
              </thead>
              <tbody>
                {payload.sequence.map((row) => (
                  <tr key={String(row.pull_id)}>
                    <th>{String(row.index)}</th>
                    <td>{String(row.start_iat ?? "Unavailable")}</td>
                    <td>{String(row.end_iat ?? "Unavailable")}</td>
                    <td>{String(row.median_boost ?? "Unavailable")}</td>
                    <td>
                      {String(row.minimum_fuel_pressure ?? "Unavailable")}
                    </td>
                    <td>{String(row.median_speed ?? "Unavailable")}</td>
                    <td>
                      {String(row.normalized_acceleration ?? "Unavailable")}
                    </td>
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
          {payload?.session_summary ? (
            <dl aria-label="Session analytics summary">
              <dt>Duration</dt>
              <dd>
                {payload.session_summary.duration_seconds ?? "Unavailable"}{" "}
                seconds
              </dd>
              <dt>Canonical observations</dt>
              <dd>
                {payload.session_summary.telemetry_observation_count ?? 0}
              </dd>
              <dt>Factual events</dt>
              <dd>{payload.session_summary.event_count ?? 0}</dd>
              {Object.entries(payload.session_summary.segment_counts ?? {}).map(
                ([kind, count]) => (
                  <div key={kind}>
                    <dt>{kind.replaceAll("_", " ")}</dt>
                    <dd>{count} segments</dd>
                  </div>
                ),
              )}
            </dl>
          ) : null}
          {view === "baseline" ? (
            <>
              <p>
                {payload?.session_count ?? 0} sessions ·{" "}
                {payload?.pull_count ?? 0} contributing pulls ·{" "}
                {payload?.excluded_pull_count ?? 0} excluded
              </p>
              <p>
                Observed history dates:{" "}
                {payload?.date_range
                  ?.map((date) => new Date(date).toLocaleDateString())
                  .join(" – ") ?? "Unavailable"}
              </p>
              {payload?.current_pull_comparison?.boost_bins?.length ? (
                <table>
                  <caption>
                    Latest pull relative to observed history (included in
                    baseline)
                  </caption>
                  <thead>
                    <tr>
                      <th>RPM bin</th>
                      <th>Latest (Pa)</th>
                      <th>Historical median (Pa)</th>
                      <th>Observed delta (Pa)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payload.current_pull_comparison.boost_bins.map((bin) => (
                      <tr key={bin.rpm_start}>
                        <th>
                          {bin.rpm_start}–{bin.rpm_end}
                        </th>
                        <td>{bin.observed ?? "Unavailable"}</td>
                        <td>{bin.historical_median ?? "Unavailable"}</td>
                        <td>{bin.absolute_delta ?? "Unavailable"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
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
              <HistoricalTrend
                segments={payload?.segments_by_configuration ?? {}}
              />
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
              <table>
                <caption>Observed differences in the common RPM window</caption>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>After − before</th>
                    <th>Unit</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(payload?.metric_deltas ?? {}).map(
                    ([metric, delta]) =>
                      !Array.isArray(delta) ? (
                        <tr key={metric}>
                          <th>{metric}</th>
                          <td>
                            {delta.absolute?.toFixed(2) ??
                              "Insufficient comparable evidence"}
                          </td>
                          <td>{delta.unit}</td>
                        </tr>
                      ) : null,
                  )}
                </tbody>
              </table>
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
          <NormalizedCurves
            profiles={profiles}
            metric={curveMetric}
            onMetricChange={setCurveMetric}
          />
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

function HistoricalTrend({
  segments,
}: {
  segments: Record<
    string,
    Array<{ observed_at: string; value: number; unit: string }>
  >;
}) {
  const points = Object.values(segments).flat();
  if (points.length < 2) return null;
  const earliest = Math.min(
    ...points.map((point) => Date.parse(point.observed_at)),
  );
  const latest = Math.max(
    ...points.map((point) => Date.parse(point.observed_at)),
  );
  const low = Math.min(...points.map((point) => point.value));
  const high = Math.max(...points.map((point) => point.value));
  const coordinate = (point: (typeof points)[number]) => ({
    x:
      30 +
      ((Date.parse(point.observed_at) - earliest) /
        Math.max(1, latest - earliest)) *
        640,
    y: 175 - ((point.value - low) / Math.max(1, high - low)) * 140,
  });
  return (
    <figure>
      <svg
        viewBox="0 0 700 220"
        role="img"
        aria-label="Observed history by date, isolated by configuration"
      >
        <title>
          {low.toFixed(1)}–{high.toFixed(1)} {points[0].unit}; each
          configuration has a separate line
        </title>
        {Object.entries(segments).map(([configuration, series], index) => (
          <g key={configuration}>
            <polyline
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeDasharray={index % 2 ? "7 4" : "none"}
              points={series
                .map((point) => {
                  const { x, y } = coordinate(point);
                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                })
                .join(" ")}
            />
            {series.map((point) => {
              const { x, y } = coordinate(point);
              return (
                <circle
                  key={point.observed_at}
                  cx={x}
                  cy={y}
                  r="3"
                  fill="currentColor"
                >
                  <title>
                    {configuration}: {point.observed_at} · {point.value}{" "}
                    {point.unit}
                  </title>
                </circle>
              );
            })}
          </g>
        ))}
      </svg>
      <figcaption>
        Observed history · {points[0].unit} ·{" "}
        {new Date(earliest).toLocaleDateString()}–
        {new Date(latest).toLocaleDateString()} · configurations remain separate
      </figcaption>
    </figure>
  );
}

function NormalizedCurves({
  profiles,
  metric,
  onMetricChange,
}: {
  profiles: Profile[];
  metric: string;
  onMetricChange: (metric: string) => void;
}) {
  const curves = profiles.map((profile) => profile.curves?.[metric] ?? []);
  const valid = curves.flat().filter((bin) => bin.median != null);
  const { label, unit } = curveLabels[metric];
  const low = Math.min(...valid.map((bin) => bin.median as number));
  const high = Math.max(...valid.map((bin) => bin.median as number));
  const first = Math.min(...valid.map((bin) => bin.rpm_start));
  const last = Math.max(...valid.map((bin) => bin.rpm_start));
  const x = (rpm: number) =>
    40 + ((rpm - first) / Math.max(1, last - first)) * 620;
  const y = (value: number) =>
    175 - ((value - low) / Math.max(1, high - low)) * 140;
  return (
    <figure>
      <label htmlFor="analytics-curve">Normalized curve metric</label>
      <select
        id="analytics-curve"
        value={metric}
        onChange={(event) => onMetricChange(event.target.value)}
      >
        {Object.entries(curveLabels).map(([key, item]) => (
          <option key={key} value={key}>
            {item.label} ({item.unit})
          </option>
        ))}
      </select>
      {valid.length ? (
        <>
          <svg
            viewBox="0 0 700 220"
            role="img"
            aria-label={`${label} by RPM; shared axes and distinct pull dash patterns`}
          >
            <title>
              {label}: common RPM axis, {unit}; gaps remain disconnected
            </title>
            <line x1="40" y1="185" x2="660" y2="185" stroke="currentColor" />
            <text x="40" y="207">
              {first} rpm
            </text>
            <text x="580" y="207">
              {last} rpm
            </text>
            <text x="40" y="20">
              {low.toFixed(1)}–{high.toFixed(1)} {unit}
            </text>
            {curves.map((curve, index) => {
              const runs: NormalizedBin[][] = [];
              curve.forEach((bin, binIndex) => {
                if (bin.median == null) return;
                const previous = curve[binIndex - 1];
                if (
                  !previous ||
                  previous.median == null ||
                  (previous.rpm_end != null && bin.rpm_start > previous.rpm_end)
                )
                  runs.push([]);
                runs.at(-1)?.push(bin);
              });
              return (
                <g key={index}>
                  {runs.map((run, runIndex) => (
                    <polyline
                      key={runIndex}
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeDasharray={index ? `${4 + index * 3} 4` : undefined}
                      points={run
                        .map(
                          (bin) =>
                            `${x(bin.rpm_start).toFixed(1)},${y(bin.median as number).toFixed(1)}`,
                        )
                        .join(" ")}
                    />
                  ))}
                  {curve
                    .filter((bin) => bin.median != null)
                    .map((bin) => (
                      <circle
                        key={bin.rpm_start}
                        cx={x(bin.rpm_start)}
                        cy={y(bin.median as number)}
                        r="3"
                        fill="currentColor"
                      >
                        <title>
                          Pull {index + 1}; {bin.rpm_start} rpm: {bin.median}{" "}
                          {unit}; {bin.sample_count ?? "unavailable"} samples
                        </title>
                      </circle>
                    ))}
                  {(profiles[index].event_markers ?? [])
                    .filter((event) => event.rpm >= first && event.rpm <= last)
                    .map((event) => (
                      <line
                        key={event.id}
                        x1={x(event.rpm)}
                        x2={x(event.rpm)}
                        y1="30"
                        y2="185"
                        stroke="currentColor"
                        strokeDasharray="2 3"
                      >
                        <title>
                          Canonical {event.event_type}; {event.rpm} rpm;{" "}
                          {event.id}
                        </title>
                      </line>
                    ))}
                </g>
              );
            })}
          </svg>
          <figcaption>
            {label} ({unit}) vs RPM · all pulls share the same axes
          </figcaption>
          <table>
            <caption>Normalized values, coverage and canonical events</caption>
            <thead>
              <tr>
                <th>Pull / pattern</th>
                <th>RPM bin</th>
                <th>Median ({unit})</th>
                <th>Coverage</th>
              </tr>
            </thead>
            <tbody>
              {curves.flatMap((curve, index) =>
                curve.map((bin) => (
                  <tr key={`${index}-${bin.rpm_start}`}>
                    <th>
                      Pull {index + 1} ·{" "}
                      {index ? `dash ${4 + index * 3}/4` : "solid"}
                    </th>
                    <td>
                      {bin.rpm_start}–{bin.rpm_end ?? "Unavailable"}
                    </td>
                    <td>{bin.median ?? "Insufficient data"}</td>
                    <td>{bin.sample_count ?? "Unavailable"} samples</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
          {profiles.map((profile, index) => (
            <p key={index}>
              Pull {index + 1} canonical events:{" "}
              {(profile.event_markers ?? [])
                .map((event) => event.event_type.replaceAll("_", " "))
                .join(", ") || "None associated"}
            </p>
          ))}
        </>
      ) : (
        <p>
          No normalized {metric} curve is available; insufficient-data gaps are
          not interpolated.
        </p>
      )}
    </figure>
  );
}
