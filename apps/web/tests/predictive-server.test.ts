import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const vehicleId = "b11d5220-a3ae-4f0d-a6c8-7d26cc3a7351";

function configureEnabled() {
  vi.stubEnv("NODE_ENV", "test");
  vi.stubEnv("ENVIRONMENT", "test");
  vi.stubEnv("PREDICTIVE_UI_ENABLED", "true");
  vi.stubEnv("PREDICTION_SERVICE_ENABLED", "true");
  vi.stubEnv("PREDICTION_OPERATOR_TOKEN", "operator-token-".padEnd(48, "x"));
  vi.stubEnv(
    "PREDICTIVE_UI_OPERATOR_SECRET",
    "browser-operator-secret-".padEnd(48, "s"),
  );
  vi.stubEnv(
    "PREDICTIVE_UI_SESSION_SECRET",
    "session-mac-secret-".padEnd(48, "m"),
  );
  vi.stubEnv("PREDICTIVE_UI_ORIGIN", "http://localhost");
  vi.stubEnv("PREDICTIVE_UI_ALLOWED_VEHICLE_IDS", vehicleId);
  vi.stubEnv("PREDICTIVE_UI_API_ALLOWED_HOSTS", "api,localhost,127.0.0.1,::1");
  vi.stubEnv("API_BASE_URL", "http://api:8000");
}

async function serverModule() {
  return await import("../src/lib/predictive/server");
}

function request(path = "/api/predictive/session", cookie = ""): NextRequest {
  return new NextRequest(`http://localhost${path}`, {
    headers: cookie ? { cookie: `vip_predictive_session=${cookie}` } : {},
  });
}

