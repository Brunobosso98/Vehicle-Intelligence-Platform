import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  PredictiveWorkspace,
  ScoreChart,
  type HistoryItem,
} from "../src/components/predictive-workspace";
import demoFixture from "../src/lib/predictive/demo-fixture.json";
import researchSummary from "../src/lib/predictive/research-summary.json";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const vehicleId = "b11d5220-a3ae-4f0d-a6c8-7d26cc3a7351";
const receiptId = "083bdb40-cf06-4413-b829-990902d7e66b";
const sessionId = "4515885a-b302-49c1-ae07-1b9f62e72cb2";
const pullId = "c2c11208-fb11-477e-91a2-79ba50b05afb";
const cutoff = "2026-10-01T12:00:00Z";

const prediction = {
  schema_version: "phase9d-prediction-response-v1",
  result_type: "next_pull",
  task: "NEXT_PULL_FUEL_DEVIATION",
  family: null,
  horizon: "NEXT_PULL",
  status: "READY_SCORE",
  reason_code: null,
  receipt_id: receiptId,
  requested_cutoff: cutoff,
  effective_cutoff: cutoff,
  source_role: "synthetic",
  model_version_id: "d4dc544c-9717-4f50-8670-22b6075ce98a",
  detector_version_id: null,
  feature_set_version: "phase9a-pull-v2",
  decision: true,
  engineering_validation_score: 0.46317,
  anomaly_score: null,
  threshold: 0.4,
  score_is_probability: false,
  interpretation: "Controlled engineering score.",
  limitation: "Not a mechanical diagnosis.",
  quality: {
    quality_class: "high",
    observed_feature_count: 8,
    expected_feature_count: 8,
    coverage: 1,
    missing_reason_counts: {},
  },
};

const historyItem = {
  prediction,
  recorded_at: cutoff,
  vehicle_id: vehicleId,
  session_id: sessionId,
  pull_id: pullId,
  configuration_id: null,
  source_type: "synthetic",
  evidence_available: true,
  evidence_completeness: "COMPLETE",
  evidence_integrity: "VERIFIED",
  captured_binding_state: "ACTIVATED",
  current_binding_state: "ACTIVATED",
};

const evidence = {
  schema_version: "phase9e-safe-projection-v1",
  evidence_id: "2817b693-0dc8-4a62-9c11-51e20dd963c0",
  receipt_id: receiptId,
  result_type: "next_pull",
  horizon: "NEXT_PULL",
  task: prediction.task,
  family: null,
  source_role: "synthetic",
  cutoff,
  status: "READY_SCORE",
  reason_code: null,
  score: 0.46317,
  threshold: 0.4,
  decision: true,
  score_is_probability: false,
  completeness: "COMPLETE",
  integrity: "VERIFIED",
  coverage: 1,
  observed_feature_count: 8,
  expected_feature_count: 8,
  source_type: "synthetic",
  missing_reason_counts: {},
  available_signals: ["boost_pressure", "engine_speed"],
  invalid_observation_count: 0,
  duplicate_timestamp_count: 0,
  pull_completeness: 1,
  artifact_availability: "VERIFIED",
  facts: [
    {
      fact_id: "feature-01",
      key: "boost_pressure",
      fact_type: "COMPUTED_FEATURE",
      value: 1.12,
      unit: "bar",
      cutoff,
      cutoff_eligible: true,
      quality: "VALID",
      missing_reason: null,
      observed_at: cutoff,
      available_at: cutoff,
      source_window_start: cutoff,
      source_window_end: cutoff,
      ordinal: 0,
      meaning: "Recorded Phase 9A input feature.",
    },
  ],
  gaps: [],
  claims: [],
  omitted_count: 0,
  node_count: 3,
  edge_count: 2,
  fact_count: 1,
  interpretation: "Historical evidence snapshot.",
  limitations: ["Snapshot only; it is not a new verification."],
};

function jsonResponse(
  body: unknown,
  status = 200,
  additionalHeaders: Record<string, string> = {},
) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...additionalHeaders },
  });
}

function pathFor(input: RequestInfo | URL): string {
  return new URL(String(input), "http://localhost").pathname;
}

