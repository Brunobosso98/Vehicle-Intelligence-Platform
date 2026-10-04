"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Vehicle = components["schemas"]["Vehicle"];
type Session = components["schemas"]["DrivingSession"];
type Window = components["schemas"]["TelemetryWindow"];
type Signal = components["schemas"]["Signal"];
type Segment = components["schemas"]["SessionSegment"];
type Pull = components["schemas"]["Pull"];
type DetectedEvent = components["schemas"]["DetectedEvent"];

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
  const [segments, setSegments] = useState<Segment[]>([]);
  const [pulls, setPulls] = useState<Pull[]>([]);
  const [events, setEvents] = useState<DetectedEvent[]>([]);
  const [activeEvent, setActiveEvent] = useState<DetectedEvent | null>(null);
  const [eventFilter, setEventFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [pullFilter, setPullFilter] = useState("all");
  const [activePull, setActivePull] = useState<Pull | null>(null);
  const [compared, setCompared] = useState<string[]>([]);
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
      void Promise.all([
        json<Segment[]>(
          `/api/domain/sessions/${sessions[0].id}/segments?limit=500`,
          controller.signal,
        ),
        json<Pull[]>(
          `/api/domain/sessions/${sessions[0].id}/pulls?limit=100`,
          controller.signal,
        ),
        json<DetectedEvent[]>(
          `/api/domain/sessions/${sessions[0].id}/events?limit=500`,
          controller.signal,
        ),
      ]).then(
        ([segmentData, pullData, eventData]) => {
          const detectedEvents = Array.isArray(eventData)
            ? eventData.filter(
                (item): item is DetectedEvent =>
                  typeof item === "object" &&
                  item !== null &&
                  "event_type" in item &&
                  typeof item.event_type === "string",
              )
            : [];
          setSegments(segmentData);
          setPulls(pullData);
          setActivePull(pullData[0] ?? null);
          setEvents(detectedEvents);
          setActiveEvent(detectedEvents[0] ?? null);
        },
        () => !controller.signal.aborted && setError(true),
      );
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
    const min = Math.min(...values),
      max = Math.max(...values),
      span = max - min || 1;
    return points
      .map(
        (point, index) =>
          `${(index / (points.length - 1)) * 700},${180 - ((point.value - min) / span) * 150}`,
      )
      .join(" ");
  }, [window]);
  const visibleEvents = events.filter(
    (event) =>
      (eventFilter === "all" || event.event_type === eventFilter) &&
      (categoryFilter === "all" || event.category === categoryFilter) &&
      (severityFilter === "all" || event.severity === severityFilter) &&
      (pullFilter === "all" || event.pull_id === pullFilter),
  );

  return (
    <section className="telemetry-card" aria-labelledby="telemetry-heading">
      <div className="section-label">VEHICLE &amp; TELEMETRY · PHASE 1</div>
      <h2 id="telemetry-heading">Session intelligence</h2>
      {vehicles === null && !error && (
        <p role="status">Loading vehicles and signals…</p>
      )}
      {error && (
        <div role="alert">
          <p>Telemetry could not be loaded.</p>
          <button onClick={() => setAttempt((value) => value + 1)}>
            Retry
          </button>
        </div>
      )}
      {vehicles?.length === 0 && (
        <p>
          No vehicles yet. Create a vehicle and import a session through the
          API.
        </p>
      )}
      {vehicles?.[0] && (
        <>
          <h3>
            {vehicles[0].nickname ??
              `${vehicles[0].manufacturer} ${vehicles[0].model}`}
          </h3>
          <p>
            {vehicles[0].generation} · {vehicles[0].model_year} ·{" "}
            {vehicles[0].engine_code}
          </p>
          {sessions.length === 0 ? (
            <p>No telemetry sessions are available.</p>
          ) : (
            <>
              <dl className="status-list">
                <div>
                  <dt>Source</dt>
                  <dd>{sessions[0].source_type}</dd>
                </div>
                <div>
                  <dt>Samples</dt>
                  <dd>{sessions[0].sample_count}</dd>
                </div>
                <div>
                  <dt>Started</dt>
                  <dd>
                    {sessions[0].started_at
                      ? new Date(sessions[0].started_at).toLocaleString()
                      : "—"}
                  </dd>
                </div>
              </dl>
              <h3>Derived session timeline</h3>
              {segments.length === 0 ? (
                <p>
                  No derived segments yet. Run session analysis through the API.
                </p>
              ) : (
                <ul
                  className="segment-timeline"
                  role="list"
                  aria-label="Driving session segments"
                >
                  {segments.map((segment) => (
                    <li key={segment.id}>
                      <button
                        className={`segment segment-${segment.segment_type}`}
                        title={`${segment.segment_type}, ${segment.duration_ms / 1000} seconds`}
                      >
                        <strong>
                          {segment.segment_type.replace("_", " ")}
                        </strong>
                        <span>{(segment.duration_ms / 1000).toFixed(1)}s</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <h3>Event timeline</h3>
              <label htmlFor="event-filter">Filter by event type</label>
              <select
                id="event-filter"
                value={eventFilter}
                onChange={(event) => setEventFilter(event.target.value)}
              >
                <option value="all">All configured events</option>
                {[...new Set(events.map((event) => event.event_type))].map(
                  (eventType) => (
                    <option key={eventType} value={eventType}>
                      {eventType.replaceAll("_", " ")}
                    </option>
                  ),
                )}
              </select>
              <label htmlFor="category-filter">Filter by category</label>
              <select
                id="category-filter"
                value={categoryFilter}
                onChange={(event) => setCategoryFilter(event.target.value)}
              >
                <option value="all">All categories</option>
                {[...new Set(events.map((event) => event.category))].map(
                  (category) => (
                    <option key={category} value={category}>
                      {category.replaceAll("_", " ")}
                    </option>
                  ),
                )}
              </select>
              <label htmlFor="severity-filter">Filter by severity</label>
              <select
                id="severity-filter"
                value={severityFilter}
                onChange={(event) => setSeverityFilter(event.target.value)}
              >
                <option value="all">All severities</option>
                {[...new Set(events.map((event) => event.severity))].map(
                  (severity) => (
                    <option key={severity} value={severity}>
                      {severity}
                    </option>
                  ),
                )}
              </select>
              <label htmlFor="pull-filter">Filter by pull</label>
              <select
                id="pull-filter"
                value={pullFilter}
                onChange={(event) => setPullFilter(event.target.value)}
              >
                <option value="all">All pulls</option>
                {pulls.map((pull, index) => (
                  <option key={pull.id} value={pull.id}>
                    Pull {index + 1}
                  </option>
                ))}
              </select>
              {visibleEvents.length === 0 ? (
                <p>
                  No configured anomaly events were detected in this session.
                </p>
              ) : (
                <div role="list" aria-label="Detected session events">
                  {visibleEvents.map((event) => (
                    <div key={event.id} role="listitem">
                      <button
                        aria-pressed={activeEvent?.id === event.id}
                        onClick={() => setActiveEvent(event)}
                      >
                        ▲ {event.event_type.replaceAll("_", " ")} ·{" "}
                        {event.severity} · {Math.round(event.confidence * 100)}%
                        confidence
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {activeEvent && (
                <section aria-label="Event inspector">
                  <h4>{activeEvent.event_type.replaceAll("_", " ")}</h4>
                  <dl className="status-list">
                    <div>
                      <dt>Category / severity</dt>
                      <dd>
                        {activeEvent.category} / {activeEvent.severity}
                      </dd>
                    </div>
                    <div>
                      <dt>Time</dt>
                      <dd>
                        {new Date(activeEvent.started_at).toLocaleString()}–
                        {new Date(activeEvent.ended_at).toLocaleTimeString()}
                      </dd>
                    </div>
                    <div>
                      <dt>Detector</dt>
                      <dd>
                        {activeEvent.algorithm_name}{" "}
                        {activeEvent.algorithm_version}
                      </dd>
                    </div>
                    <div>
                      <dt>Baseline</dt>
                      <dd>{activeEvent.baseline_type}</dd>
                    </div>
                    <div>
                      <dt>Quality</dt>
                      <dd>
                        {activeEvent.quality_flags.join(", ") || "complete"}
                      </dd>
                    </div>
                  </dl>
                  <details>
                    <summary>Structured factual evidence</summary>
                    <pre>{JSON.stringify(activeEvent.evidence, null, 2)}</pre>
                  </details>
                </section>
              )}
              <h3>Pull inspector</h3>
              {pulls.length === 0 ? (
                <p>No qualifying acceleration pulls were detected.</p>
              ) : (
                <>
                  <div className="pull-list" aria-label="Detected pulls">
                    {pulls.map((pull, index) => (
                      <div key={pull.id}>
                        <button
                          aria-pressed={activePull?.id === pull.id}
                          onClick={() => setActivePull(pull)}
                        >
                          Pull {index + 1}
                        </button>
                        <label>
                          <input
                            type="checkbox"
                            checked={compared.includes(pull.id)}
                            disabled={
                              !compared.includes(pull.id) &&
                              compared.length >= 3
                            }
                            onChange={() =>
                              setCompared((items) =>
                                items.includes(pull.id)
                                  ? items.filter((id) => id !== pull.id)
                                  : [...items, pull.id],
                              )
                            }
                          />{" "}
                          Compare
                        </label>
                      </div>
                    ))}
                  </div>
                  {activePull && (
                    <>
                      <dl
                        className="status-list"
                        aria-label="Selected pull metrics"
                      >
                        <div>
                          <dt>Duration</dt>
                          <dd>
                            {(activePull.duration_ms / 1000).toFixed(1)} s
                          </dd>
                        </div>
                        <div>
                          <dt>RPM range</dt>
                          <dd>
                            {activePull.start_rpm?.toFixed(0) ?? "—"}–
                            {activePull.end_rpm?.toFixed(0) ?? "—"}
                          </dd>
                        </div>
                        <div>
                          <dt>Speed range</dt>
                          <dd>
                            {activePull.start_speed?.toFixed(1) ?? "—"}–
                            {activePull.end_speed?.toFixed(1) ?? "—"} m/s
                          </dd>
                        </div>
                        <div>
                          <dt>Boost avg / max</dt>
                          <dd>
                            {activePull.average_boost?.toFixed(0) ?? "—"} /{" "}
                            {activePull.max_boost?.toFixed(0) ?? "—"} Pa
                          </dd>
                        </div>
                        <div>
                          <dt>IAT change</dt>
                          <dd>{activePull.iat_delta?.toFixed(1) ?? "—"} K</dd>
                        </div>
                        <div>
                          <dt>Confidence</dt>
                          <dd>
                            {Math.round(activePull.confidence * 100)}% heuristic
                          </dd>
                        </div>
                        <div>
                          <dt>Quality</dt>
                          <dd>
                            {activePull.quality_flags.length
                              ? activePull.quality_flags.join(", ")
                              : "complete"}
                          </dd>
                        </div>
                      </dl>
                      <div aria-label="Events associated with selected pull">
                        <h4>Detected events</h4>
                        {events.filter(
                          (event) => event.pull_id === activePull.id,
                        ).length ? (
                          <ul>
                            {events
                              .filter(
                                (event) => event.pull_id === activePull.id,
                              )
                              .map((event) => (
                                <li key={event.id}>
                                  {event.event_type.replaceAll("_", " ")}
                                </li>
                              ))}
                          </ul>
                        ) : (
                          <p>No configured events for this pull.</p>
                        )}
                      </div>
                    </>
                  )}
                  {compared.length >= 2 && (
                    <div className="comparison" aria-label="Pull comparison">
                      <h4>Factual comparison</h4>
                      <table>
                        <thead>
                          <tr>
                            <th>Pull</th>
                            <th>Duration</th>
                            <th>RPM</th>
                            <th>Max boost</th>
                          </tr>
                        </thead>
                        <tbody>
                          {compared.map((id) => {
                            const pull = pulls.find((item) => item.id === id)!;
                            return (
                              <tr key={id}>
                                <th>{pulls.indexOf(pull) + 1}</th>
                                <td>{(pull.duration_ms / 1000).toFixed(1)}s</td>
                                <td>
                                  {pull.min_rpm?.toFixed(0)}–
                                  {pull.max_rpm?.toFixed(0)}
                                </td>
                                <td>{pull.max_boost?.toFixed(0) ?? "—"}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
              <h3>Raw telemetry</h3>
              <label htmlFor="signal">Signal</label>
              <select
                id="signal"
                value={selected}
                onChange={(event) => {
                  setWindow(null);
                  setSelected(event.target.value);
                }}
              >
                {catalog.map((signal) => (
                  <option key={signal.key} value={signal.key}>
                    {signal.name} ({signal.unit})
                  </option>
                ))}
              </select>
              {window === null ? (
                <p role="status">Loading telemetry…</p>
              ) : window.points.length === 0 ? (
                <p>No points in this time window.</p>
              ) : (
                <figure>
                  <svg
                    viewBox="0 0 700 200"
                    role="img"
                    aria-label={`${selected} time-series chart`}
                  >
                    <polyline
                      points={polyline}
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                    />
                  </svg>
                  <figcaption>
                    {window.returned} points · {window.points[0]?.unit}
                    {window.truncated
                      ? " · bounded response; narrow the window"
                      : ""}
                  </figcaption>
                </figure>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