describe("predictive server boundary", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    configureEnabled();
  });

  it("fails closed unless the full development operator configuration is present", async () => {
    const server = await serverModule();
    expect(server.predictiveEnabled()).toBe(true);
    vi.stubEnv("ENVIRONMENT", "production");
    expect(server.predictiveEnabled()).toBe(false);
    vi.stubEnv("ENVIRONMENT", "test");
    vi.stubEnv("PREDICTION_OPERATOR_TOKEN", "");
    expect(server.predictiveEnabled()).toBe(false);
  });

  it("rejects production demo and limits the configured vehicle scope", async () => {
    const server = await serverModule();
    expect(server.demoEnabled()).toBe(false);
    vi.stubEnv("PREDICTIVE_UI_DEMO_ENABLED", "true");
    expect(server.demoEnabled()).toBe(true);
    vi.stubEnv("ENVIRONMENT", "production");
    expect(server.demoEnabled()).toBe(false);
    vi.stubEnv("ENVIRONMENT", "test");
    expect(server.isAllowedVehicle(vehicleId)).toBe(true);
    expect(
      server.isAllowedVehicle("00000000-0000-4000-8000-000000000001"),
    ).toBe(false);
    vi.stubEnv("PREDICTIVE_UI_ALLOWED_VEHICLE_IDS", "not-a-uuid");
    expect(server.boundedVehicleIds()).toEqual([]);
  });

  it("authenticates the dedicated UI credential and issues a short-lived revocable session", async () => {
    const server = await serverModule();
    expect(
      server.authenticateOperator("browser-operator-secret-".padEnd(48, "s")),
    ).toBe(true);
    expect(server.authenticateOperator("wrong".padEnd(48, "s"))).toBe(false);
    const created = server.createSession();
    const authenticatedRequest = request(
      "/api/predictive/session",
      created.token,
    );
    const session = server.verifySession(authenticatedRequest as never);
    expect(session.csrf).toBe(created.csrf);
    expect(session.expiresAt).toBeGreaterThan(Date.now());
    const csrfRequest = new Request(
      "http://localhost/api/predictive/auth/logout",
      { headers: { "x-csrf-token": created.csrf } },
    );
    expect(() =>
      server.verifyCsrf(csrfRequest as never, session),
    ).not.toThrow();
    expect(() =>
      server.verifyCsrf(new Request("http://localhost") as never, session),
    ).toThrow();
    server.revokeSession(authenticatedRequest as never);
    expect(() => server.verifySession(authenticatedRequest as never)).toThrow(
      "expired",
    );
  });

  it("rejects tampered cookies and malformed or production API origins", async () => {
    const server = await serverModule();
    const created = server.createSession();
    const changed = `${created.token.slice(0, -1)}${created.token.endsWith("A") ? "B" : "A"}`;
    expect(() =>
      server.verifySession(
        request("/api/predictive/session", changed) as never,
      ),
    ).toThrow();
    vi.stubEnv("API_BASE_URL", "https://outside.example.test/api");
    expect(server.predictiveEnabled()).toBe(false);
    vi.stubEnv("API_BASE_URL", "http://user:secret@api:8000");
    expect(server.predictiveEnabled()).toBe(false);
    vi.stubEnv("API_BASE_URL", "http://169.254.169.254:80");
    expect(server.predictiveEnabled()).toBe(false);
  });

  it("enforces same-origin requests, allowlisted upstream paths and server-only bearer forwarding", async () => {
    const server = await serverModule();
    const sameOrigin = new Request(
      "http://localhost/api/predictive/auth/login",
      { headers: { origin: "http://localhost" } },
    );
    expect(() => server.assertSameOrigin(sameOrigin as never)).not.toThrow();
    expect(() =>
      server.assertSameOrigin(
        new Request("http://localhost", {
          headers: { origin: "https://attacker.test" },
        }) as never,
      ),
    ).toThrow();
    expect(() =>
      server.assertSameOrigin(new Request("http://localhost") as never),
    ).toThrow();
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ safe: true }), {
          headers: { "content-type": "application/json" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await server.predictionApiGet(
      request(
        `/api/predictive/vehicles/${vehicleId}/receipts?limit=1`,
      ) as never,
      `/api/v1/prediction-service/vehicles/${vehicleId}/runs`,
    );
    expect(result).toEqual({ safe: true });
    const options = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(new Headers(options.headers).get("authorization")).toContain(
      "Bearer operator-token-",
    );
    expect(options.cache).toBe("no-store");
    await expect(
      server.predictionApiGet(
        request() as never,
        "/api/v1/prediction-service/../vehicles",
      ),
    ).rejects.toThrow("Invalid predictive request");
  });

  it("rejects upstream redirects, oversized bodies, invalid content types and upstream errors", async () => {
    const server = await serverModule();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(null, {
            status: 302,
            headers: { location: "http://attacker.test" },
          }),
      ),
    );
    await expect(
      server.predictionApiGet(
        request() as never,
        "/api/v1/prediction-service/vehicles/receipts",
      ),
    ).rejects.toThrow("response was rejected");
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response("x".repeat(1_000_001), {
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    await expect(
      server.predictionApiGet(
        request() as never,
        "/api/v1/prediction-service/vehicles/receipts",
      ),
    ).rejects.toThrow("response limit");
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response("{}", { headers: { "content-type": "text/html" } }),
      ),
    );
    await expect(
      server.predictionApiGet(
        request() as never,
        "/api/v1/prediction-service/vehicles/receipts",
      ),
    ).rejects.toThrow("unsupported response");
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response("{}", {
            status: 404,
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    await expect(
      server.predictionApiGet(
        request() as never,
        "/api/v1/prediction-service/vehicles/receipts",
      ),
    ).rejects.toThrow("unavailable for the selected vehicle");
  });

  it("bounds operator login failures and sanitizes receipt and evidence DTOs", async () => {
    const server = await serverModule();
    for (let index = 0; index < 5; index += 1)
      expect(server.takeLoginFailureSlot()).toBe(true);
    expect(server.takeLoginFailureSlot()).toBe(false);
    server.clearLoginFailures();
    expect(server.takeLoginFailureSlot()).toBe(true);
    const prediction = server.safePrediction({
      schema_version: "phase9d-prediction-response-v1",
      receipt_id: vehicleId,
      result_type: "next_pull",
      horizon: "NEXT_PULL",
      task: "NEXT_PULL_FUEL_DEVIATION",
      family: null,
      status: "READY_SCORE",
      score_is_probability: false,
      source_role: "synthetic",
      requested_cutoff: "2026-10-01T12:00:00Z",
      effective_cutoff: "2026-10-01T12:00:00Z",
      model_version_id: "d4dc544c-9717-4f50-8670-22b6075ce98a",
      detector_version_id: null,
      decision: true,
      engineering_validation_score: 0.46317,
      anomaly_score: null,
      threshold: 0.4,
      interpretation: "Engineering score.",
      limitation: "Not a diagnosis.",
      quality: {
        quality_class: "high",
        coverage: 1,
        observed_feature_count: 1,
        expected_feature_count: 1,
        missing_reason_counts: {},
      },
      lineage: { feature_set_id: "private-node" },
      raw_hash: "private-hash",
    });
    expect(prediction).not.toHaveProperty("lineage");
    expect(prediction).not.toHaveProperty("raw_hash");
    const evidence = server.safeEvidence(
      {
        schema_version: "phase9e-safe-projection-v1",
        evidence_id: "2817b693-0dc8-4a62-9c11-51e20dd963c0",
        receipt_id: vehicleId,
        score: 0.46317,
        threshold: 0.4,
        source_role: "synthetic",
        horizon: "NEXT_PULL",
        result_type: "next_pull",
        score_is_probability: false,
        integrity: "VERIFIED",
        completeness: "COMPLETE",
        cutoff: "2026-10-01T12:00:00Z",
        coverage: 1,
        observed_feature_count: 1,
        expected_feature_count: 1,
        artifact_availability: "VERIFIED",
        source_type: "synthetic",
        available_signals: ["boost_pressure"],
        missing_reason_counts: {},
        limitations: ["Snapshot only."],
        facts: [
          {
            id: "f1",
            key: "coverage",
            type: "COMPUTED_FEATURE",
            quality: "VALID",
            meaning: "Coverage",
            unit: null,
            source_node_id: "private-node",
            value: 1,
          },
        ],
        gaps: [{ code: "SIGNAL_UNAVAILABLE", source_node_id: "private-node" }],
        claims: [],
        source_checksum: "private-hash",
      },
      vehicleId,
    );
    expect(
      (evidence.facts as Array<Record<string, unknown>>)[0],
    ).not.toHaveProperty("source_node_id");
    expect((evidence.facts as Array<Record<string, unknown>>)[0]).toMatchObject(
      { fact_id: "f1", fact_type: "COMPUTED_FEATURE" },
    );
    expect(evidence).not.toHaveProperty("source_checksum");
    expect(() =>
      server.safeEvidence(
        {
          schema_version: "phase9e-safe-projection-v1",
          receipt_id: "another-receipt",
          evidence_id: "evidence-id",
          facts: [],
          gaps: [],
          claims: [],
        },
        vehicleId,
      ),
    ).toThrow("does not match");
  });

  it("validates bounded history scopes and allowlisted filter values", async () => {
    const server = await serverModule();
    const history = {
      schema_version: "phase9h-receipt-history-v1",
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
      items: [
        {
          prediction: {
            schema_version: "phase9d-prediction-response-v1",
            receipt_id: "083bdb40-cf06-4413-b829-990902d7e66b",
            result_type: "next_pull",
            task: "NEXT_PULL_FUEL_DEVIATION",
            family: null,
            horizon: "NEXT_PULL",
            status: "READY_SCORE",
            reason_code: null,
            requested_cutoff: "2026-10-01T12:00:00Z",
            effective_cutoff: "2026-10-01T12:00:00Z",
            source_role: "synthetic",
            model_version_id: "d4dc544c-9717-4f50-8670-22b6075ce98a",
            detector_version_id: null,
            feature_set_version: "phase9a-pull-v2",
            decision: true,
            engineering_validation_score: 0.46317,
            anomaly_score: null,
            threshold: 0.4,
            score_is_probability: false,
            interpretation: "Engineering score.",
            limitation: "Not diagnosis.",
            quality: {
              quality_class: "high",
              observed_feature_count: 8,
              expected_feature_count: 8,
              coverage: 1,
              missing_reason_counts: {},
            },
            lineage: { feature_set_id: "private-id" },
          },
          recorded_at: "2026-10-01T12:01:00Z",
          vehicle_id: vehicleId,
          session_id: "4515885a-b302-49c1-ae07-1b9f62e72cb2",
          pull_id: "c2c11208-fb11-477e-91a2-79ba50b05afb",
          configuration_id: null,
          source_type: "synthetic",
          evidence_available: false,
          evidence_completeness: null,
          evidence_integrity: null,
          captured_binding_state: "ACTIVATED",
          current_binding_state: "REVOKED",
        },
      ],
    };
    const projected = server.safeHistory(history, vehicleId);
    expect(
      (projected.items as Array<Record<string, unknown>>)[0],
    ).toMatchObject({
      vehicle_id: vehicleId,
      current_binding_state: "REVOKED",
    });
    expect(
      (projected.items as Array<Record<string, unknown>>)[0]?.prediction,
    ).not.toHaveProperty("lineage");
    expect(() =>
      server.safeHistory(history, "00000000-0000-4000-8000-000000000001"),
    ).toThrow("selected vehicle");
    expect(() =>
      server.safeHistory(
        {
          ...history,
          items: Array.from({ length: 21 }, () => history.items[0]),
        },
        vehicleId,
      ),
    ).toThrow("malformed");

    const invalidFilterRequest = request(
      "/api/predictive/vehicles/" +
        vehicleId +
        "/receipts?family=turbo&limit=500",
    );
    await expect(
      server.predictionApiGet(
        invalidFilterRequest as never,
        `/api/v1/prediction-service/vehicles/${vehicleId}/runs`,
      ),
    ).rejects.toThrow("filter value");
    const invalidLimitRequest = request(
      "/api/predictive/vehicles/" + vehicleId + "/receipts?limit=500",
    );
    await expect(
      server.predictionApiGet(
        invalidLimitRequest as never,
        `/api/v1/prediction-service/vehicles/${vehicleId}/runs`,
      ),
    ).rejects.toThrow("page size");
  });

  it("rejects malformed model receipts across task, horizon, score, cutoff and quality fields", async () => {
    const server = await serverModule();
    const prediction = {
      schema_version: "phase9d-prediction-response-v1",
      receipt_id: vehicleId,
      result_type: "next_pull",
      horizon: "NEXT_PULL",
      task: "NEXT_PULL_FUEL_DEVIATION",
      family: null,
      status: "READY_SCORE",
      reason_code: null,
      requested_cutoff: "2026-10-01T12:00:00Z",
      effective_cutoff: "2026-10-01T12:00:00Z",
      source_role: "synthetic",
      model_version_id: vehicleId,
      detector_version_id: null,
      feature_set_version: "phase9a-pull-v2",
      decision: true,
      engineering_validation_score: 0.5,
      anomaly_score: null,
      threshold: 0.4,
      score_is_probability: false,
      interpretation: "Engineering score.",
      limitation: "Not a diagnosis.",
      quality: {
        quality_class: "high",
        observed_feature_count: 8,
        expected_feature_count: 8,
        coverage: 1,
        missing_reason_counts: {},
      },
    };
    const invalid = [
      null,
      [],
      { ...prediction, schema_version: "old" },
      { ...prediction, receipt_id: "bad-id" },
      { ...prediction, result_type: "unknown" },
      { ...prediction, horizon: "AFTER_PULL_OFFLINE" },
      { ...prediction, task: "unknown-task" },
      { ...prediction, family: "thermal" },
      { ...prediction, anomaly_score: 1 },
      { ...prediction, decision: "ANOMALOUS" },
      { ...prediction, source_role: "production" },
      { ...prediction, status: "UNKNOWN" },
      { ...prediction, model_version_id: "bad-id" },
      { ...prediction, detector_version_id: "bad-id" },
      { ...prediction, requested_cutoff: "2026-10-01" },
      { ...prediction, effective_cutoff: "not-a-time" },
      { ...prediction, decision: null },
      { ...prediction, interpretation: 1 },
      { ...prediction, interpretation: "x".repeat(241) },
      { ...prediction, limitation: null },
      { ...prediction, limitation: "x".repeat(401) },
      { ...prediction, engineering_validation_score: Number.POSITIVE_INFINITY },
      { ...prediction, engineering_validation_score: -0.1 },
      { ...prediction, threshold: -0.1 },
      {
        ...prediction,
        status: "ABSTAINED_LOW_QUALITY",
        engineering_validation_score: 0.5,
        decision: null,
      },
      { ...prediction, quality: null },
      {
        ...prediction,
        quality: { ...prediction.quality, quality_class: "medium" },
      },
      {
        ...prediction,
        quality: { ...prediction.quality, observed_feature_count: 129 },
      },
      {
        ...prediction,
        quality: { ...prediction.quality, expected_feature_count: -1 },
      },
      { ...prediction, quality: { ...prediction.quality, coverage: 1.1 } },
      {
        ...prediction,
        quality: {
          ...prediction.quality,
          missing_reason_counts: { missing: 129 },
        },
      },
      {
        ...prediction,
        quality: {
          ...prediction.quality,
          missing_reason_counts: Object.fromEntries(
            Array.from({ length: 17 }, (_, index) => [`missing_${index}`, 1]),
          ),
        },
      },
    ];
    for (const [index, value] of invalid.entries())
      expect(
        () => server.safePrediction(value),
        `prediction case ${index}`,
      ).toThrow();

    const anomaly = {
      ...prediction,
      result_type: "anomaly",
      horizon: "AFTER_PULL_OFFLINE",
      task: null,
      family: "thermal",
      decision: "INLIER",
      engineering_validation_score: null,
      anomaly_score: 0.8,
      detector_version_id: vehicleId,
    };
    expect(server.safePrediction(anomaly)).toMatchObject({
      family: "thermal",
      horizon: "AFTER_PULL_OFFLINE",
    });
    for (const value of [
      { ...anomaly, family: "unknown" },
      { ...anomaly, task: "NEXT_PULL_FUEL_DEVIATION" },
      { ...anomaly, engineering_validation_score: 0.1 },
      { ...anomaly, decision: true },
      { ...anomaly, status: "READY_SCORE", decision: "unknown" },
    ])
      expect(() => server.safePrediction(value)).toThrow();
  });

  it("rejects malformed 9E projections and redacts private or unsafe fact values", async () => {
    const server = await serverModule();
    const projection = {
      schema_version: "phase9e-safe-projection-v1",
      evidence_id: vehicleId,
      receipt_id: vehicleId,
      result_type: "next_pull",
      horizon: "NEXT_PULL",
      task: "NEXT_PULL_FUEL_DEVIATION",
      family: null,
      source_role: "synthetic",
      cutoff: "2026-10-01T12:00:00Z",
      status: "READY_SCORE",
      reason_code: null,
      score: 0.5,
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
      available_signals: ["boost_pressure"],
      invalid_observation_count: 0,
      duplicate_timestamp_count: 0,
      pull_completeness: 1,
      artifact_availability: "VERIFIED",
      facts: [
        {
          id: "fact-1",
          key: "boost_pressure",
          type: "COMPUTED_FEATURE",
          quality: "VALID",
          meaning: "Boost pressure",
          unit: "bar",
          value: 1.2,
          missing_reason: null,
        },
      ],
      gaps: [],
      claims: [],
      omitted_count: 0,
      node_count: 1,
      edge_count: 0,
      fact_count: 1,
      interpretation: "Snapshot.",
      limitations: ["Historical snapshot only."],
    };
    const invalid = [
      null,
      { ...projection, schema_version: "old" },
      { ...projection, receipt_id: "other-receipt" },
      { ...projection, evidence_id: "bad-id" },
      { ...projection, source_role: "unknown" },
      { ...projection, result_type: "other" },
      { ...projection, horizon: "NEXT_PULL", result_type: "anomaly" },
      { ...projection, completeness: "UNKNOWN" },
      { ...projection, integrity: "FAILED" },
      { ...projection, coverage: 2 },
      { ...projection, observed_feature_count: 129 },
      { ...projection, expected_feature_count: -1 },
      { ...projection, cutoff: "yesterday" },
      { ...projection, score_is_probability: true },
      { ...projection, score: Number.NaN },
      { ...projection, threshold: -1 },
      { ...projection, limitations: [] },
      { ...projection, limitations: ["x".repeat(501)] },
      { ...projection, available_signals: null },
      {
        ...projection,
        available_signals: Array.from({ length: 33 }, () => "signal"),
      },
      { ...projection, available_signals: [1] },
      { ...projection, missing_reason_counts: null },
      {
        ...projection,
        missing_reason_counts: Object.fromEntries(
          Array.from({ length: 17 }, (_, index) => [`reason_${index}`, 1]),
        ),
      },
      { ...projection, missing_reason_counts: { missing: 129 } },
      { ...projection, source_type: "x".repeat(25) },
      {
        ...projection,
        facts: Array.from({ length: 49 }, () => projection.facts[0]),
      },
      {
        ...projection,
        gaps: Array.from({ length: 17 }, () => ({ code: "gap" })),
      },
      { ...projection, claims: Array.from({ length: 9 }, () => ({})) },
    ];
    for (const value of invalid)
      expect(() => server.safeEvidence(value, vehicleId)).toThrow();

    const malformedFacts = [
      null,
      { ...projection.facts[0], id: "x".repeat(81) },
      { ...projection.facts[0], key: "x".repeat(161) },
      { ...projection.facts[0], type: null },
      { ...projection.facts[0], quality: null },
      { ...projection.facts[0], meaning: "x".repeat(241) },
      { ...projection.facts[0], unit: "x".repeat(49) },
      { ...projection.facts[0], value: { private: true } },
      {
        ...projection.facts[0],
        value: Array.from({ length: 33 }, () => "signal"),
      },
      { ...projection.facts[0], value: ["x".repeat(121)] },
    ];
    for (const fact of malformedFacts)
      expect(() =>
        server.safeEvidence({ ...projection, facts: [fact] }, vehicleId),
      ).toThrow();
    for (const value of [
      { ...projection, facts: "not-an-array" },
      { ...projection, gaps: [null] },
      { ...projection, claims: [null] },
      {
        ...projection,
        limitations: Array.from({ length: 13 }, () => "limitation"),
      },
    ])
      expect(() => server.safeEvidence(value, vehicleId)).toThrow();

    const privateProjection = server.safeEvidence(
      {
        ...projection,
        available_signals: [],
        missing_reason_counts: {},
        facts: [
          {
            ...projection.facts[0],
            key: "vehicle_vin",
            value: "SYNTHETIC-PRIVATE",
          },
        ],
        gaps: [{ code: "SIGNAL_UNAVAILABLE" }],
        claims: [
          {
            id: "claim-1",
            category: "support",
            template: "Observed fact",
            fact_ids: ["fact-1"],
          },
        ],
      },
      vehicleId,
    );
    expect(privateProjection).toMatchObject({
      available_signals: [],
      facts: [{ value: null, missing_reason: "REDACTED_FOR_OPERATOR_UI" }],
      gaps: [{ code: "SIGNAL_UNAVAILABLE" }],
      claims: [{ claim_id: "claim-1" }],
    });
  });

  it("validates paged history and receipt-linked AgentRun context", async () => {
    const server = await serverModule();
    const validPrediction = {
      schema_version: "phase9d-prediction-response-v1",
      receipt_id: vehicleId,
      result_type: "next_pull",
      horizon: "NEXT_PULL",
      task: "NEXT_PULL_FUEL_DEVIATION",
      family: null,
      status: "READY_SCORE",
      reason_code: null,
      requested_cutoff: "2026-10-01T12:00:00Z",
      effective_cutoff: "2026-10-01T12:00:00Z",
      source_role: "synthetic",
      model_version_id: vehicleId,
      detector_version_id: null,
      feature_set_version: "phase9a-pull-v2",
      decision: true,
      engineering_validation_score: 0.5,
      anomaly_score: null,
      threshold: null,
      score_is_probability: false,
      interpretation: "Engineering score.",
      limitation: "Not diagnosis.",
      quality: {
        quality_class: "high",
        observed_feature_count: 8,
        expected_feature_count: 8,
        coverage: 1,
        missing_reason_counts: {},
      },
    };
    const page = {
      schema_version: "phase9h-receipt-history-v1",
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
      items: [
        {
          prediction: validPrediction,
          recorded_at: "2026-10-01T12:01:00Z",
          vehicle_id: vehicleId,
          session_id: vehicleId,
          pull_id: vehicleId,
          configuration_id: null,
          source_type: null,
          evidence_available: false,
          evidence_completeness: null,
          evidence_integrity: null,
          captured_binding_state: "ACTIVATED",
          current_binding_state: "REVOKED",
        },
      ],
    };
    expect(server.safeHistory(page, vehicleId)).toMatchObject({
      items: [{ current_binding_state: "REVOKED" }],
    });
    const invalidPages = [
      null,
      { ...page, schema_version: "old" },
      { ...page, items: "not-an-array" },
      { ...page, items: Array.from({ length: 21 }, () => page.items[0]) },
      { ...page, total: -1 },
      { ...page, limit: 21 },
      { ...page, offset: 501 },
      { ...page, has_more: "false" },
      {
        ...page,
        items: [
          {
            ...page.items[0],
            vehicle_id: "00000000-0000-4000-8000-000000000001",
          },
        ],
      },
      { ...page, items: [{ ...page.items[0], session_id: "bad-id" }] },
      { ...page, items: [{ ...page.items[0], pull_id: "bad-id" }] },
      { ...page, items: [{ ...page.items[0], configuration_id: "bad-id" }] },
      { ...page, items: [{ ...page.items[0], source_type: "x".repeat(25) }] },
      { ...page, items: [{ ...page.items[0], evidence_available: "false" }] },
      {
        ...page,
        items: [{ ...page.items[0], captured_binding_state: "UNKNOWN" }],
      },
      { ...page, items: [{ ...page.items[0], recorded_at: "yesterday" }] },
      {
        ...page,
        items: [{ ...page.items[0], evidence_completeness: "UNKNOWN" }],
      },
      { ...page, items: [{ ...page.items[0], evidence_integrity: "FAILED" }] },
      { ...page, items: [{ ...page.items[0], evidence_available: true }] },
      {
        ...page,
        items: [{ ...page.items[0], evidence_completeness: "COMPLETE" }],
      },
      {
        ...page,
        items: [
          {
            ...page.items[0],
            prediction: { ...validPrediction, schema_version: "old" },
          },
        ],
      },
    ];
    for (const value of invalidPages)
      expect(() => server.safeHistory(value, vehicleId)).toThrow();

    const context = {
      schema_version: "phase9h-agent-context-v1",
      receipt_id: vehicleId,
      items: [
        {
          run_id: vehicleId,
          started_at: "2026-10-01T12:00:00Z",
          status: "completed",
          source_role: "synthetic",
          horizon: "NEXT_PULL",
          completeness: "COMPLETE",
          integrity: "VERIFIED",
        },
      ],
    };
    expect(server.safeAgentContext(context, vehicleId)).toMatchObject({
      items: [{ run_id: vehicleId }],
    });
    for (const value of [
      null,
      { ...context, schema_version: "old" },
      { ...context, receipt_id: "another-receipt" },
      { ...context, items: "not-an-array" },
      { ...context, items: Array.from({ length: 21 }, () => context.items[0]) },
      { ...context, items: [{ ...context.items[0], run_id: "bad-id" }] },
      { ...context, items: [{ ...context.items[0], started_at: "yesterday" }] },
      { ...context, items: [{ ...context.items[0], status: "unknown" }] },
      { ...context, items: [{ ...context.items[0], source_role: "unknown" }] },
      { ...context, items: [{ ...context.items[0], horizon: "UNKNOWN" }] },
      { ...context, items: [{ ...context.items[0], completeness: "UNKNOWN" }] },
      {
        ...context,
        items: [{ ...context.items[0], integrity: "FAILED_SOURCE_MISMATCH" }],
      },
    ])
      expect(() => server.safeAgentContext(value, vehicleId)).toThrow();
  });

  it("maps upstream statuses, malformed bodies, timeouts, network errors and bounded concurrency", async () => {
    const server = await serverModule();
    const path = `/api/v1/prediction-service/vehicles/${vehicleId}/runs`;
    for (const status of [429, 503, 504, 500]) {
      vi.stubGlobal(
        "fetch",
        vi.fn(
          async () =>
            new Response("{}", {
              status,
              headers: { "content-type": "application/json" },
            }),
        ),
      );
      await expect(
        server.predictionApiGet(request() as never, path),
      ).rejects.toThrow();
    }
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response("{bad", {
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    await expect(
      server.predictionApiGet(request() as never, path),
    ).rejects.toThrow("invalid data");
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(null, {
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    await expect(
      server.predictionApiGet(request() as never, path),
    ).rejects.toThrow();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new DOMException("timeout", "TimeoutError");
      }),
    );
    await expect(
      server.predictionApiGet(request() as never, path),
    ).rejects.toThrow("too long");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network");
      }),
    );
    await expect(
      server.predictionApiGet(request() as never, path),
    ).rejects.toThrow("temporarily unavailable");

    const releases: Array<() => void> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Promise<Response>((resolve) => {
            releases.push(() =>
              resolve(
                new Response("{}", {
                  headers: { "content-type": "application/json" },
                }),
              ),
            );
          }),
      ),
    );
    const active = Array.from({ length: 4 }, () =>
      server.predictionApiGet(request() as never, path),
    );
    await expect(
      server.predictionApiGet(request() as never, path),
    ).rejects.toThrow("busy");
    releases.forEach((release) => release());
    await Promise.all(active);
  });
});
