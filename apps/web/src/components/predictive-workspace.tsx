"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";

type SessionView = {
  enabled: boolean;
  authenticated: boolean;
  demoEnabled: boolean;
  csrfToken?: string;
  expiresAt?: number;
};
type Prediction = {
  result_type: "next_pull" | "anomaly";
  task: string | null;
  family: string | null;
  horizon: "NEXT_PULL" | "AFTER_PULL_OFFLINE";
  status: string;
  reason_code: string | null;
  receipt_id: string;
  requested_cutoff: string;
  effective_cutoff: string | null;
  source_role: string;
  model_version_id: string | null;
  detector_version_id: string | null;
  feature_set_version: string | null;
  decision: boolean | "ANOMALOUS" | "INLIER" | null;
  engineering_validation_score: number | null;
  anomaly_score: number | null;
  threshold: number | null;
  score_is_probability: false;
  interpretation: string;
  limitation: string;
  quality: {
    quality_class: string;
    observed_feature_count: number;
    expected_feature_count: number;
    coverage: number;
    missing_reason_counts: Record<string, number>;
  };
};
export type HistoryItem = {
  prediction: Prediction;
  recorded_at: string | null;
  vehicle_id: string;
  session_id: string;
  pull_id: string;
  configuration_id: string | null;
  source_type: string | null;
  evidence_available: boolean;
  evidence_completeness: string | null;
  evidence_integrity: string | null;
  captured_binding_state: string;
  current_binding_state: string;
};
type HistoryPage = {
  schema_version: string;
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};
type Evidence = {
  evidence_id: string;
  receipt_id: string;
  score: number | null;
  threshold: number | null;
  source_role: string;
  horizon: string;
  cutoff: string;
  completeness: string;
  integrity: string;
  coverage: number;
  observed_feature_count: number;
  expected_feature_count: number;
  artifact_availability: string;
  available_signals: string[];
  missing_reason_counts: Record<string, number>;
  facts: Array<Record<string, unknown>>;
  gaps: Array<Record<string, unknown>>;
  claims: Array<Record<string, unknown>>;
  limitations: string[];
};
type AgentLink = {
  run_id: string;
  started_at: string;
  status: string;
  source_role: string;
  horizon: string;
  completeness: string;
  integrity: string;
};
type ResearchTask = {
  task: string;
  label: string;
  n: number;
  sessions: number;
  threshold: number;
  selectedMap: string;
  mapForServing: boolean;
  brier: number;
  brierCi: [number, number];
  logLoss: number;
  ece: number;
  eceCi: [number, number];
  auroc: number;
  averagePrecision: number;
  reliability: Array<{
    bin: string;
    meanScore: number;
    observedRate: number;
    rows: number;
    sessions: number;
  }>;
};
type Research = {
  schemaVersion: string;
  protocol: string;
  generator: string;
  featureVersion: string;
  sourceCodeSha: string;
  sourceReceiptSha256: string;
  scope: string;
  servingPromotion: boolean;
  realWorldCalibration: string;
  supervised: ResearchTask[];
  anomaly: Array<{
    family: string;
    label: string;
    methods: Array<{
      name: string;
      cleanAlarms: string;
      crossFamilyAlarms: string;
      targetDetections: string;
      totalAlarms: number;
      scored: number;
    }>;
  }>;
  applicability: {
    driftObservations: number;
    psiComparisons: number;
    psiWarnings: number;
    trainingOnlyOodWarnings: number;
    assessmentCount: number;
    syntheticRows: number;
    labeledRows: number;
    sessions: number;
  };
  limitations: string[];
};
type DemoFixture = {
  schemaVersion: string;
  fixtureVersion: string;
  label: string;
  sourceRole: string;
  vehicleLabel: string;
  vehicleId: string;
  generatedAt: string;
  persistedPrediction: false;
  servingRequest: false;
  items: HistoryItem[];
  evidence: Record<string, Evidence>;
};
type ApiError = { error?: string; code?: string };

const statusLabels: Record<string, string> = {
  READY_SCORE: "Score disponível",
  ABSTAINED_INSUFFICIENT_SIGNAL: "Sem sinal suficiente",
  ABSTAINED_LOW_QUALITY: "Qualidade insuficiente",
  ABSTAINED_INSUFFICIENT_REFERENCE: "Referência insuficiente",
  ABSTAINED_INCOMPATIBLE_CONTEXT: "Contexto incompatível",
  ABSTAINED_UNSUPPORTED_SOURCE: "Origem não suportada",
  ABSTAINED_CUTOFF: "Corte temporal indisponível",
};
const sourceLabels: Record<string, string> = {
  synthetic: "Sintético",
  real_vehicle: "Veículo real — sem validação preditiva",
  imported: "Importado",
  imported_fixture: "Fixture importada",
};

function scoreOf(prediction: Prediction): number | null {
  return prediction.result_type === "next_pull"
    ? prediction.engineering_validation_score
    : prediction.anomaly_score;
}

function exact(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toString()
    : "—";
}

function localTime(value: string | null | undefined): string {
  if (!value) return "Horário indisponível";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "Horário indisponível"
    : new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "medium",
        timeStyle: "medium",
        timeZone: "UTC",
      }).format(date) + " UTC";
}

function formatName(value: string | null | undefined): string {
  if (!value) return "Não disponível";
  return value
    .replaceAll("_", " ")
    .replace(/^NEXT PULL /, "")
    .toLocaleLowerCase("pt-BR");
}

async function responseError(response: Response): Promise<Error> {
  let detail: ApiError = {};
  try {
    detail = (await response.json()) as ApiError;
  } catch {
    /* use the route status below */
  }
  return new Error(
    detail.error ?? `A solicitação falhou (${response.status}).`,
  );
}

export function ScoreChart({
  items,
  heading,
}: {
  items: HistoryItem[];
  heading: string;
}) {
  const scored = items.filter((item) => scoreOf(item.prediction) !== null);
  if (!scored.length)
    return (
      <p className="predictive-empty">
        Nenhum score disponível neste recorte. Abstinências continuam visíveis
        na tabela.
      </p>
    );
  const anomaly = scored[0]?.prediction.result_type === "anomaly";
  const values = scored.map((item) => scoreOf(item.prediction) ?? 0);
  const thresholds = scored
    .map((item) => item.prediction.threshold)
    .filter((value): value is number => value !== null);
  const min = anomaly ? Math.min(0, ...values, ...thresholds) : 0;
  const max = anomaly ? Math.max(1, ...values, ...thresholds) : 1;
  const width = 840;
  const height = 226;
  const left = 64;
  const right = 24;
  const top = 24;
  const bottom = 44;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const yFor = (value: number) =>
    top + plotHeight - ((value - min) / (max - min || 1)) * plotHeight;
  const xFor = (index: number) =>
    left +
    (scored.length === 1
      ? plotWidth / 2
      : (index / (scored.length - 1)) * plotWidth);
  return (
    <figure className="predictive-chart">
      <figcaption>
        <strong>{heading}</strong>
        <span>
          {anomaly
            ? "Anomaly score · scale local à esta família e método"
            : "Engineering-validation score · escala de 0 a 1"}
        </span>
      </figcaption>
      <svg
        role="img"
        aria-labelledby={`chart-title-${chartId(heading)}`}
        aria-describedby={`chart-desc-${chartId(heading)}`}
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={`chart-title-${chartId(heading)}`}>{heading}</title>
        <desc id={`chart-desc-${chartId(heading)}`}>
          {scored.length} resultados históricos ordenados por registro.
          Marcadores tracejados mostram o threshold original de cada receipt;
          nenhum score é uma probabilidade de falha.
        </desc>
        {[0, 0.5, 1].map((fraction) => {
          const y = top + fraction * plotHeight;
          const value = max - fraction * (max - min);
          return (
            <g key={fraction}>
              <line
                className="chart-grid"
                x1={left}
                x2={width - right}
                y1={y}
                y2={y}
              />
              <text
                className="chart-axis"
                x={left - 9}
                y={y + 4}
                textAnchor="end"
              >
                {value.toString()}
              </text>
            </g>
          );
        })}
        {scored.map((item, index) => {
          const threshold = item.prediction.threshold;
          const y = yFor(scoreOf(item.prediction) ?? 0);
          const x = xFor(index);
          const recorded = item.recorded_at ?? item.prediction.requested_cutoff;
          return (
            <g key={item.prediction.receipt_id}>
              {threshold !== null && (
                <line
                  className="chart-threshold"
                  x1={x - 7}
                  x2={x + 7}
                  y1={yFor(threshold)}
                  y2={yFor(threshold)}
                />
              )}
              <circle className="chart-point" cx={x} cy={y} r="5">
                <title>{`${localTime(recorded)} · score ${exact(scoreOf(item.prediction))} · threshold ${exact(threshold)} · ${item.prediction.status}`}</title>
              </circle>
              <text
                className="chart-date"
                x={x}
                y={height - 14}
                textAnchor="middle"
              >{`${index + 1}`}</text>
            </g>
          );
        })}
        <text
          className="chart-axis-title"
          x="14"
          y={height / 2}
          transform={`rotate(-90 14 ${height / 2})`}
        >
          Score
        </text>
      </svg>
      <p className="chart-footnote">
        Pontos em ordem cronológica · traços mostram o threshold original de
        cada receipt · sem interpolação.
      </p>
    </figure>
  );
}