type PrivateApiOptions = {
  authenticatedSession?: boolean;
  sessionFailureAt?: number;
  sessionResponses?: Array<{
    enabled: boolean;
    authenticated: boolean;
    demoEnabled: boolean;
    csrfToken?: string;
    expiresAt?: number;
  }>;
  empty?: boolean;
  expireVehicles?: boolean;
  loginStatus?: number;
  vehiclesStatus?: number;
  historyStatus?: number;
  retryAfter?: string;
  moreHistory?: boolean;
  historyItems?: unknown[];
  detailBody?: unknown;
  detailMismatch?: boolean;
  detailMismatchField?:
    | "receipt_id"
    | "result_type"
    | "task"
    | "family"
    | "horizon"
    | "status"
    | "source_role"
    | "requested_cutoff"
    | "effective_cutoff"
    | "engineering_validation_score"
    | "anomaly_score"
    | "threshold"
    | "decision";
  evidenceStatus?: number;
  evidenceMismatch?: boolean;
  evidenceMismatchField?:
    "receipt_id" | "source_role" | "horizon" | "cutoff" | "score" | "threshold";
  evidenceBody?: unknown;
  agentStatus?: number;
  agentItems?: Array<{
    run_id: string;
    started_at: string;
    status: string;
    source_role: string;
    horizon: string;
    completeness: string;
    integrity: string;
  }>;
  scienceStatus?: number;
  logoutStatus?: number;
  vehicleIds?: string[];
};