function EvidencePanel({ evidence }: { evidence: Evidence | null }) {
  if (!evidence)
    return (
      <div className="predictive-empty" role="status">
        Esta receipt não tem projeção de evidência disponível. A ausência não
        indica integridade nem resultado normal.
      </div>
    );
  return (
    <div className="evidence-detail">
      <dl className="predictive-metadata">
        <div>
          <dt>Integridade do snapshot</dt>
          <dd>
            <span
              className={`state-pill state-${evidence.integrity.toLowerCase()}`}
            >
              {evidence.integrity}
            </span>
          </dd>
        </div>
        <div>
          <dt>Completude</dt>
          <dd>{evidence.completeness}</dd>
        </div>
        <div>
          <dt>Cutoff efetivo</dt>
          <dd>
            <time dateTime={evidence.cutoff}>{localTime(evidence.cutoff)}</time>
          </dd>
        </div>
        <div>
          <dt>Cobertura de features</dt>
          <dd>
            {exact(evidence.coverage)} · {evidence.observed_feature_count}/
            {evidence.expected_feature_count}
          </dd>
        </div>
        <div>
          <dt>Artefato</dt>
          <dd>{evidence.artifact_availability}</dd>
        </div>
        <div>
          <dt>Sinais disponíveis</dt>
          <dd>
            {evidence.available_signals.length
              ? evidence.available_signals.join(", ")
              : "Nenhum listado"}
          </dd>
        </div>
        <div>
          <dt>Missing signal counts</dt>
          <dd>
            {Object.entries(evidence.missing_reason_counts).length
              ? Object.entries(evidence.missing_reason_counts)
                  .map(([reason, count]) => `${reason}: ${count}`)
                  .join(" · ")
              : "Nenhum sinal ausente registrado"}
          </dd>
        </div>
      </dl>
      {evidence.gaps.length > 0 && (
        <section className="evidence-subsection">
          <h4>Lacunas registradas</h4>
          <ul>
            {evidence.gaps.map((gap, index) => (
              <li key={`${String(gap.code)}-${index}`}>
                {String(gap.code)}
                {gap.reason_code ? ` · ${String(gap.reason_code)}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="evidence-subsection">
        <h4>Fatos de origem e qualidade</h4>
        {evidence.facts.length ? (
          <div className="table-scroll">
            <table className="evidence-table">
              <caption>
                Resumo dos fatos publicados pela projeção segura 9E; o grafo de
                origem permanece no servidor
              </caption>
              <thead>
                <tr>
                  <th scope="col">Fato</th>
                  <th scope="col">Valor</th>
                  <th scope="col">Qualidade</th>
                  <th scope="col">Tipo</th>
                </tr>
              </thead>
              <tbody>
                {evidence.facts.map((fact, index) => (
                  <tr key={String(fact.fact_id ?? index)}>
                    <td data-label="Fato">
                      {String(fact.meaning ?? fact.key ?? "Fato sem descrição")}
                      <small>{String(fact.key ?? "Chave não publicada")}</small>
                    </td>
                    <td data-label="Valor">
                      {fact.value === null || fact.value === undefined
                        ? "Ausente"
                        : String(fact.value)}
                      {fact.unit ? ` ${String(fact.unit)}` : ""}
                    </td>
                    <td data-label="Qualidade">
                      {String(fact.quality ?? "Indisponível")}
                    </td>
                    <td data-label="Tipo">
                      {String(fact.fact_type ?? "Não publicado")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>
            Nenhum fato projetado. A projeção pode estar abstida ou sem dados de
            origem.
          </p>
        )}
      </section>
      {evidence.facts.some((fact) => fact.missing_reason) && (
        <section className="evidence-subsection">
          <h4>Missing observations</h4>
          <ul>
            {evidence.facts
              .filter((fact) => fact.missing_reason)
              .map((fact, index) => (
                <li key={`${String(fact.fact_id ?? index)}-missing`}>
                  {String(fact.key ?? "Signal")}: {String(fact.missing_reason)}
                </li>
              ))}
          </ul>
        </section>
      )}
      {evidence.claims.length > 0 && (
        <section className="evidence-subsection">
          <h4>Vínculos de interpretação</h4>
          <ul>
            {evidence.claims.map((claim, index) => (
              <li key={String(claim.claim_id ?? index)}>
                {String(claim.category ?? "Vínculo")}:{" "}
                {String(claim.template ?? "referência")}
                {Array.isArray(claim.fact_ids)
                  ? ` · ${claim.fact_ids.length} fatos referenciados`
                  : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
      {evidence.limitations.map((limitation) => (
        <p className="science-warning" key={limitation}>
          {limitation}
        </p>
      ))}
      <p className="evidence-fingerprint">
        ID da evidência: <code>{evidence.evidence_id}</code>
      </p>
    </div>
  );
}

export function PredictiveWorkspace({
  initialVehicleId,
  initialReceiptId,
}: {
  initialVehicleId?: string;
  initialReceiptId?: string;
}) {
  const [mode, setMode] = useState<
    "checking" | "disabled" | "signedOut" | "ready" | "failed" | "demo"
  >("checking");
  const [csrf, setCsrf] = useState("");
  const [sessionExpiresAt, setSessionExpiresAt] = useState<number | null>(null);
  const [demoEnabled, setDemoEnabled] = useState(false);
  const [credential, setCredential] = useState("");
  const [loginError, setLoginError] = useState("");
  const [message, setMessage] = useState("");
  const [vehicles, setVehicles] = useState<Array<{ vehicleId: string }>>([]);
  const [vehicleId, setVehicleId] = useState(initialVehicleId ?? "");
  const [history, setHistory] = useState<HistoryPage | null>(null);
  const [selectedReceiptId, setSelectedReceiptId] = useState(
    initialReceiptId ?? "",
  );
  const preferredReceiptId = useRef(initialReceiptId ?? "");
  const [detail, setDetail] = useState<Prediction | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [evidenceState, setEvidenceState] = useState<
    "idle" | "loading" | "missing" | "ready" | "failed"
  >("idle");
  const [agentLinks, setAgentLinks] = useState<AgentLink[]>([]);
  const [detailState, setDetailState] = useState<
    "idle" | "loading" | "missing" | "ready" | "failed" | "mismatch"
  >("idle");
  const [science, setScience] = useState<Research | null>(null);
  const [scienceState, setScienceState] = useState<
    "idle" | "loading" | "ready" | "unavailable"
  >("idle");
  const [demo, setDemo] = useState<DemoFixture | null>(null);
  const [historyState, setHistoryState] = useState<
    "idle" | "loading" | "ready" | "empty" | "failed"
  >("idle");
  const [offset, setOffset] = useState(0);
  const [draftFilters, setDraftFilters] = useState({
    result_kind: "",
    task: "",
    family: "",
    horizon: "",
    source_role: "",
    status: "",
    evidence_completeness: "",
    evidence_integrity: "",
    configuration_id: "",
    session_id: "",
    pull_id: "",
    recorded_from: "",
    recorded_to: "",
  });
  const [filters, setFilters] = useState(draftFilters);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const clearPrivateState = useCallback(() => {
    setVehicles([]);
    setVehicleId("");
    setHistory(null);
    setSelectedReceiptId("");
    setDetail(null);
    setEvidence(null);
    setAgentLinks([]);
    setScience(null);
    setDemo(null);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/predictive/session", {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        const value = (await response.json()) as SessionView;
        setDemoEnabled(value.demoEnabled === true);
        if (!value.enabled) {
          setMode("disabled");
          return;
        }
        if (value.authenticated && value.csrfToken) {
          setCsrf(value.csrfToken);
          setSessionExpiresAt(value.expiresAt ?? Date.now() + 30 * 60 * 1000);
          setMode("ready");
        } else setMode("signedOut");
      })
      .catch(() => !controller.signal.aborted && setMode("failed"));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (mode !== "ready" || sessionExpiresAt === null) return;
    const timeout = window.setTimeout(
      () => {
        clearPrivateState();
        setCsrf("");
        setSessionExpiresAt(null);
        setMode("signedOut");
        setMessage(
          "Sua sessão expirou. Entre novamente para ver dados privados.",
        );
      },
      Math.max(0, sessionExpiresAt - Date.now()),
    );
    return () => window.clearTimeout(timeout);
  }, [mode, sessionExpiresAt, clearPrivateState]);

  useEffect(() => {
    if (mode !== "ready") return;
    const controller = new AbortController();
    void fetch("/api/predictive/vehicles", {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (response.status === 401) throw new Error("SESSION_EXPIRED");
        if (!response.ok) throw await responseError(response);
        const result = (await response.json()) as {
          vehicles: Array<{ vehicleId: string }>;
        };
        setVehicles(result.vehicles);
        setVehicleId((current) =>
          result.vehicles.some((item) => item.vehicleId === current)
            ? current
            : (result.vehicles[0]?.vehicleId ?? ""),
        );
      })
      .catch((error: Error) => {
        if (controller.signal.aborted) return;
        if (error.message === "SESSION_EXPIRED") {
          clearPrivateState();
          setCsrf("");
          setSessionExpiresAt(null);
          setMode("signedOut");
          setMessage(
            "Sua sessão expirou. Entre novamente para ver dados privados.",
          );
        } else setMessage(error.message);
      });
    return () => controller.abort();
  }, [mode, clearPrivateState]);

  useEffect(() => {
    if (mode !== "ready" || !vehicleId) return;
    const controller = new AbortController();
    const params = new URLSearchParams({ limit: "20", offset: String(offset) });
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value);
    }
    if (filters.recorded_from)
      params.set(
        "recorded_from",
        new Date(`${filters.recorded_from}T00:00:00.000Z`).toISOString(),
      );
    if (filters.recorded_to)
      params.set(
        "recorded_to",
        new Date(`${filters.recorded_to}T23:59:59.999Z`).toISOString(),
      );
    void Promise.resolve()
      .then(() => {
        if (controller.signal.aborted) return null;
        setHistoryState("loading");
        setDetail(null);
        setEvidence(null);
        setAgentLinks([]);
        setDetailState("idle");
        return fetch(
          `/api/predictive/vehicles/${encodeURIComponent(vehicleId)}/receipts?${params.toString()}`,
          { cache: "no-store", signal: controller.signal },
        );
      })
      .then(async (response) => {
        if (!response) return null;
        if (response.status === 401) throw new Error("SESSION_EXPIRED");
        if (!response.ok) throw await responseError(response);
        return (await response.json()) as HistoryPage;
      })
      .then((result) => {
        if (controller.signal.aborted || !result) return;
        setHistory(result);
        setHistoryState(result.items.length ? "ready" : "empty");
        const selected = result.items.some(
          (item) => item.prediction.receipt_id === preferredReceiptId.current,
        )
          ? preferredReceiptId.current
          : (result.items[0]?.prediction.receipt_id ?? "");
        preferredReceiptId.current = selected;
        setSelectedReceiptId(selected);
        replaceShareState(vehicleId, selected);
      })
      .catch((error: Error) => {
        if (controller.signal.aborted) return;
        if (error.message === "SESSION_EXPIRED") {
          clearPrivateState();
          setMode("signedOut");
          setMessage(
            "Sua sessão expirou. Entre novamente para ver dados privados.",
          );
        } else {
          setHistoryState("failed");
          setMessage(error.message);
          setHistory(null);
        }
      });
    return () => controller.abort();
  }, [mode, vehicleId, filters, offset, clearPrivateState]);

  const selectedItem =
    history?.items.find(
      (item) => item.prediction.receipt_id === selectedReceiptId,
    ) ?? null;

  useEffect(() => {
    if (mode !== "ready" || !vehicleId || !selectedReceiptId || !selectedItem)
      return;
    const controller = new AbortController();
    const prefix = `/api/predictive/vehicles/${encodeURIComponent(vehicleId)}/receipts/${encodeURIComponent(selectedReceiptId)}`;
    void Promise.resolve()
      .then(() => {
        if (controller.signal.aborted) return null;
        setDetailState("loading");
        setEvidenceState("loading");
        return Promise.all([
          fetch(prefix, { cache: "no-store", signal: controller.signal }),
          fetch(`${prefix}/evidence`, {
            cache: "no-store",
            signal: controller.signal,
          }),
          fetch(`${prefix}/agent-context`, {
            cache: "no-store",
            signal: controller.signal,
          }),
        ]);
      })
      .then(async (responses) => {
        if (!responses) return null;
        const [detailResponse, evidenceResponse, agentResponse] = responses;
        if (
          detailResponse.status === 401 ||
          evidenceResponse.status === 401 ||
          agentResponse.status === 401
        )
          throw new Error("SESSION_EXPIRED");
        if (!detailResponse.ok) throw await responseError(detailResponse);
        const original = (await detailResponse.json()) as Prediction;
        if (controller.signal.aborted) return;
        setDetail(original);
        if (!sameReceipt(selectedItem.prediction, original)) {
          setDetailState("mismatch");
          setEvidenceState("failed");
          setAgentLinks([]);
          setMessage(
            "Os campos da lista e da leitura original não coincidem; valores ocultos por segurança.",
          );
          return null;
        }
        setDetailState("ready");
        if (evidenceResponse.status === 404) {
          setEvidence(null);
          setEvidenceState("missing");
        } else if (evidenceResponse.ok) {
          const projection = (await evidenceResponse.json()) as Evidence;
          if (!evidenceMatches(original, projection)) {
            setEvidence(null);
            setEvidenceState("failed");
          } else {
            setEvidence(projection);
            setEvidenceState("ready");
          }
        } else {
          setEvidence(null);
          setEvidenceState("failed");
        }
        if (agentResponse.ok) {
          const context = (await agentResponse.json()) as {
            items: AgentLink[];
          };
          setAgentLinks(context.items);
        } else setAgentLinks([]);
        return null;
      })
      .catch((error: Error) => {
        if (controller.signal.aborted) return;
        if (error.message === "SESSION_EXPIRED") {
          clearPrivateState();
          setCsrf("");
          setSessionExpiresAt(null);
          setMode("signedOut");
          setMessage(
            "Sua sessão expirou. Entre novamente para ver dados privados.",
          );
        } else {
          setDetailState("failed");
          setEvidenceState("failed");
          setMessage(error.message);
        }
      });
    return () => controller.abort();
  }, [mode, vehicleId, selectedReceiptId, selectedItem, clearPrivateState]);

  const chartGroups = useMemo(() => {
    const groups = new Map<string, { label: string; items: HistoryItem[] }>();
    for (const item of history?.items ?? []) {
      const prediction = item.prediction;
      const identity =
        prediction.result_type === "next_pull"
          ? (prediction.task ?? "task indisponível")
          : `${prediction.family ?? "family indisponível"} · ${prediction.detector_version_id ?? "detector indisponível"}`;
      const key = `${prediction.result_type}:${identity}:${prediction.source_role}`;
      const group = groups.get(key) ?? {
        label: `${formatName(identity)} · ${sourceLabels[prediction.source_role] ?? prediction.source_role}`,
        items: [],
      };
      group.items.push(item);
      groups.set(key, group);
    }
    return [...groups.entries()].map(([key, group]) => ({ key, ...group }));
  }, [history]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginError("");
    const value = credential;
    setCredential("");
    try {
      const response = await fetch("/api/predictive/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ credential: value }),
        cache: "no-store",
      });
      if (!response.ok) throw await responseError(response);
      const result = (await response.json()) as {
        csrfToken: string;
        expiresIn?: number;
      };
      setCsrf(result.csrfToken);
      setSessionExpiresAt(Date.now() + (result.expiresIn ?? 1800) * 1000);
      setMode("ready");
      setMessage("");
    } catch (error) {
      setLoginError(
        error instanceof Error
          ? error.message
          : "Não foi possível autenticar o operador.",
      );
    }
  }

  async function signOut() {
    try {
      const response = await fetch("/api/predictive/auth/logout", {
        method: "POST",
        headers: { "x-csrf-token": csrf },
        cache: "no-store",
      });
      if (!response.ok) throw await responseError(response);
    } catch {
      /* local state is cleared even if the network is unavailable */
    }
    clearPrivateState();
    setCsrf("");
    setSessionExpiresAt(null);
    setMode("signedOut");
    setMessage("Sessão encerrada.");
  }

  async function openDemo() {
    try {
      const response = await fetch("/api/predictive/demo", {
        cache: "no-store",
      });
      if (!response.ok) throw await responseError(response);
      const fixture = (await response.json()) as DemoFixture;
      clearPrivateState();
      setDemo(fixture);
      setMode("demo");
      setMessage("");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Demonstração indisponível.",
      );
    }
  }

  async function openScience() {
    if (science || scienceState === "loading") return;
    setScienceState("loading");
    try {
      const response = await fetch(
        mode === "demo"
          ? "/api/predictive/demo-science"
          : "/api/predictive/evaluation/summary",
        { cache: "no-store" },
      );
      if (!response.ok) throw await responseError(response);
      setScience((await response.json()) as Research);
      setScienceState("ready");
    } catch {
      setScienceState("unavailable");
    }
  }

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setFilters({ ...draftFilters });
  }

  function selectReceipt(receiptId: string) {
    preferredReceiptId.current = receiptId;
    setSelectedReceiptId(receiptId);
    replaceShareState(vehicleId, receiptId);
  }

  const displayItems =
    mode === "demo" ? (demo?.items ?? []) : (history?.items ?? []);
  const currentPrediction =
    mode === "demo"
      ? (displayItems.find(
          (item) => item.prediction.receipt_id === selectedReceiptId,
        )?.prediction ??
        displayItems[0]?.prediction ??
        null)
      : detail;

  return (
    <>
      <a className="skip-link" href="#main">
        Pular para o conteúdo preditivo
      </a>
      <main id="main" className="predictive-main" tabIndex={-1}>
        <header className="predictive-header">
          <Link href="/" className="wordmark">
            N55<span> / INTELLIGENCE LAB</span>
          </Link>
          <div className="predictive-header-actions">
            <span className="phase">PHASE 9H</span>
            {mode === "ready" && (
              <button
                className="button button-quiet"
                type="button"
                onClick={() => void signOut()}
              >
                Encerrar sessão
              </button>
            )}
            {mode === "demo" && (
              <button
                className="button button-quiet"
                type="button"
                onClick={() => window.location.reload()}
              >
                Sair da demonstração
              </button>
            )}
          </div>
        </header>
        <section
          className="predictive-intro"
          aria-labelledby="predictive-title"
        >
          <div>
            <h1 id="predictive-title">Predictive intelligence</h1>
            <p>
              Histórico de resultados de engenharia, sua evidência de origem e
              os limites dos estudos disponíveis.
            </p>
          </div>
          <div className="scope-status">
            <span
              className={`status-dot ${mode === "ready" ? "is-authorized" : mode === "demo" ? "is-demo" : ""}`}
              aria-hidden="true"
            />
            {mode === "ready"
              ? "Operador de teste autorizado"
              : mode === "demo"
                ? "Somente demonstração sintética"
                : mode === "checking"
                  ? "Verificando disponibilidade"
                  : "Visualização privada controlada"}
          </div>
        </section>

        {mode === "checking" && (
          <div className="predictive-loading" role="status">
            <span className="skeleton-line" />
            <span className="skeleton-line short" />
            Carregando estado de acesso…
          </div>
        )}
        {(mode === "disabled" || mode === "signedOut" || mode === "failed") && (
          <section className="operator-gate" aria-labelledby="operator-heading">
            <div className="operator-copy">
              <h2 id="operator-heading">
                Acesso de operador de desenvolvimento
              </h2>
              <p>
                Resultados persistidos ficam disponíveis apenas em ambiente de
                desenvolvimento/teste com autorização do servidor e veículo
                explicitamente permitido. A interface não envia o token do
                Prediction Service ao navegador.
              </p>
              {message && <p role="status">{message}</p>}
            </div>
            {mode === "signedOut" && (
              <form
                className="operator-login"
                onSubmit={(event) => void signIn(event)}
              >
                <label htmlFor="operator-credential">
                  Credencial local do operador
                </label>
                <div className="password-entry">
                  <input
                    id="operator-credential"
                    type={passwordVisible ? "text" : "password"}
                    autoComplete="off"
                    value={credential}
                    onChange={(event) => setCredential(event.target.value)}
                    required
                    maxLength={256}
                  />
                  <button
                    className="button button-quiet"
                    type="button"
                    aria-pressed={passwordVisible}
                    onClick={() => setPasswordVisible((visible) => !visible)}
                  >
                    {passwordVisible ? "Ocultar" : "Mostrar"}
                  </button>
                </div>
                <button className="button button-primary" type="submit">
                  Entrar no workspace
                </button>
                {loginError && (
                  <p className="form-error" role="alert">
                    {loginError}
                  </p>
                )}
              </form>
            )}
            {mode === "failed" && (
              <button
                className="button button-secondary"
                type="button"
                onClick={() => window.location.reload()}
              >
                Tentar novamente
              </button>
            )}
            {demoEnabled && (
              <div className="demo-entry">
                <p>
                  Demonstração isolada com valores fixos e sem conexão ao
                  serviço de previsões.
                </p>
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => void openDemo()}
                >
                  Abrir demonstração sintética
                </button>
              </div>
            )}
          </section>
        )}

        {mode === "ready" && (
          <>
            <section
              className="predictive-toolbar"
              aria-label="Escopo do workspace"
            >
              <label htmlFor="predictive-vehicle">Veículo permitido</label>
              <select
                id="predictive-vehicle"
                value={vehicleId}
                onChange={(event) => {
                  preferredReceiptId.current = "";
                  setHistory(null);
                  setOffset(0);
                  setSelectedReceiptId("");
                  setVehicleId(event.target.value);
                }}
                disabled={!vehicles.length}
              >
                {vehicles.map((item) => (
                  <option value={item.vehicleId} key={item.vehicleId}>
                    {item.vehicleId}
                  </option>
                ))}
              </select>
              <span className="vehicle-reference">
                ID de escopo: <code>{vehicleId || "—"}</code>
              </span>
              {demoEnabled && (
                <button
                  className="button button-quiet"
                  type="button"
                  onClick={() => void openDemo()}
                >
                  Ver demonstração separada
                </button>
              )}
            </section>
            {message && (
              <p className="predictive-notice" role="status">
                {message}
              </p>
            )}
            <nav
              className="predictive-nav"
              aria-label="Seções de inteligência preditiva"
            >
              <a href="#overview">Visão geral</a>
              <a href="#history">Histórico</a>
              <a href="#predictions">9B · Supervisionado</a>
              <a href="#anomalies">9C · Anomalias</a>
              <a href="#evidence">9E · Evidência</a>
              <a href="#science" onClick={() => void openScience()}>
                9G · Pesquisa
              </a>
              <a href="#agent-context">9F · AgentRun</a>
            </nav>
            <section
              id="overview"
              className="predictive-section predictive-overview"
              aria-labelledby="overview-heading"
            >
              <div className="section-heading">
                <div>
                  <h2 id="overview-heading">Visão geral</h2>
                  <p>
                    Observações persistidas para o veículo selecionado. Ausência
                    de receipt não representa condição normal.
                  </p>
                </div>
                <span className="section-source">SOURCE · 9D READ-ONLY</span>
              </div>
              <div className="overview-ledger">
                <div>
                  <span>Receipts nesta página</span>
                  <strong>{history?.items.length ?? "—"}</strong>
                </div>
                <div>
                  <span>Supervisionado · NEXT_PULL</span>
                  <strong>
                    {history?.items.filter(
                      (item) => item.prediction.result_type === "next_pull",
                    ).length ?? "—"}
                  </strong>
                </div>
                <div>
                  <span>Anomalia · AFTER_PULL_OFFLINE</span>
                  <strong>
                    {history?.items.filter(
                      (item) => item.prediction.result_type === "anomaly",
                    ).length ?? "—"}
                  </strong>
                </div>
                <div>
                  <span>Com evidência registrada</span>
                  <strong>
                    {history?.items.filter((item) => item.evidence_available)
                      .length ?? "—"}
                  </strong>
                </div>
              </div>
              <div className="overview-note">
                <span className="note-marker" aria-hidden="true">
                  i
                </span>
                <p>
                  Scores 9B são engineering-validation scores, não
                  probabilidades de falha. Scores 9C são medidas estatísticas,
                  não percentuais de saúde nem diagnóstico. Real-world
                  predictive validity and calibration:{" "}
                  <strong>NOT_ESTABLISHED</strong>.
                </p>
              </div>
            </section>

            <section
              id="history"
              className="predictive-section"
              aria-labelledby="history-heading"
            >
              <div className="section-heading">
                <div>
                  <h2 id="history-heading">Pull e prediction history</h2>
                  <p>
                    Registros ordenados pelo horário persistido, com sessão,
                    pull, source role e estado de vínculo.
                  </p>
                </div>
                <span className="section-source">
                  ATÉ 20 · PAGE {Math.floor(offset / 20) + 1}
                </span>
              </div>
              <form className="history-filters" onSubmit={applyFilters}>
                <label>
                  Tipo de resultado
                  <select
                    value={draftFilters.result_kind}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        result_kind: event.target.value,
                      })
                    }
                  >
                    <option value="">Todos</option>
                    <option value="next_pull">Supervisionado</option>
                    <option value="anomaly">Anomalia</option>
                  </select>
                </label>
                <label>
                  Task 9B
                  <select
                    value={draftFilters.task}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        task: event.target.value,
                      })
                    }
                  >
                    <option value="">Todas</option>
                    <option>NEXT_PULL_FUEL_DEVIATION</option>
                    <option>NEXT_PULL_PERFORMANCE_DEGRADATION</option>
                    <option>NEXT_PULL_THERMAL_DEGRADATION</option>
                  </select>
                </label>
                <label>
                  Family 9C
                  <select
                    value={draftFilters.family}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        family: event.target.value,
                      })
                    }
                  >
                    <option value="">Todas</option>
                    <option value="boost_air">Boost / air</option>
                    <option value="fuel">Fuel</option>
                    <option value="performance">Performance</option>
                    <option value="thermal">Thermal</option>
                  </select>
                </label>
                <label>
                  Horizon
                  <select
                    value={draftFilters.horizon}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        horizon: event.target.value,
                      })
                    }
                  >
                    <option value="">Todos</option>
                    <option value="NEXT_PULL">NEXT_PULL</option>
                    <option value="AFTER_PULL_OFFLINE">
                      AFTER_PULL_OFFLINE
                    </option>
                  </select>
                </label>
                <label>
                  Source role
                  <select
                    value={draftFilters.source_role}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        source_role: event.target.value,
                      })
                    }
                  >
                    <option value="">Todos</option>
                    <option value="synthetic">synthetic</option>
                    <option value="real_vehicle">real_vehicle</option>
                    <option value="imported">imported</option>
                    <option value="imported_fixture">imported_fixture</option>
                  </select>
                </label>
                <label>
                  Status
                  <select
                    value={draftFilters.status}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        status: event.target.value,
                      })
                    }
                  >
                    <option value="">Todos</option>
                    {Object.keys(statusLabels).map((status) => (
                      <option key={status}>{status}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Evidência
                  <select
                    value={draftFilters.evidence_completeness}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        evidence_completeness: event.target.value,
                      })
                    }
                  >
                    <option value="">Qualquer estado</option>
                    <option>COMPLETE</option>
                    <option>PARTIAL</option>
                    <option>ABSTAINED</option>
                  </select>
                </label>
                <label>
                  Integridade
                  <select
                    value={draftFilters.evidence_integrity}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        evidence_integrity: event.target.value,
                      })
                    }
                  >
                    <option value="">Qualquer estado</option>
                    <option>VERIFIED</option>
                    <option>VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE</option>
                    <option>FAILED_SOURCE_MISMATCH</option>
                    <option>NOT_VERIFIABLE</option>
                    <option>UNSUPPORTED_SCHEMA</option>
                  </select>
                </label>
                <label>
                  Configuration ID
                  <input
                    inputMode="text"
                    value={draftFilters.configuration_id}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        configuration_id: event.target.value,
                      })
                    }
                    maxLength={36}
                  />
                </label>
                <label>
                  Session ID
                  <input
                    inputMode="text"
                    value={draftFilters.session_id}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        session_id: event.target.value,
                      })
                    }
                    maxLength={36}
                  />
                </label>
                <label>
                  Pull ID
                  <input
                    inputMode="text"
                    value={draftFilters.pull_id}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        pull_id: event.target.value,
                      })
                    }
                    maxLength={36}
                  />
                </label>
                <label>
                  Registrado desde
                  <input
                    type="date"
                    value={draftFilters.recorded_from}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        recorded_from: event.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Registrado até
                  <input
                    type="date"
                    value={draftFilters.recorded_to}
                    onChange={(event) =>
                      setDraftFilters({
                        ...draftFilters,
                        recorded_to: event.target.value,
                      })
                    }
                  />
                </label>
                <div className="filter-actions">
                  <button className="button button-primary" type="submit">
                    Aplicar filtros
                  </button>
                  <button
                    className="button button-quiet"
                    type="button"
                    onClick={() => {
                      const empty = {
                        result_kind: "",
                        task: "",
                        family: "",
                        horizon: "",
                        source_role: "",
                        status: "",
                        evidence_completeness: "",
                        evidence_integrity: "",
                        configuration_id: "",
                        session_id: "",
                        pull_id: "",
                        recorded_from: "",
                        recorded_to: "",
                      };
                      setDraftFilters(empty);
                      setFilters(empty);
                      setOffset(0);
                    }}
                  >
                    Limpar
                  </button>
                </div>
              </form>
              {historyState === "loading" && (
                <div className="predictive-loading" role="status">
                  <span className="skeleton-line" />
                  <span className="skeleton-line" />
                  <span className="skeleton-line short" />
                  Lendo receipts da API protegida…
                </div>
              )}
              {historyState === "failed" && (
                <div className="predictive-empty" role="alert">
                  Histórico indisponível: {message}
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => setOffset((value) => value)}
                  >
                    Tentar novamente
                  </button>
                </div>
              )}
              {historyState === "empty" && (
                <div className="predictive-empty">
                  <strong>
                    Nenhuma prediction registrada para estes filtros.
                  </strong>
                  <p>
                    Isso indica ausência de receipt neste recorte, não um score
                    zero, ausência de anomalia ou condição saudável.
                  </p>
                  <p>
                    Se não havia binding compatível no source role e horizonte,
                    o serviço não registra uma prediction para a consulta.
                  </p>
                </div>
              )}
              {historyState === "ready" && history && (
                <>
                  <div className="table-scroll">
                    <table className="receipt-table">
                      <caption>
                        Histórico persistido; selecione uma linha para ver o
                        detalhe original
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Registrado</th>
                          <th scope="col">Resultado</th>
                          <th scope="col">Horizon</th>
                          <th scope="col">Score / threshold</th>
                          <th scope="col">Estado</th>
                          <th scope="col">Origem / evidência</th>
                          <th scope="col">Session / pull</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.items.map((item) => {
                          const p = item.prediction;
                          const selected = p.receipt_id === selectedReceiptId;
                          return (
                            <tr
                              key={p.receipt_id}
                              data-receipt-id={p.receipt_id}
                              className={selected ? "is-selected" : undefined}
                              aria-selected={selected}
                            >
                              <td data-label="Registrado">
                                <button
                                  className="table-select"
                                  type="button"
                                  onClick={() => selectReceipt(p.receipt_id)}
                                  aria-current={selected ? "true" : undefined}
                                >
                                  {localTime(item.recorded_at)}
                                </button>
                              </td>
                              <td data-label="Resultado">
                                {p.result_type === "next_pull"
                                  ? formatName(p.task)
                                  : formatName(p.family)}
                              </td>
                              <td data-label="Horizon">
                                <span className="horizon-label">
                                  {p.horizon}
                                </span>
                              </td>
                              <td data-label="Score / threshold">
                                <span className="tabular">
                                  {exact(scoreOf(p))}
                                </span>
                                <small>threshold {exact(p.threshold)}</small>
                              </td>
                              <td data-label="Estado">
                                <span
                                  className={`state-pill ${p.status.startsWith("ABSTAINED") ? "state-warning" : "state-ready"}`}
                                >
                                  {statusLabels[p.status] ?? p.status}
                                </span>
                              </td>
                              <td data-label="Origem / evidência">
                                {sourceLabels[p.source_role] ?? p.source_role}
                                <small>
                                  {item.evidence_available
                                    ? `${item.evidence_completeness ?? "Completude indisponível"} · ${item.evidence_integrity ?? "integridade indisponível"}`
                                    : "Sem projeção 9E"}
                                </small>
                              </td>
                              <td data-label="Session / pull">
                                <code>{item.session_id}</code>
                                <small>
                                  <code>{item.pull_id}</code>
                                </small>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <div className="pagination">
                    <span>
                      {history.total >= 500
                        ? "500+ receipts no limite de consulta"
                        : `${history.total} receipts encontrados`}
                    </span>
                    <div>
                      <button
                        className="button button-secondary"
                        type="button"
                        disabled={offset === 0}
                        onClick={() =>
                          setOffset((value) => Math.max(0, value - 20))
                        }
                      >
                        Anterior
                      </button>
                      <span>Página {Math.floor(offset / 20) + 1}</span>
                      <button
                        className="button button-secondary"
                        type="button"
                        disabled={!history.has_more || offset >= 500}
                        onClick={() =>
                          setOffset((value) => Math.min(500, value + 20))
                        }
                      >
                        Próxima
                      </button>
                    </div>
                  </div>
                </>
              )}
            </section>

            <section
              id="predictions"
              className="predictive-section"
              aria-labelledby="prediction-heading"
            >
              <div className="section-heading">
                <div>
                  <h2 id="prediction-heading">Phase 9B · Supervised results</h2>
                  <p>
                    Três tasks NEXT_PULL. Scores mantêm threshold, source role,
                    versão e cutoff da receipt.
                  </p>
                </div>
              </div>
              {chartGroups
                .filter(
                  (group) =>
                    group.items[0]?.prediction.result_type === "next_pull",
                )
                .map((group) => (
                  <ScoreChart
                    key={group.key}
                    heading={group.label}
                    items={group.items}
                  />
                ))}
              <div className="scientific-callout">
                <strong>Interpretação permitida</strong>
                <p>
                  Engineering-validation score dentro do escopo e dos dados
                  registrados. Não representa probabilidade de falha mecânica,
                  risco de segurança ou diagnóstico de componente.
                </p>
              </div>
            </section>

            <section
              id="anomalies"
              className="predictive-section"
              aria-labelledby="anomaly-heading"
            >
              <div className="section-heading">
                <div>
                  <h2 id="anomaly-heading">Phase 9C · Statistical anomalies</h2>
                  <p>
                    Horizon AFTER_PULL_OFFLINE. Cada family, método e versão tem
                    escala própria.
                  </p>
                </div>
              </div>
              {chartGroups
                .filter(
                  (group) =>
                    group.items[0]?.prediction.result_type === "anomaly",
                )
                .map((group) => (
                  <ScoreChart
                    key={group.key}
                    heading={group.label}
                    items={group.items}
                  />
                ))}
              <div className="scientific-callout">
                <strong>Saída estatística</strong>
                <p>
                  Um score ou flag não identifica turbo, bomba de combustível,
                  intercooler ou outro componente. A detecção de anomalia não é
                  diagnóstico.
                </p>
              </div>
            </section>

            <section
              id="evidence"
              className="predictive-section"
              aria-labelledby="evidence-heading"
            >
              <div className="section-heading">
                <div>
                  <h2 id="evidence-heading">Phase 9E · Evidence provenance</h2>
                  <p>
                    Projeção segura vinculada à receipt selecionada. Integridade
                    do snapshot e completude são estados diferentes.
                  </p>
                </div>
                {currentPrediction && (
                  <span className="section-source">
                    RECEIPT · <code>{currentPrediction.receipt_id}</code>
                  </span>
                )}
              </div>
              {!selectedReceiptId && (
                <div className="predictive-empty">
                  Selecione uma receipt histórica para examinar sua evidência.
                </div>
              )}
              {detailState === "loading" && (
                <div className="predictive-loading" role="status">
                  <span className="skeleton-line" />
                  Lendo detalhe e projeção de evidência…
                </div>
              )}
              {detailState === "mismatch" && (
                <div className="source-mismatch" role="alert">
                  <strong>Source mismatch — valores ocultos</strong>
                  <p>
                    Os campos retornados não coincidem com a receipt original.
                    Nenhum score ou evidência divergente será mostrado.
                  </p>
                </div>
              )}
              {detailState === "failed" && (
                <div className="predictive-empty" role="alert">
                  Detalhe original indisponível: {message}
                </div>
              )}
              {detailState === "ready" && currentPrediction && (
                <>
                  <PredictionDetail
                    prediction={currentPrediction}
                    item={selectedItem}
                  />
                  {evidenceState === "loading" && (
                    <div role="status">Projeção 9E carregando…</div>
                  )}
                  {evidenceState === "failed" && (
                    <div className="source-mismatch" role="alert">
                      Projeção não confere com o escopo da receipt. Detalhes
                      foram ocultados.
                    </div>
                  )}
                  {evidenceState === "missing" && (
                    <EvidencePanel evidence={null} />
                  )}
                  {evidenceState === "ready" && (
                    <EvidencePanel evidence={evidence} />
                  )}
                </>
              )}
            </section>

            <section
              id="science"
              className="predictive-section"
              aria-labelledby="science-heading"
            >
              <div className="section-heading">
                <div>
                  <h2 id="science-heading">Phase 9G · Synthetic research</h2>
                  <p>
                    Relatórios offline, congelados e separados dos resultados do
                    veículo selecionado.
                  </p>
                </div>
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => void openScience()}
                >
                  {science
                    ? "Pesquisa carregada"
                    : "Carregar resumo científico"}
                </button>
              </div>
              {scienceState === "loading" && (
                <div className="predictive-loading" role="status">
                  Carregando snapshot versionado…
                </div>
              )}
              {scienceState === "unavailable" && (
                <div className="predictive-empty" role="status">
                  Snapshot de pesquisa indisponível. Nenhuma métrica sintética
                  foi usada como substituta.
                </div>
              )}
              {science && <ResearchPanel research={science} />}
            </section>

            <section
              id="agent-context"
              className="predictive-section"
              aria-labelledby="agent-heading"
            >
              <div className="section-heading">
                <div>
                  <h2 id="agent-heading">Phase 9F · AgentRun context</h2>
                  <p>
                    Investigações pré-existentes com vínculo persistido à
                    evidence receipt selecionada. A abertura do workspace não
                    cria uma nova execução.
                  </p>
                </div>
              </div>
              {detailState !== "ready" && (
                <div className="predictive-empty">
                  Selecione uma receipt para verificar vínculos de investigação.
                </div>
              )}
              {detailState === "ready" && agentLinks.length === 0 && (
                <div className="predictive-empty">
                  Nenhum AgentRun pré-existente está vinculado a esta receipt.
                </div>
              )}
              {detailState === "ready" && agentLinks.length > 0 && (
                <ul className="agent-links">
                  {agentLinks.map((link) => (
                    <li key={link.run_id}>
                      <div>
                        <strong>{localTime(link.started_at)}</strong>
                        <span>
                          {link.status} · {link.source_role} · {link.horizon} ·{" "}
                          {link.completeness}
                        </span>
                      </div>
                      <Link
                        href={`/?vehicleId=${encodeURIComponent(vehicleId)}&agentRunId=${encodeURIComponent(link.run_id)}#agent-workspace`}
                      >
                        Abrir investigação existente <code>{link.run_id}</code>
                      </Link>
                      <small>
                        Integridade vinculada: {link.integrity}. A resposta do
                        AgentRun é contexto de engenharia, não diagnóstico.
                      </small>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}

        {mode === "demo" && demo && (
          <DemoWorkspace
            fixture={demo}
            onScience={() => void openScience()}
            science={science}
            scienceState={scienceState}
          />
        )}
        <footer className="predictive-footer">
          <span>Vehicle Intelligence Platform · Phase 9H</span>
          <p>
            Somente observação e análise. Sem controle de ECU, inferência
            automática ou geração de novas predictions.
          </p>
          <Link href="/">Voltar ao workspace do veículo</Link>
        </footer>
      </main>
    </>
  );
}

function chartId(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function sameReceipt(left: Prediction, right: Prediction): boolean {
  return (
    left.receipt_id === right.receipt_id &&
    left.result_type === right.result_type &&
    left.task === right.task &&
    left.family === right.family &&
    left.horizon === right.horizon &&
    left.status === right.status &&
    left.source_role === right.source_role &&
    left.requested_cutoff === right.requested_cutoff &&
    left.effective_cutoff === right.effective_cutoff &&
    left.engineering_validation_score === right.engineering_validation_score &&
    left.anomaly_score === right.anomaly_score &&
    left.threshold === right.threshold &&
    left.decision === right.decision
  );
}

function PredictionDetail({
  prediction,
  item,
}: {
  prediction: Prediction;
  item: HistoryItem | null;
}) {
  const score = scoreOf(prediction);
  return (
    <div className="prediction-detail">
      <div className="prediction-result-line">
        <div>
          <span className="record-label">
            {prediction.result_type === "next_pull"
              ? "PHASE 9B · SUPERVISED"
              : "PHASE 9C · STATISTICAL"}
          </span>
          <h3>{formatName(prediction.task ?? prediction.family)}</h3>
        </div>
        <span
          className={`state-pill ${prediction.status.startsWith("ABSTAINED") ? "state-warning" : "state-ready"}`}
        >
          {statusLabels[prediction.status] ?? prediction.status}
        </span>
      </div>
      {prediction.status.startsWith("ABSTAINED") ? (
        <div className="abstention-note">
          <strong>No score was produced.</strong>
          <span>
            {prediction.reason_code ?? "Reason not recorded"}. Abstention is
            unavailable evidence, not a zero or normal reading.
          </span>
        </div>
      ) : (
        <div className="exact-score">
          <span>
            {prediction.result_type === "next_pull"
              ? "Engineering-validation score"
              : "Anomaly score · scale local ao método"}
          </span>
          <strong className="tabular">{exact(score)}</strong>
          <span className="score-threshold">
            Original threshold{" "}
            <strong className="tabular">{exact(prediction.threshold)}</strong>
          </span>
        </div>
      )}
      <dl className="predictive-metadata">
        <div>
          <dt>Horizon</dt>
          <dd>{prediction.horizon}</dd>
        </div>
        <div>
          <dt>Source role</dt>
          <dd>
            {sourceLabels[prediction.source_role] ?? prediction.source_role}
          </dd>
        </div>
        <div>
          <dt>Requested cutoff</dt>
          <dd>
            <time dateTime={prediction.requested_cutoff}>
              {localTime(prediction.requested_cutoff)}
            </time>
          </dd>
        </div>
        <div>
          <dt>Effective cutoff</dt>
          <dd>
            {prediction.effective_cutoff ? (
              <time dateTime={prediction.effective_cutoff}>
                {localTime(prediction.effective_cutoff)}
              </time>
            ) : (
              "Indisponível"
            )}
          </dd>
        </div>
        <div>
          <dt>Model / detector</dt>
          <dd>
            <code>
              {prediction.model_version_id ??
                prediction.detector_version_id ??
                "Não registrado"}
            </code>
          </dd>
        </div>
        <div>
          <dt>Feature version</dt>
          <dd>
            <code>{prediction.feature_set_version ?? "Não materializada"}</code>
          </dd>
        </div>
        <div>
          <dt>Quality</dt>
          <dd>
            {prediction.quality.quality_class} ·{" "}
            {prediction.quality.observed_feature_count}/
            {prediction.quality.expected_feature_count} · coverage{" "}
            {exact(prediction.quality.coverage)}
          </dd>
        </div>
        <div>
          <dt>Missing signal counts</dt>
          <dd>
            {Object.entries(prediction.quality.missing_reason_counts).length
              ? Object.entries(prediction.quality.missing_reason_counts)
                  .map(([reason, count]) => `${reason}: ${count}`)
                  .join(" · ")
              : "Nenhum sinal ausente registrado"}
          </dd>
        </div>
        <div>
          <dt>Binding captured / current</dt>
          <dd>
            {item?.captured_binding_state ?? "Indisponível"} /{" "}
            {item?.current_binding_state ?? "Indisponível"}
          </dd>
        </div>
        <div>
          <dt>Recorded</dt>
          <dd>{localTime(item?.recorded_at)}</dd>
        </div>
      </dl>
      <div className="interpretation-note">
        <strong>Interpretação registrada</strong>
        <p>{prediction.interpretation}</p>
        <p>{prediction.limitation}</p>
        <small>
          Receipt: <code>{prediction.receipt_id}</code>
        </small>
      </div>
    </div>
  );
}

function evidenceMatches(prediction: Prediction, evidence: Evidence): boolean {
  const score =
    prediction.result_type === "next_pull"
      ? prediction.engineering_validation_score
      : prediction.anomaly_score;
  return (
    evidence.receipt_id === prediction.receipt_id &&
    evidence.source_role === prediction.source_role &&
    evidence.horizon === prediction.horizon &&
    evidence.cutoff ===
      (prediction.effective_cutoff ?? prediction.requested_cutoff) &&
    evidence.integrity !== undefined &&
    evidence.completeness !== undefined &&
    evidence.score === score &&
    evidence.threshold === prediction.threshold
  );
}

function replaceShareState(vehicleId: string, receiptId: string) {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  url.searchParams.set("vehicleId", vehicleId);
  if (receiptId) url.searchParams.set("receiptId", receiptId);
  else url.searchParams.delete("receiptId");
  window.history.replaceState(null, "", url);
}

function ResearchPanel({ research }: { research: Research }) {
  return (
    <div className="research-report">
      <div className="research-banner">
        <strong>ESTUDO SINTÉTICO · NÃO É CALIBRAÇÃO DE PRODUÇÃO</strong>
        <span>
          Real-world calibration: {research.realWorldCalibration} · serving
          promotion: {research.servingPromotion ? "yes" : "no"}
        </span>
      </div>
      <dl className="research-provenance">
        <div>
          <dt>Protocol</dt>
          <dd>{research.protocol}</dd>
        </div>
        <div>
          <dt>Generator</dt>
          <dd>{research.generator}</dd>
        </div>
        <div>
          <dt>Features</dt>
          <dd>{research.featureVersion}</dd>
        </div>
        <div>
          <dt>Code SHA</dt>
          <dd>
            <code>{research.sourceCodeSha}</code>
          </dd>
        </div>
        <div>
          <dt>Acceptance receipt SHA256</dt>
          <dd>
            <code>{research.sourceReceiptSha256}</code>
          </dd>
        </div>
      </dl>
      <section className="research-subsection">
        <h3>Calibration summary · Phase 9B tasks</h3>
        <p>
          Held-out generated labels only. Selected maps remain marked{" "}
          <code>not_for_serving</code>.
        </p>
        <div className="table-scroll">
          <table>
            <caption>
              Test metrics and original frozen thresholds for synthetic test
              cohorts
            </caption>
            <thead>
              <tr>
                <th scope="col">Task</th>
                <th scope="col">n / sessions</th>
                <th scope="col">Threshold</th>
                <th scope="col">Brier (95% CI)</th>
                <th scope="col">Log loss</th>
                <th scope="col">ECE (95% CI)</th>
                <th scope="col">AUROC</th>
                <th scope="col">Avg precision</th>
                <th scope="col">Research map</th>
              </tr>
            </thead>
            <tbody>
              {research.supervised.map((task) => (
                <tr key={task.task}>
                  <th scope="row">{task.label}</th>
                  <td>
                    {task.n} / {task.sessions}
                  </td>
                  <td className="tabular">{exact(task.threshold)}</td>
                  <td className="tabular">
                    {exact(task.brier)} ({exact(task.brierCi[0])}–
                    {exact(task.brierCi[1])})
                  </td>
                  <td className="tabular">{exact(task.logLoss)}</td>
                  <td className="tabular">
                    {exact(task.ece)} ({exact(task.eceCi[0])}–
                    {exact(task.eceCi[1])})
                  </td>
                  <td className="tabular">{exact(task.auroc)}</td>
                  <td className="tabular">{exact(task.averagePrecision)}</td>
                  <td>{task.selectedMap} · not for serving</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {research.supervised.map((task) => (
          <details className="reliability-details" key={task.task}>
            <summary>
              {task.label}: reliability bins (descriptive; &lt;20 sessions per
              bin)
            </summary>
            <div className="table-scroll">
              <table>
                <caption>
                  {task.label} calibration reliability bins; no bin-level
                  confidence intervals
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Score band</th>
                    <th scope="col">Mean score</th>
                    <th scope="col">Observed synthetic label rate</th>
                    <th scope="col">Rows / sessions</th>
                  </tr>
                </thead>
                <tbody>
                  {task.reliability.map((bin) => (
                    <tr key={bin.bin}>
                      <th scope="row">{bin.bin}</th>
                      <td className="tabular">{exact(bin.meanScore)}</td>
                      <td className="tabular">{exact(bin.observedRate)}</td>
                      <td>
                        {bin.rows} / {bin.sessions}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        ))}
      </section>
      <section className="research-subsection">
        <h3>Synthetic alarm accounting · Phase 9C</h3>
        <div className="table-scroll">
          <table>
            <caption>
              Case counts from the registered synthetic stress matrix; methods
              retain separate score scales
            </caption>
            <thead>
              <tr>
                <th scope="col">Family</th>
                <th scope="col">Method</th>
                <th scope="col">Clean alarms</th>
                <th scope="col">Cross-family alarms</th>
                <th scope="col">Target detections</th>
                <th scope="col">Total alarms</th>
                <th scope="col">Scored / 30</th>
              </tr>
            </thead>
            <tbody>
              {research.anomaly.flatMap((family) =>
                family.methods.map((method) => (
                  <tr key={`${family.family}-${method.name}`}>
                    <th scope="row">{family.label}</th>
                    <td>{method.name}</td>
                    <td>{method.cleanAlarms}</td>
                    <td>{method.crossFamilyAlarms}</td>
                    <td>{method.targetDetections}</td>
                    <td>{method.totalAlarms}</td>
                    <td>{method.scored}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </section>
      <section className="research-subsection">
        <h3>Applicability and drift</h3>
        <dl className="research-provenance">
          <div>
            <dt>Drift observations</dt>
            <dd>{research.applicability.driftObservations}</dd>
          </div>
          <div>
            <dt>PSI warnings</dt>
            <dd>
              {research.applicability.psiWarnings} /{" "}
              {research.applicability.psiComparisons}
            </dd>
          </div>
          <div>
            <dt>Training-only OOD warnings</dt>
            <dd>{research.applicability.trainingOnlyOodWarnings}</dd>
          </div>
          <div>
            <dt>Applicability assessments</dt>
            <dd>{research.applicability.assessmentCount}</dd>
          </div>
          <div>
            <dt>Rows / labels / sessions</dt>
            <dd>
              {research.applicability.syntheticRows} /{" "}
              {research.applicability.labeledRows} /{" "}
              {research.applicability.sessions}
            </dd>
          </div>
        </dl>
      </section>
      <div className="science-warning">
        <strong>NOT_ESTABLISHED:</strong> dados reais não têm outcomes
        verificados neste estudo. Métricas sintéticas não estimam probabilidade
        de falha mecânica, calibração real, segurança ou validade fora do
        conjunto avaliado. Cada família e método de anomalia mantém escala
        própria.
      </div>
    </div>
  );
}

function DemoWorkspace({
  fixture,
  onScience,
  science,
  scienceState,
}: {
  fixture: DemoFixture;
  onScience: () => void;
  science: Research | null;
  scienceState: "idle" | "loading" | "ready" | "unavailable";
}) {
  const [selected, setSelected] = useState(
    fixture.items[0]?.prediction.receipt_id ?? "",
  );
  const item =
    fixture.items.find((entry) => entry.prediction.receipt_id === selected) ??
    fixture.items[0];
  const prediction = item?.prediction;
  const score = prediction ? scoreOf(prediction) : null;
  const evidence = prediction
    ? (fixture.evidence[prediction.receipt_id] ?? null)
    : null;
  const groups = new Map<string, { heading: string; items: HistoryItem[] }>();
  for (const entry of fixture.items) {
    const current = entry.prediction;
    const identity =
      current.result_type === "next_pull"
        ? (current.task ?? "task unavailable")
        : `${current.family ?? "family unavailable"} · ${current.detector_version_id ?? "detector unavailable"}`;
    const key = `${current.result_type}:${identity}`;
    const group = groups.get(key) ?? {
      heading: `${formatName(identity)} · synthetic demonstration`,
      items: [],
    };
    group.items.push(entry);
    groups.set(key, group);
  }
  return (
    <>
      <div className="demo-banner" role="status">
        <strong>{fixture.label}</strong>
        <span>
          Fixture {fixture.fixtureVersion} · {fixture.vehicleLabel}
        </span>
        <p>
          Estes valores são fixos, não persistidos e não vêm de um veículo. A
          demonstração não chama 9D/9E, não usa token de operador e não
          substitui dados privados ausentes.
        </p>
      </div>
      <section id="overview" className="predictive-section">
        <div className="section-heading">
          <div>
            <h2>Visão geral · demonstração</h2>
            <p>
              Veículo sintético: {fixture.vehicleId} · source role:{" "}
              {fixture.sourceRole}.
            </p>
          </div>
          <span className="section-source">{fixture.fixtureVersion}</span>
        </div>
        <div className="overview-ledger">
          <div>
            <span>Exemplos fixos</span>
            <strong>{fixture.items.length}</strong>
          </div>
          <div>
            <span>Persistidos</span>
            <strong>Não</strong>
          </div>
          <div>
            <span>Requests de serving</span>
            <strong>0</strong>
          </div>
          <div>
            <span>Horário de fixture</span>
            <strong>{localTime(fixture.generatedAt)}</strong>
          </div>
        </div>
      </section>
      <section id="history" className="predictive-section">
        <div className="section-heading">
          <div>
            <h2>Pull e result history</h2>
            <p>
              Dados demonstrativos com IDs próprios, separados de qualquer
              receipt persistida.
            </p>
          </div>
        </div>
        {[...groups.values()].map((group) => (
          <ScoreChart
            key={group.heading}
            items={group.items}
            heading={group.heading}
          />
        ))}
        <div className="table-scroll">
          <table className="receipt-table">
            <caption>
              Fixture sintética de demonstração; nenhum item é uma receipt real
            </caption>
            <thead>
              <tr>
                <th scope="col">Registrado</th>
                <th scope="col">Resultado</th>
                <th scope="col">Horizon</th>
                <th scope="col">Score / threshold</th>
                <th scope="col">Estado</th>
                <th scope="col">Source role</th>
              </tr>
            </thead>
            <tbody>
              {fixture.items.map((entry) => {
                const p = entry.prediction;
                return (
                  <tr
                    key={p.receipt_id}
                    className={
                      selected === p.receipt_id ? "is-selected" : undefined
                    }
                  >
                    <td data-label="Registrado">
                      <button
                        type="button"
                        className="table-select"
                        onClick={() => setSelected(p.receipt_id)}
                      >
                        {localTime(entry.recorded_at)}
                      </button>
                    </td>
                    <td data-label="Resultado">
                      {formatName(p.task ?? p.family)}
                    </td>
                    <td data-label="Horizon">{p.horizon}</td>
                    <td data-label="Score / threshold">
                      {exact(scoreOf(p))}
                      <small>threshold {exact(p.threshold)}</small>
                    </td>
                    <td data-label="Estado">
                      {statusLabels[p.status] ?? p.status}
                    </td>
                    <td data-label="Source role">synthetic</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {prediction && (
          <div className="demo-record">
            <div className="section-heading">
              <div>
                <h3>{formatName(prediction.task ?? prediction.family)}</h3>
                <p>
                  Exemplo{" "}
                  {prediction.result_type === "next_pull"
                    ? "supervisionado"
                    : "estatístico"}{" "}
                  · {prediction.horizon}
                </p>
              </div>
              <span className="state-pill">
                {statusLabels[prediction.status] ?? prediction.status}
              </span>
            </div>
            <dl className="predictive-metadata">
              <div>
                <dt>Score exato</dt>
                <dd>{exact(score)}</dd>
              </div>
              <div>
                <dt>Threshold original</dt>
                <dd>{exact(prediction.threshold)}</dd>
              </div>
              <div>
                <dt>Model / detector version</dt>
                <dd>
                  <code>
                    {prediction.model_version_id ??
                      prediction.detector_version_id ??
                      "—"}
                  </code>
                </dd>
              </div>
              <div>
                <dt>Requested cutoff</dt>
                <dd>{localTime(prediction.requested_cutoff)}</dd>
              </div>
              <div>
                <dt>Effective cutoff</dt>
                <dd>{localTime(prediction.effective_cutoff)}</dd>
              </div>
              <div>
                <dt>Qualidade</dt>
                <dd>
                  {prediction.quality.quality_class} ·{" "}
                  {exact(prediction.quality.coverage)}
                </dd>
              </div>
            </dl>
            <p className="science-warning">{prediction.limitation}</p>
            <EvidencePanel evidence={evidence} />
          </div>
        )}
      </section>
      <section id="science" className="predictive-section">
        <div className="section-heading">
          <div>
            <h2>Phase 9G · Synthetic research</h2>
            <p>
              Snapshot estático e versionado. Não representa evidência do
              veículo sintético de demonstração.
            </p>
          </div>
          <button
            className="button button-secondary"
            type="button"
            onClick={onScience}
          >
            Carregar resumo
          </button>
        </div>
        {scienceState === "loading" && <p role="status">Carregando…</p>}
        {scienceState === "unavailable" && (
          <p role="status">Resumo indisponível; nenhum fallback aplicado.</p>
        )}
        {science && <ResearchPanel research={science} />}
      </section>
    </>
  );
}