function installPrivateApi(options: PrivateApiOptions = {}) {
  let sessionRequest = 0;
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const requestUrl = new URL(String(input), "http://localhost");
    const path = requestUrl.pathname;
    if (path === "/api/predictive/session") {
      const currentRequest = sessionRequest;
      sessionRequest += 1;
      if (options.sessionFailureAt === currentRequest)
        return jsonResponse({ error: "Session status unavailable." }, 503);
      const configured = options.sessionResponses?.[currentRequest];
      return jsonResponse(
        configured ?? {
          enabled: true,
          authenticated: options.authenticatedSession ?? false,
          demoEnabled: true,
          ...(options.authenticatedSession
            ? { csrfToken: "csrf-session-token" }
            : {}),
        },
      );
    }
    if (path === "/api/predictive/auth/login")
      return options.loginStatus
        ? jsonResponse(
            { error: "Operator credential was not accepted." },
            options.loginStatus,
          )
        : jsonResponse({
            authenticated: true,
            csrfToken: "csrf-session-token",
          });
    if (path === "/api/predictive/auth/logout")
      return jsonResponse(
        { error: "Logout could not reach the server." },
        options.logoutStatus ?? 200,
      );
    if (path === "/api/predictive/vehicles")
      return options.expireVehicles
        ? jsonResponse(
            { code: "SESSION_EXPIRED", error: "Session expired" },
            401,
          )
        : options.vehiclesStatus
          ? jsonResponse(
              { error: "Vehicle scope unavailable." },
              options.vehiclesStatus,
            )
          : jsonResponse({
              vehicles: (options.vehicleIds ?? [vehicleId]).map((id) => ({
                vehicleId: id,
              })),
            });
    if (
      path.endsWith("/receipts") &&
      path.startsWith("/api/predictive/vehicles/")
    ) {
      const filteredOut =
        requestUrl.searchParams.get("result_kind") === "anomaly";
      const empty = options.empty || filteredOut;
      const scopedItem = {
        ...historyItem,
        vehicle_id: path.split("/")[4] ?? vehicleId,
      };
      const offset = Number(requestUrl.searchParams.get("offset") ?? 0);
      return options.historyStatus
        ? jsonResponse(
            { error: "History upstream failed." },
            options.historyStatus,
            options.retryAfter ? { "retry-after": options.retryAfter } : {},
          )
        : jsonResponse({
            schema_version: "phase9h-receipt-history-v1",
            items: empty ? [] : (options.historyItems ?? [scopedItem]),
            total: empty
              ? 0
              : options.moreHistory
                ? 501
                : (options.historyItems?.length ?? 1),
            limit: 20,
            offset,
            has_more: options.moreHistory && offset < 500,
          });
    }
    if (
      path ===
      `/api/predictive/vehicles/${vehicleId}/receipts/${receiptId}/evidence`
    ) {
      if (options.evidenceStatus)
        return jsonResponse(
          { error: "Evidence upstream failed." },
          options.evidenceStatus,
        );
      const mismatches: Record<string, unknown> = {
        receipt_id: "00000000-0000-4000-8000-000000000099",
        source_role: "real_vehicle",
        horizon: "AFTER_PULL_OFFLINE",
        cutoff: "2026-10-02T12:00:00Z",
        score: 0.55,
        threshold: 0.6,
      };
      const mismatchField =
        options.evidenceMismatchField ??
        (options.evidenceMismatch ? "receipt_id" : null);
      return jsonResponse(
        options.evidenceBody ??
          (mismatchField
            ? { ...evidence, [mismatchField]: mismatches[mismatchField] }
            : evidence),
      );
    }
    if (
      path ===
      `/api/predictive/vehicles/${vehicleId}/receipts/${receiptId}/agent-context`
    )
      return options.agentStatus
        ? jsonResponse(
            { error: "Agent context upstream failed." },
            options.agentStatus,
          )
        : jsonResponse({
            schema_version: "phase9h-agent-context-v1",
            receipt_id: receiptId,
            items: options.agentItems ?? [],
          });
    if (
      path === `/api/predictive/vehicles/${vehicleId}/receipts/${receiptId}`
    ) {
      const mismatches: Record<string, unknown> = {
        receipt_id: "00000000-0000-4000-8000-000000000099",
        result_type: "anomaly",
        task: "NEXT_PULL_PERFORMANCE_DEGRADATION",
        family: "thermal",
        horizon: "AFTER_PULL_OFFLINE",
        status: "ABSTAINED_LOW_QUALITY",
        source_role: "real_vehicle",
        requested_cutoff: "2026-10-02T12:00:00Z",
        effective_cutoff: null,
        engineering_validation_score: 0.99,
        anomaly_score: 0.99,
        threshold: 0.8,
        decision: false,
      };
      const mismatchField = options.detailMismatchField;
      return jsonResponse(
        options.detailBody
          ? options.detailBody
          : options.detailMismatch
            ? { ...prediction, engineering_validation_score: 0.99 }
            : mismatchField
              ? { ...prediction, [mismatchField]: mismatches[mismatchField] }
              : prediction,
      );
    }
    if (path === "/api/predictive/evaluation/summary")
      return options.scienceStatus
        ? jsonResponse(
            { error: "Research snapshot unavailable." },
            options.scienceStatus,
          )
        : jsonResponse(researchSummary);
    return jsonResponse({ error: `unexpected request ${path}` }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(
    await screen.findByLabelText("Credencial local do operador"),
    "local-operator-secret",
  );
  await user.click(screen.getByRole("button", { name: "Entrar no workspace" }));
  await screen.findByRole("heading", { name: "Visão geral" });
}

describe("Predictive Intelligence workspace", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("keeps the synthetic demonstration explicit, isolated and usable without prediction credentials", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = pathFor(input);
      if (path === "/api/predictive/session")
        return jsonResponse({
          enabled: false,
          authenticated: false,
          demoEnabled: true,
        });
      if (path === "/api/predictive/demo") return jsonResponse(demoFixture);
      if (path === "/api/predictive/demo-science")
        return jsonResponse(researchSummary);
      return jsonResponse({ error: "unexpected" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    await user.click(
      await screen.findByRole("button", {
        name: "Abrir demonstração sintética",
      }),
    );
    expect(
      await screen.findByText("DADOS SIMULADOS PARA DEMONSTRAÇÃO"),
    ).toBeInTheDocument();
    expect(screen.getByText(/não persistidos/i)).toBeInTheDocument();
    expect(screen.getAllByText("0.4217").length).toBeGreaterThan(0);
    expect(screen.getByText(/not a real vehicle result/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Carregar resumo" }));
    expect(
      await screen.findByText(/Real-world calibration: NOT_ESTABLISHED/i),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([input]) =>
        pathFor(input).includes("/prediction-service/"),
      ),
    ).toBe(false);
  });

  it("logs in, reads original values, evidence and research, then revokes local state on logout", async () => {
    const fetchMock = installPrivateApi();
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    const credential = await screen.findByLabelText(
      "Credencial local do operador",
    );
    await user.type(credential, "local-operator-secret");
    await user.click(
      screen.getByRole("button", { name: "Entrar no workspace" }),
    );
    expect((await screen.findAllByText("0.46317")).length).toBeGreaterThan(0);
    expect(await screen.findByText(/Original threshold/i)).toBeInTheDocument();
    expect(await screen.findByText(/Evidence provenance/i)).toBeInTheDocument();
    expect(
      await screen.findByText("2817b693-0dc8-4a62-9c11-51e20dd963c0"),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Carregar resumo científico" }),
    );
    expect(
      await screen.findByText(/Real-world calibration: NOT_ESTABLISHED/i),
    ).toBeInTheDocument();
    const bearerForwarded = fetchMock.mock.calls.some(([, init]) =>
      new Headers(init?.headers).has("authorization"),
    );
    expect(bearerForwarded).toBe(false);
    await user.click(screen.getByRole("button", { name: "Encerrar sessão" }));
    expect(
      await screen.findByLabelText("Credencial local do operador"),
    ).toBeInTheDocument();
  });

  it("shows an authorized empty state without silently switching to demonstration data", async () => {
    installPrivateApi({ empty: true });
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    await user.type(
      await screen.findByLabelText("Credencial local do operador"),
      "local-operator-secret",
    );
    await user.click(
      screen.getByRole("button", { name: "Entrar no workspace" }),
    );
    expect(
      await screen.findByText(
        "Nenhuma prediction registrada para estes filtros.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("DADOS SIMULADOS PARA DEMONSTRAÇÃO"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Ver demonstração separada" }),
    ).toBeInTheDocument();
  });

  it("plots anomaly scores on a method-local scale without probability language", () => {
    const anomaly: HistoryItem = {
      ...historyItem,
      prediction: {
        ...prediction,
        result_type: "anomaly",
        task: null,
        family: "turbo_spool",
        horizon: "AFTER_PULL_OFFLINE",
        engineering_validation_score: null,
        anomaly_score: 1.72,
        threshold: 1.5,
        score_is_probability: false,
      },
    };
    render(<ScoreChart items={[anomaly]} heading="Historical anomaly score" />);
    expect(
      screen.getByRole("img", { name: "Historical anomaly score" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Anomaly score · scale local à esta família e método"),
    ).toBeInTheDocument();
    expect(screen.getByText("1.72")).toBeInTheDocument();
    expect(
      screen.queryByText(/probability of failure/i),
    ).not.toBeInTheDocument();
  });

  it("restores an already verified server session without asking for credentials", async () => {
    const fetchMock = installPrivateApi({ authenticatedSession: true });
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    expect(
      await screen.findByRole("heading", { name: "Visão geral" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("table", { name: /Histórico persistido/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Credencial local do operador"),
    ).not.toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([, init]) =>
        new Headers(init?.headers).has("authorization"),
      ),
    ).toBe(false);
  });

  it("hides persisted private data while revalidating a restored page and clears it after revocation", async () => {
    installPrivateApi({
      authenticatedSession: true,
      sessionResponses: [
        {
          enabled: true,
          authenticated: true,
          demoEnabled: true,
          csrfToken: "csrf-session-token",
        },
        { enabled: true, authenticated: false, demoEnabled: true },
      ],
    });
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    const persistedHistory = await screen.findByRole("table", {
      name: /Histórico persistido/i,
    });
    expect(persistedHistory).toBeInTheDocument();
    expect(screen.getAllByText("0.46317").length).toBeGreaterThan(0);

    act(() => {
      const pageHide = new Event("pagehide");
      Object.defineProperty(pageHide, "persisted", { value: false });
      window.dispatchEvent(pageHide);
      const pageShow = new Event("pageshow");
      Object.defineProperty(pageShow, "persisted", { value: false });
      window.dispatchEvent(pageShow);
    });
    expect(
      screen.getByRole("table", { name: /Histórico persistido/i }),
    ).toBeInTheDocument();

    act(() => {
      const pageHide = new Event("pagehide");
      Object.defineProperty(pageHide, "persisted", { value: true });
      window.dispatchEvent(pageHide);
    });
    expect(
      screen.queryByRole("table", { name: /Histórico persistido/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("0.46317")).not.toBeInTheDocument();

    act(() => {
      const pageShow = new Event("pageshow");
      Object.defineProperty(pageShow, "persisted", { value: true });
      window.dispatchEvent(pageShow);
    });

    expect(
      await screen.findByLabelText("Credencial local do operador"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: /Histórico persistido/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("0.46317")).not.toBeInTheDocument();
  });

  it("clears the restored workspace when session revalidation is unavailable", async () => {
    installPrivateApi({ authenticatedSession: true, sessionFailureAt: 1 });
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    expect(
      await screen.findByRole("table", { name: /Histórico persistido/i }),
    ).toBeInTheDocument();

    act(() => {
      const pageHide = new Event("pagehide");
      Object.defineProperty(pageHide, "persisted", { value: true });
      window.dispatchEvent(pageHide);
      const pageShow = new Event("pageshow");
      Object.defineProperty(pageShow, "persisted", { value: true });
      window.dispatchEvent(pageShow);
    });

    expect(
      await screen.findByText("Não foi possível revalidar a sessão protegida."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: /Histórico persistido/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("0.46317")).not.toBeInTheDocument();
  });

  it("shows an anomaly receipt with its original local score and threshold", async () => {
    const anomaly: HistoryItem = {
      ...historyItem,
      prediction: {
        ...prediction,
        result_type: "anomaly",
        task: null,
        family: "turbo_spool",
        horizon: "AFTER_PULL_OFFLINE",
        engineering_validation_score: null,
        anomaly_score: 1.72,
        threshold: 1.5,
        score_is_probability: false,
      },
    };
    installPrivateApi({
      historyItems: [anomaly],
      detailBody: anomaly.prediction,
      evidenceStatus: 404,
    });
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    const historyTable = await screen.findByRole("table", {
      name: /Histórico persistido/i,
    });
    await user.click(within(historyTable).getByRole("button"));
    expect(
      await screen.findByText("Anomaly score · scale local ao método"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("1.72", { exact: true }).length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("1.5", { exact: true }).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getByText(/não representa probabilidade/i),
    ).toBeInTheDocument();
  });

  it("clears private view when the operator session expires", async () => {
    installPrivateApi({ expireVehicles: true });
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    await user.type(
      await screen.findByLabelText("Credencial local do operador"),
      "local-operator-secret",
    );
    await user.click(
      screen.getByRole("button", { name: "Entrar no workspace" }),
    );
    await waitFor(() =>
      expect(
        screen.getByLabelText("Credencial local do operador"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText(
        "Sua sessão expirou. Entre novamente para ver dados privados.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("0.46317")).not.toBeInTheDocument();
  });

  it("ignores a late history response after the operator changes vehicle scope", async () => {
    const secondVehicleId = "2f4a6244-4c5a-4f4f-a4e2-d6f255b71222";
    const secondReceiptId = "7227217d-616f-41cf-af03-b237850af689";
    let resolveFirstHistory: ((response: Response) => void) | undefined;
    const firstHistory = new Promise<Response>((resolve) => {
      resolveFirstHistory = resolve;
    });
    const secondPrediction = {
      ...prediction,
      receipt_id: secondReceiptId,
      engineering_validation_score: 0.25,
      threshold: 0.2,
    };
    const secondEvidence = {
      ...evidence,
      evidence_id: "4f6f14d8-c84c-41ce-8dbd-247b484bc658",
      receipt_id: secondReceiptId,
      score: 0.25,
      threshold: 0.2,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const requestUrl = new URL(String(input), "http://localhost");
        if (requestUrl.pathname === "/api/predictive/session")
          return jsonResponse({
            enabled: true,
            authenticated: false,
            demoEnabled: false,
          });
        if (requestUrl.pathname === "/api/predictive/auth/login")
          return jsonResponse({
            authenticated: true,
            csrfToken: "csrf-session-token",
          });
        if (requestUrl.pathname === "/api/predictive/vehicles")
          return jsonResponse({
            vehicles: [{ vehicleId }, { vehicleId: secondVehicleId }],
          });
        if (requestUrl.pathname.endsWith("/receipts")) {
          const requestedVehicle = requestUrl.pathname.split("/")[4];
          if (requestedVehicle === vehicleId) return firstHistory;
          return jsonResponse({
            schema_version: "phase9h-receipt-history-v1",
            items: [
              {
                ...historyItem,
                vehicle_id: secondVehicleId,
                prediction: secondPrediction,
              },
            ],
            total: 1,
            limit: 20,
            offset: 0,
            has_more: false,
          });
        }
        if (requestUrl.pathname.endsWith("/evidence"))
          return jsonResponse(secondEvidence);
        if (requestUrl.pathname.endsWith("/agent-context"))
          return jsonResponse({
            schema_version: "phase9h-agent-context-v1",
            receipt_id: secondReceiptId,
            items: [],
          });
        if (requestUrl.pathname.endsWith(`/receipts/${secondReceiptId}`))
          return jsonResponse(secondPrediction);
        return jsonResponse({ error: "unexpected request" }, 404);
      }),
    );

    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    await screen.findByRole("option", { name: secondVehicleId });
    await user.selectOptions(
      screen.getByLabelText("Veículo permitido"),
      secondVehicleId,
    );
    expect(await screen.findAllByText("0.25", { exact: true })).toHaveLength(2);
    await act(async () => {
      resolveFirstHistory?.(
        jsonResponse({
          schema_version: "phase9h-receipt-history-v1",
          items: [
            {
              ...historyItem,
              prediction: { ...prediction, engineering_validation_score: 0.99 },
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
          has_more: false,
        }),
      );
      await firstHistory;
    });
    expect(screen.getByLabelText("Veículo permitido")).toHaveValue(
      secondVehicleId,
    );
    expect(screen.getAllByText("0.25", { exact: true })).toHaveLength(2);
    expect(screen.queryByText("0.99", { exact: true })).not.toBeInTheDocument();
  });

  it("keeps the disabled state closed and presents a retry state when access lookup fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          enabled: false,
          authenticated: false,
          demoEnabled: false,
        }),
      ),
    );
    const { unmount } = render(<PredictiveWorkspace />);
    expect(
      await screen.findByRole("heading", {
        name: "Acesso de operador de desenvolvimento",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Credencial local do operador"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Abrir demonstração sintética" }),
    ).not.toBeInTheDocument();
    unmount();

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("operator status network unavailable");
      }),
    );
    render(<PredictiveWorkspace />);
    expect(
      await screen.findByRole("button", { name: "Tentar novamente" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Acesso de operador de desenvolvimento",
      }),
    ).toBeInTheDocument();
  });

  it("shows operator credential errors without exposing the password by default", async () => {
    installPrivateApi({ loginStatus: 401 });
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    const input = await screen.findByLabelText("Credencial local do operador");
    expect(input).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Mostrar" }));
    expect(input).toHaveAttribute("type", "text");
    await user.type(input, "invalid-local-credential");
    await user.click(
      screen.getByRole("button", { name: "Entrar no workspace" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Operator credential was not accepted.",
    );
    expect(
      screen.queryByRole("heading", { name: "Visão geral" }),
    ).not.toBeInTheDocument();
  });

  it("reports vehicle and history failures and keeps retry actions scoped to the selected view", async () => {
    installPrivateApi({ vehiclesStatus: 503 });
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    await logIn(user);
    expect(
      await screen.findByText("Vehicle scope unavailable."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: /Histórico persistido/i }),
    ).not.toBeInTheDocument();
  });

  it("shows a retryable history error without replacing it with demonstration data", async () => {
    installPrivateApi({ historyStatus: 503 });
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    await logIn(user);
    expect(
      await screen.findByText(
        "Histórico indisponível: History upstream failed.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Tentar novamente" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("DADOS SIMULADOS PARA DEMONSTRAÇÃO"),
    ).not.toBeInTheDocument();
  });

  it("shows the Retry-After delay on rate-limited history reads", async () => {
    installPrivateApi({ historyStatus: 429, retryAfter: "17" });
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    await logIn(user);
    expect(
      await screen.findByText(
        "History upstream failed. Aguarde 17 s antes de tentar novamente.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("DADOS SIMULADOS PARA DEMONSTRAÇÃO"),
    ).not.toBeInTheDocument();
  });

  it("applies bounded history filters and pages through the capped receipt list", async () => {
    const fetchMock = installPrivateApi({ moreHistory: true });
    const user = userEvent.setup();
    render(<PredictiveWorkspace />);
    await logIn(user);
    await screen.findByRole("table", { name: /Histórico persistido/i });
    expect(
      screen.getByText("500+ receipts no limite de consulta"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() =>
      expect(screen.getByText("Página 2")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Anterior" }));
    await user.selectOptions(
      screen.getByLabelText("Tipo de resultado"),
      "anomaly",
    );
    await user.type(screen.getByLabelText("Registrado desde"), "2026-10-01");
    await user.type(screen.getByLabelText("Registrado até"), "2026-10-02");
    await user.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    expect(
      await screen.findByText(
        "Nenhuma prediction registrada para estes filtros.",
      ),
    ).toBeInTheDocument();
    const filteredUrl = fetchMock.mock.calls
      .map(([input]) => String(input))
      .find((url) => url.includes("result_kind=anomaly"));
    expect(filteredUrl).toContain("recorded_from=2026-10-01T00%3A00%3A00.000Z");
    expect(filteredUrl).toContain("recorded_to=2026-10-02T23%3A59%3A59.999Z");
    await user.click(screen.getByRole("button", { name: "Limpar" }));
    await waitFor(() =>
      expect(
        screen.getByRole("table", { name: /Histórico persistido/i }),
      ).toBeInTheDocument(),
    );
    const resetUrl = fetchMock.mock.calls
      .map(([input]) => String(input))
      .filter((url) => url.includes("/receipts?"))
      .at(-1);
    expect(resetUrl).not.toContain("result_kind=");
    expect(resetUrl).toContain("offset=0");
  }, 15_000);

  it.each([
    [
      "source field mismatch",
      { detailMismatch: true },
      /Source mismatch — valores ocultos/,
    ],
    [
      "missing evidence",
      { evidenceStatus: 404 },
      /Esta receipt não tem projeção de evidência disponível/,
    ],
    [
      "unavailable evidence",
      { evidenceStatus: 503 },
      /Projeção não confere com o escopo da receipt/,
    ],
    [
      "evidence receipt mismatch",
      { evidenceMismatch: true },
      /Projeção não confere com o escopo da receipt/,
    ],
  ] as const)("fails closed for %s", async (_label, options, expected) => {
    installPrivateApi(options);
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    expect(await screen.findByText(expected)).toBeInTheDocument();
    if ("detailMismatch" in options && options.detailMismatch)
      expect(document.querySelector(".prediction-detail")).toBeNull();
  });

  it.each([
    "receipt_id",
    "result_type",
    "task",
    "family",
    "horizon",
    "status",
    "source_role",
    "requested_cutoff",
    "effective_cutoff",
    "engineering_validation_score",
    "anomaly_score",
    "threshold",
    "decision",
  ] as const)(
    "hides every mismatched original receipt scope field: %s",
    async (detailMismatchField) => {
      installPrivateApi({ detailMismatchField });
      const user = userEvent.setup();
      render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
      await logIn(user);
      expect(
        await screen.findByText("Source mismatch — valores ocultos"),
      ).toBeInTheDocument();
      expect(document.querySelector(".prediction-detail")).toBeNull();
    },
  );

  it.each([
    "receipt_id",
    "source_role",
    "horizon",
    "cutoff",
    "score",
    "threshold",
  ] as const)(
    "fails closed for a 9E projection mismatch in %s",
    async (evidenceMismatchField) => {
      installPrivateApi({ evidenceMismatchField });
      const user = userEvent.setup();
      render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
      await logIn(user);
      expect(
        await screen.findByText(/Projeção não confere com o escopo da receipt/),
      ).toBeInTheDocument();
      expect(document.querySelector(".evidence-detail")).toBeNull();
    },
  );

  it("renders detailed evidence gaps, missing observations and linked claims accessibly", async () => {
    installPrivateApi({
      evidenceBody: {
        ...evidence,
        available_signals: [],
        missing_reason_counts: { SIGNAL_UNAVAILABLE: 1 },
        facts: [
          {
            ...evidence.facts[0],
            value: null,
            unit: null,
            missing_reason: "SIGNAL_UNAVAILABLE",
          },
          {
            fact_id: "feature-02",
            key: "engine_speed",
            value: 2450,
            unit: "rpm",
            quality: "VALID",
            fact_type: "COMPUTED_FEATURE",
            meaning: "Engine speed",
            missing_reason: null,
          },
        ],
        gaps: [
          { code: "SIGNAL_UNAVAILABLE", reason_code: "NO_CAPTURED_SOURCE" },
        ],
        claims: [
          {
            claim_id: "claim-01",
            category: "support",
            template: "Observed input",
            fact_ids: ["feature-01"],
          },
          { claim_id: "claim-02", category: null, template: null },
        ],
      },
    });
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    expect(await screen.findByText("Nenhum listado")).toBeInTheDocument();
    expect(screen.getByText("SIGNAL_UNAVAILABLE: 1")).toBeInTheDocument();
    expect(
      screen.getByText(/SIGNAL_UNAVAILABLE · NO_CAPTURED_SOURCE/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Missing observations" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Vínculos de interpretação" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 fatos referenciados/)).toBeInTheDocument();
    expect(screen.getByText("Ausente")).toBeInTheDocument();
  });

  it("preserves empty evidence collections and does not imply a zero or healthy state", async () => {
    installPrivateApi({
      evidenceBody: {
        ...evidence,
        available_signals: [],
        missing_reason_counts: {},
        facts: [],
        gaps: [],
        claims: [],
        limitations: [],
      },
    });
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    expect(await screen.findByText("Nenhum listado")).toBeInTheDocument();
    expect(screen.getAllByText("Nenhum sinal ausente registrado")).toHaveLength(
      2,
    );
    expect(screen.getByText(/Nenhum fato projetado/)).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Missing observations" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Vínculos de interpretação" }),
    ).not.toBeInTheDocument();
  });

  it("plots multiple historical scores without interpolating thresholds", async () => {
    const secondReceiptId = "c7dd4bb4-8b1f-4113-b001-64b1e934cad2";
    installPrivateApi({
      historyItems: [
        historyItem,
        {
          ...historyItem,
          recorded_at: "not-a-date",
          prediction: {
            ...prediction,
            receipt_id: secondReceiptId,
            engineering_validation_score: 0.25,
            threshold: null,
          },
        },
      ],
    });
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    expect(await screen.findByText("Horário indisponível")).toBeInTheDocument();
    expect(
      document.querySelectorAll(".predictive-chart svg .chart-point"),
    ).toHaveLength(2);
    expect(
      document.querySelectorAll(".predictive-chart svg .chart-threshold"),
    ).toHaveLength(1);
  });

  it("links only an existing receipt-related AgentRun and handles a missing research snapshot", async () => {
    const runId = "c7dd4bb4-8b1f-4113-b001-64b1e934cad2";
    installPrivateApi({
      agentItems: [
        {
          run_id: runId,
          started_at: cutoff,
          status: "completed",
          source_role: "synthetic",
          horizon: "NEXT_PULL",
          completeness: "COMPLETE",
          integrity: "VERIFIED",
        },
      ],
      scienceStatus: 503,
      logoutStatus: 503,
    });
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    expect(
      await screen.findByRole("link", { name: new RegExp(runId) }),
    ).toHaveAttribute(
      "href",
      `/?vehicleId=${vehicleId}&agentRunId=${runId}#agent-workspace`,
    );
    await user.click(
      screen.getByRole("button", { name: "Carregar resumo científico" }),
    );
    expect(
      await screen.findByText(/Snapshot de pesquisa indisponível/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Encerrar sessão" }));
    expect(
      await screen.findByLabelText("Credencial local do operador"),
    ).toBeInTheDocument();
    expect(screen.getByText("Sessão encerrada.")).toBeInTheDocument();
  });

  it("ignores a slow history response after the operator switches vehicle scope", async () => {
    const secondVehicleId = "00000000-0000-4000-8000-000000000022";
    const historyFor = (scope: string, score: number) =>
      jsonResponse({
        schema_version: "phase9h-receipt-history-v1",
        items: [
          {
            ...historyItem,
            vehicle_id: scope,
            prediction: { ...prediction, engineering_validation_score: score },
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
        has_more: false,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const requestUrl = new URL(String(input), "http://localhost");
      if (requestUrl.pathname === "/api/predictive/session")
        return jsonResponse({
          enabled: true,
          authenticated: false,
          demoEnabled: false,
        });
      if (requestUrl.pathname === "/api/predictive/auth/login")
        return jsonResponse({
          authenticated: true,
          csrfToken: "csrf-session-token",
        });
      if (requestUrl.pathname === "/api/predictive/vehicles")
        return jsonResponse({
          vehicles: [{ vehicleId }, { vehicleId: secondVehicleId }],
        });
      if (
        requestUrl.pathname.endsWith("/receipts") &&
        requestUrl.pathname.includes(vehicleId)
      ) {
        return new Promise<Response>((resolve) =>
          window.setTimeout(() => resolve(historyFor(vehicleId, 0.90001)), 150),
        );
      }
      if (
        requestUrl.pathname.endsWith("/receipts") &&
        requestUrl.pathname.includes(secondVehicleId)
      )
        return historyFor(secondVehicleId, 0.80002);
      if (requestUrl.pathname.endsWith("/agent-context"))
        return jsonResponse({
          schema_version: "phase9h-agent-context-v1",
          receipt_id: receiptId,
          items: [],
        });
      if (requestUrl.pathname.endsWith("/evidence"))
        return jsonResponse(evidence);
      if (requestUrl.pathname.endsWith(`/receipts/${receiptId}`))
        return jsonResponse(prediction);
      return jsonResponse({ error: "unexpected request" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<PredictiveWorkspace initialVehicleId={vehicleId} />);
    await logIn(user);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes(`/vehicles/${vehicleId}/receipts?`),
        ),
      ).toBe(true),
    );
    await user.selectOptions(
      screen.getByLabelText("Veículo permitido"),
      secondVehicleId,
    );
    expect(await screen.findByText("0.80002")).toBeInTheDocument();
    await new Promise((resolve) => window.setTimeout(resolve, 200));
    expect(screen.getByLabelText("Veículo permitido")).toHaveValue(
      secondVehicleId,
    );
    expect(screen.getByText("0.80002")).toBeInTheDocument();
    expect(screen.queryByText("0.90001")).not.toBeInTheDocument();
  });
});
