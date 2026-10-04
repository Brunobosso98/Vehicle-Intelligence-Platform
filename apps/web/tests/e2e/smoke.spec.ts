import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("real API readiness, keyboard access and accessibility", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Engenharia guiada",
  );
  const systemStatus = page
    .getByRole("heading", { name: "Status do sistema" })
    .locator("..")
    .getByRole("status");
  await expect(systemStatus).toContainText("Operacional");
  await expect(systemStatus).toContainText("Pronto");
  await page.getByRole("button", { name: "Atualizar status" }).focus();
  await expect(
    page.getByRole("button", { name: "Atualizar status" }),
  ).toBeFocused();
  expect(
    (await new AxeBuilder({ page }).setLegacyMode(true).analyze()).violations,
  ).toEqual([]);
});
test("API unreachable shows a recoverable error", async ({ page }) => {
  await page.route("**/api/status", (route) => route.abort());
  await page.goto("/");
  const systemStatus = page
    .getByRole("heading", { name: "Status do sistema" })
    .locator("..")
    .getByRole("status");
  await expect(systemStatus).toContainText("Não foi possível conectar");
  await page.unroute("**/api/status");
  await page.getByRole("button", { name: "Atualizar status" }).click();
  await expect(systemStatus).toContainText("Operacional");
});

test("real imported session renders telemetry and changes signal", async ({
  page,
  request,
}) => {
  const vehicle = await request.post("http://127.0.0.1:8000/api/v1/vehicles", {
    data: {
      manufacturer: "BMW",
      model: "335i",
      generation: "F30",
      model_year: 2015,
      engine_code: "N55",
      nickname: "E2E reference",
    },
  });
  expect(vehicle.ok()).toBeTruthy();
  const vehicleBody = (await vehicle.json()) as { id: string };
  const session = await request.post("http://127.0.0.1:8000/api/v1/sessions", {
    data: {
      vehicle_id: vehicleBody.id,
      source_type: "csv",
      started_at: "2026-01-01T00:00:00Z",
    },
  });
  const sessionBody = (await session.json()) as { id: string };
  const imported = await request.post(
    `http://127.0.0.1:8000/api/v1/sessions/${sessionBody.id}/imports/csv`,
    {
      multipart: {
        file: {
          name: "e2e.csv",
          mimeType: "text/csv",
          buffer: Buffer.from(
            "timestamp,signal,value,unit,record_id,sequence\n" +
              "2026-01-01T00:00:00Z,rpm,800,rpm,1,1\n" +
              "2026-01-01T00:00:01Z,rpm,1200,rpm,2,2\n" +
              "2026-01-01T00:00:00Z,speed,0,km/h,3,3\n" +
              "2026-01-01T00:00:01Z,speed,20,km/h,4,4\n",
          ),
        },
      },
    },
  );
  expect(imported.ok()).toBeTruthy();
  await page.goto("/");
  await page
    .getByLabel("Vehicle", { exact: true })
    .selectOption(vehicleBody.id);
  await expect(
    page.getByRole("heading", { name: "E2E reference" }),
  ).toBeVisible();
  await expect(page.getByRole("img", { name: /engine.rpm/ })).toBeVisible();
  await page
    .getByLabel("Signal", { exact: true })
    .selectOption("vehicle.speed");
  await expect(page.getByRole("img", { name: /vehicle.speed/ })).toBeVisible();
});

function phase3Csv(anomalous: boolean, startedAt: string): string {
  const rows = ["timestamp,signal,value,unit,record_id,sequence"];
  let sequence = 0;
  for (let tick = 0; tick <= 155; tick += 1) {
    const second = tick / 5;
    const pullIndex =
      second >= 5 && second < 11
        ? 0
        : second >= 15 && second < 21
          ? 1
          : second >= 25 && second < 31
            ? 2
            : -1;
    const pullStart = pullIndex === 0 ? 5 : pullIndex === 1 ? 15 : 25;
    const offset = pullIndex >= 0 ? second - pullStart : 0;
    const values: [string, number, string][] =
      pullIndex >= 0
        ? [
            ["rpm", 2200 + offset * 500, "rpm"],
            ["speed", 18 + offset * 2, "m/s"],
            ["throttle", 90, "%"],
            [
              "boost",
              anomalous && pullIndex === 2 ? 85000 : 115000 + offset * 1000,
              "Pa",
            ],
            [
              "iat",
              anomalous && pullIndex === 2
                ? 314 + offset * 3
                : 300 + offset * 0.5,
              "K",
            ],
            [
              "hpfp",
              anomalous && pullIndex === 1 && offset >= 2 ? 14000000 : 19000000,
              "Pa",
            ],
          ]
        : [
            ["rpm", 2100, "rpm"],
            ["speed", 20, "m/s"],
            ["throttle", 20, "%"],
            ["boost", 5000, "Pa"],
            ["iat", 301, "K"],
            ["hpfp", 8000000, "Pa"],
          ];
    const timestamp = new Date(
      Date.parse(startedAt) + tick * 200,
    ).toISOString();
    for (const [signal, value, unit] of values) {
      rows.push(
        `${timestamp},${signal},${value},${unit},p3-${sequence},${sequence}`,
      );
      sequence += 1;
    }
  }
  return rows.join("\n");
}

test("Phase 3 real-stack events remain factual, filterable and pull-associated", async ({
  page,
  request,
}) => {
  const vehicleResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/vehicles",
    {
      data: {
        manufacturer: "BMW",
        model: "335i",
        nickname: "Phase 3 independent events",
      },
    },
  );
  expect(vehicleResponse.ok()).toBeTruthy();
  const vehicle = (await vehicleResponse.json()) as { id: string };
  expect(vehicle).toBeDefined();
  const existingSessions = (await (
    await request.get(
      `http://127.0.0.1:8000/api/v1/sessions?vehicle_id=${vehicle.id}`,
    )
  ).json()) as { started_at: string | null }[];
  let newestStartedAt = Math.max(
    Date.parse("2090-01-01T00:00:00Z"),
    ...existingSessions.map((session) =>
      session.started_at ? Date.parse(session.started_at) : 0,
    ),
  );
  const createSession = async (startedAt: string, anomalous: boolean) => {
    // The UI opens the latest session. Repeated local runs retain their fixtures.
    newestStartedAt = Math.max(
      Date.parse(startedAt),
      newestStartedAt + 86_400_000,
    );
    const sessionStartedAt = new Date(newestStartedAt).toISOString();
    const response = await request.post(
      "http://127.0.0.1:8000/api/v1/sessions",
      {
        data: {
          vehicle_id: vehicle.id,
          source_type: "csv",
          source_reference: "synthetic-phase-3",
          started_at: sessionStartedAt,
          metadata: { synthetic: true },
        },
      },
    );
    const session = (await response.json()) as { id: string };
    const imported = await request.post(
      `http://127.0.0.1:8000/api/v1/sessions/${session.id}/imports/csv`,
      {
        multipart: {
          file: {
            name: "phase3.csv",
            mimeType: "text/csv",
            buffer: Buffer.from(phase3Csv(anomalous, sessionStartedAt)),
          },
        },
      },
    );
    expect(imported.ok(), await imported.text()).toBeTruthy();
    const analysis = await request.post(
      `http://127.0.0.1:8000/api/v1/sessions/${session.id}/analysis`,
      { data: { profile: "generic-v1" } },
    );
    const analysisBody = await analysis.text();
    expect(analysis.ok(), analysisBody).toBeTruthy();
    expect(
      (JSON.parse(analysisBody) as { pull_count: number }).pull_count,
    ).toBe(3);
    const eventAnalysis = await request.post(
      `http://127.0.0.1:8000/api/v1/sessions/${session.id}/events/analyze`,
      { data: {} },
    );
    expect(eventAnalysis.ok(), await eventAnalysis.text()).toBeTruthy();
    const events = await request.get(
      `http://127.0.0.1:8000/api/v1/sessions/${session.id}/events`,
    );
    expect(events.ok()).toBeTruthy();
    if (anomalous) {
      expect((await events.json()) as { event_type: string }[]).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ event_type: "boost_drop" }),
        ]),
      );
    }
    return session;
  };

  await createSession("2090-01-01T00:00:00Z", true);
  await page.goto("/");
  await page.getByLabel("Vehicle", { exact: true }).selectOption(vehicle.id);
  await expect(page.getByRole("button", { name: /boost drop/i })).toBeVisible();
  await page.getByRole("button", { name: /boost drop/i }).click();
  await expect(page.getByText("Structured factual evidence")).toBeVisible();
  await expect(page.getByText("pull-behavior-detector 1.1.0")).toBeVisible();
  await page.screenshot({
    path: "test-results/phase3-event-inspector.png",
    fullPage: true,
  });
  await page.getByLabel("Filter by event type").selectOption("boost_drop");
  await page.getByLabel("Filter by severity").selectOption("high");
  await page.getByRole("button", { name: "Pull 3" }).click();
  await expect(
    page.getByLabel("Events associated with selected pull"),
  ).toContainText("boost drop");

  await createSession("2091-01-01T00:00:00Z", false);
  await page.reload();
  await page.getByLabel("Vehicle", { exact: true }).selectOption(vehicle.id);
  await expect(
    page.getByText(
      "No configured anomaly events were detected in this session.",
    ),
  ).toBeVisible();
});

test("Phase 4 durable live acquisition finalizes provisional telemetry canonically", async ({
  page,
  request,
}) => {
  const vehicleResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/vehicles",
    {
      data: {
        manufacturer: "BMW",
        model: "335i",
        generation: "F30",
        model_year: 2015,
        engine_code: "N55",
        nickname: "Phase 4 live N55",
      },
    },
  );
  const vehicle = (await vehicleResponse.json()) as { id: string };
  const createdResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/acquisitions",
    {
      data: {
        vehicle_id: vehicle.id,
        recipe_key: "performance-pull",
        adapter: "synthetic",
        source_id: "playwright-synthetic",
      },
    },
  );
  expect(createdResponse.ok(), await createdResponse.text()).toBeTruthy();
  const acquisition = (await createdResponse.json()) as {
    id: string;
    driving_session_id: string;
    ingestion_token: string;
  };
  const started = new Date(Date.now() - 60_000).toISOString();
  const rows = phase3Csv(true, started).split("\n").slice(1).filter(Boolean);
  const canonical: Record<string, string> = {
    rpm: "engine.rpm",
    speed: "vehicle.speed",
    throttle: "engine.throttle_position",
    boost: "engine.boost_pressure",
    iat: "engine.intake_air_temperature",
    hpfp: "fuel.high_pressure",
  };
  const observations = rows.map((row, index) => {
    const [observed_at, signal, value, unit, source_record_id] = row.split(",");
    return {
      message_id: crypto.randomUUID(),
      observed_at,
      sequence: index,
      signal: canonical[signal],
      value: Number(value),
      unit,
      source_record_id,
    };
  });
  for (let offset = 0; offset < observations.length; offset += 500) {
    const response = await request.post(
      `http://127.0.0.1:8000/api/v1/acquisitions/${acquisition.id}/batches`,
      {
        headers: { authorization: `Bearer ${acquisition.ingestion_token}` },
        data: {
          schema_version: "1.0",
          batch_id: crypto.randomUUID(),
          observations: observations.slice(offset, offset + 500),
        },
      },
    );
    expect(response.status()).toBe(202);
  }
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `http://127.0.0.1:8000/api/v1/sessions/${acquisition.driving_session_id}`,
        );
        return ((await response.json()) as { sample_count: number })
          .sample_count;
      },
      { timeout: 30_000 },
    )
    .toBe(observations.length);
  const stopped = await request.post(
    `http://127.0.0.1:8000/api/v1/acquisitions/${acquisition.id}/stop`,
    { headers: { authorization: `Bearer ${acquisition.ingestion_token}` } },
  );
  expect(stopped.ok()).toBeTruthy();
  const rejected = await request.post(
    `http://127.0.0.1:8000/api/v1/acquisitions/${acquisition.id}/batches`,
    {
      headers: { authorization: `Bearer ${acquisition.ingestion_token}` },
      data: {
        schema_version: "1.0",
        batch_id: crypto.randomUUID(),
        observations: observations.slice(0, 1),
      },
    },
  );
  expect(rejected.status()).toBe(401);
  const finalized = await request.post(
    `http://127.0.0.1:8000/api/v1/acquisitions/${acquisition.id}/finalize`,
  );
  expect(finalized.ok(), await finalized.text()).toBeTruthy();
  const result = (await finalized.json()) as {
    state: string;
    phase2: { pull_count: number };
    phase3: { event_count: number };
    capability_report: { recipe_adherence: boolean };
  };
  expect(result.state).toBe("completed");
  expect(result.phase2.pull_count).toBe(3);
  expect(result.phase3.event_count).toBeGreaterThan(0);
  expect(result.capability_report.recipe_adherence).toBeTruthy();

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Plan a read-only acquisition" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /preflight/i }).click();
  await expect(page.getByText("READY")).toBeVisible();
  await page.screenshot({
    path: "test-results/phase4-live-acquisition.png",
    fullPage: true,
  });

  const degraded = await request.post(
    "http://127.0.0.1:8000/api/v1/logging/recipes/performance-pull/preflight",
    {
      data: {
        adapter: "synthetic-degraded",
        maximum_requests_per_second: 30,
        signals: {
          "engine.rpm": "supported",
          "vehicle.speed": "supported",
          "engine.throttle_position": "supported",
          "engine.boost_pressure": "unsupported",
        },
      },
    },
  );
  expect(
    (await degraded.json()) as {
      readiness: string;
      unavailable_capabilities: string[];
    },
  ).toEqual(
    expect.objectContaining({
      readiness: "degraded",
      unavailable_capabilities: expect.arrayContaining(["boost_analysis"]),
    }),
  );
});

test("Phase 5 real-stack analytics workspace", async ({ page, request }) => {
  test.setTimeout(600_000);
  const vehicleResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/vehicles",
    {
      data: {
        manufacturer: "BMW",
        model: "335i",
        nickname: "Phase 5 independent browser history",
      },
    },
  );
  expect(vehicleResponse.ok(), await vehicleResponse.text()).toBeTruthy();
  const vehicleId = ((await vehicleResponse.json()) as { id: string }).id;
  async function configuration(description: string, effective_at: string) {
    const response = await request.post(
      `http://127.0.0.1:8000/api/v1/vehicles/${vehicleId}/configurations`,
      { data: { effective_at, description, provenance: "phase5-browser-e2e" } },
    );
    expect(response.ok(), await response.text()).toBeTruthy();
    return (await response.json()) as { id: string };
  }
  const configurationA = await configuration(
    "Phase 5 configuration A",
    "2060-01-01T00:00:00Z",
  );
  const configurationB = await configuration(
    "Phase 5 configuration B",
    "2070-01-01T00:00:00Z",
  );
  const analyticsCsv = (changed: boolean, startedAt: string) => {
    const rows = ["timestamp,signal,value,unit,record_id,sequence"];
    let sequence = 0;
    for (let tick = 0; tick <= 90; tick += 1) {
      const second = tick / 5;
      const start =
        second >= 1 && second <= 5
          ? 1
          : second >= 7 && second <= 11
            ? 7
            : second >= 13 && second <= 17
              ? 13
              : -1;
      const offset = start < 0 ? 0 : second - start;
      const signals: [string, number, string][] =
        start >= 0
          ? [
              ["rpm", 2800 + offset * 450, "rpm"],
              ["speed", 18 + offset * (changed ? 1.7 : 2), "m/s"],
              ["throttle", 90, "%"],
              ["boost", (changed ? 105000 : 120000) + offset * 500, "Pa"],
              ["iat", (changed ? 315 : 300) + offset, "K"],
              ["hpfp", changed ? 17500000 : 19000000, "Pa"],
            ]
          : [
              ["rpm", 2200, "rpm"],
              ["speed", 16, "m/s"],
              ["throttle", 20, "%"],
              ["boost", 5000, "Pa"],
              ["iat", changed ? 314 : 299, "K"],
              ["hpfp", 12000000, "Pa"],
            ];
      for (const [signal, value, unit] of signals) {
        rows.push(
          `${new Date(Date.parse(startedAt) + tick * 200).toISOString()},${signal},${value},${unit},p5-${sequence},${sequence}`,
        );
        sequence += 1;
      }
    }
    return rows.join("\n");
  };
  for (const [configurationId, year, changed] of [
    [configurationA.id, 2061, false],
    [configurationA.id, 2062, false],
    [configurationA.id, 2063, false],
    [configurationB.id, 2071, true],
    [configurationB.id, 2072, true],
    [configurationB.id, 2073, true],
  ] as const) {
    const startedAt = `${year}-01-01T00:00:00Z`;
    const created = await request.post(
      "http://127.0.0.1:8000/api/v1/sessions",
      {
        data: {
          vehicle_id: vehicleId,
          configuration_id: configurationId,
          source_type: "csv",
          started_at: startedAt,
        },
      },
    );
    const session = (await created.json()) as { id: string };
    const imported = await request.post(
      `http://127.0.0.1:8000/api/v1/sessions/${session.id}/imports/csv`,
      {
        multipart: {
          file: {
            name: "phase5.csv",
            mimeType: "text/csv",
            buffer: Buffer.from(analyticsCsv(changed, startedAt)),
          },
        },
      },
    );
    expect(imported.ok(), await imported.text()).toBeTruthy();
    const analyzed = await request.post(
      `http://127.0.0.1:8000/api/v1/sessions/${session.id}/analysis`,
      { data: { profile: "generic-v1" } },
    );
    expect(analyzed.ok(), await analyzed.text()).toBeTruthy();
  }
  await page.goto("/");
  await page.getByLabel("Vehicle", { exact: true }).selectOption(vehicleId);
  await expect(
    page.getByRole("heading", { name: "Analytics workspace" }),
  ).toBeVisible();
  await expect(
    page.getByText(/Observed association is not root-cause/),
  ).toBeVisible();
  const choices = page
    .getByRole("group", { name: "Select 2–3 pulls" })
    .getByRole("checkbox");
  await choices.nth(0).check();
  await choices.nth(1).check();
  await page.getByRole("button", { name: "Compare pulls" }).click();
  const result = page.locator(".analytics-result");
  await expect(
    result.getByRole("heading", { name: "RPM-normalized comparison" }),
  ).toBeVisible();
  await expect(result.getByText("Algorithm")).toBeVisible();
  await page.screenshot({
    path: "test-results/phase5-pull-comparison.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Analyze repeated pulls" }).click();
  await expect(
    result.getByRole("heading", { name: "Repeated-pull progression" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Summarize selected session" })
    .click();
  await expect(result.getByLabel("Session analytics summary")).toContainText(
    "546",
  );
  await page
    .getByLabel("Vehicle configuration")
    .selectOption(configurationA.id);
  await page.getByRole("button", { name: "Build historical baseline" }).click();
  await expect(
    result.getByRole("heading", { name: "Observed historical baseline" }),
  ).toBeVisible();
  await expect(
    result.getByText("3 sessions · 9 contributing pulls · 0 excluded"),
  ).toBeVisible();
  await page.getByRole("button", { name: "View boost history" }).click();
  await expect(
    result.getByRole("heading", { name: "Configuration-segmented history" }),
  ).toBeVisible();
  await page.getByLabel("Before configuration").selectOption(configurationA.id);
  await page.getByLabel("After configuration").selectOption(configurationB.id);
  await page.getByRole("button", { name: "Compare configurations" }).click();
  await expect(
    result.getByRole("heading", { name: "Observed before/after difference" }),
  ).toBeVisible();
  await expect(
    result.getByRole("cell", { name: "-15000.00", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/phase5-history-before-after.png",
    fullPage: true,
  });
  const insufficient = await configuration(
    "Phase 5 insufficient history",
    "2080-01-01T00:00:00Z",
  );
  await page.reload();
  await page.getByLabel("Vehicle", { exact: true }).selectOption(vehicleId);
  await page.getByLabel("Vehicle configuration").selectOption(insufficient.id);
  await page.getByRole("button", { name: "Build historical baseline" }).click();
  await expect(result.getByText("insufficient", { exact: true })).toBeVisible();
  await expect(result.getByRole("status")).toContainText(
    "insufficient_same_configuration_sessions",
  );
  await expect(
    result.getByText("0 sessions · 0 contributing pulls · 0 excluded"),
  ).toBeVisible();
});

test("Phase 4 browser reconciles streamed provisional findings to canonical results", async ({
  page,
}) => {
  await page.goto("/");
  const live = page.getByRole("region", {
    name: "Plan a read-only acquisition",
  });
  await live
    .getByRole("button", { name: "Run synthetic device preflight" })
    .click();
  await expect(live.getByText("READY", { exact: true })).toBeVisible();
  await live
    .getByRole("button", { name: "Start synthetic live acquisition" })
    .click();
  await expect(
    live.getByText("Acquisition: active", { exact: true }),
  ).toBeVisible();
  const provisional = live.getByLabel("Provisional live findings");
  await expect(
    provisional.getByText(/boost drop · provisional/).first(),
  ).toBeVisible({ timeout: 30_000 });

  await expect(
    provisional.getByText("LIVE / PROVISIONAL", { exact: true }),
  ).toBeVisible();
  await expect(
    provisional.getByText(/possible pull · provisional/).first(),
  ).toBeVisible();
  await expect(live.getByLabel("Actual signal quality")).toBeVisible();
  await expect(
    live.getByText(/^Collector: (connected|disconnected)$/),
  ).toBeVisible();
  await expect(
    live.getByRole("img", { name: "engine.rpm provisional time-series chart" }),
  ).toBeVisible();
  for (let reconnection = 0; reconnection < 12; reconnection += 1) {
    await page.context().setOffline(true);
    await expect(
      live.getByText("Acquisition: disconnected", { exact: true }),
    ).toBeVisible();
    await page.context().setOffline(false);
    await expect(
      live.getByText("Acquisition: active", { exact: true }),
    ).toBeVisible();
  }
  await page.screenshot({
    path: "test-results/phase4-browser-provisional.png",
    fullPage: true,
  });
  await live.getByRole("button", { name: "Stop and finalize" }).click();
  const canonical = live.getByLabel("Canonical final results");
  await expect(
    canonical.getByText("FINAL CANONICAL RESULTS", { exact: true }),
  ).toBeVisible();
  await expect(
    canonical.getByText(/Phase 2 complete · [1-9]\d* pull/),
  ).toBeVisible();
  await expect(
    canonical.getByText(/Phase 3 complete · [1-9]\d* factual event/),
  ).toBeVisible();
  await expect(
    canonical.getByText(/Reconciled: [1-9]\d* confirmed/),
  ).toBeVisible();
  await expect(
    live.getByText("Acquisition: completed", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/phase4-browser-canonical.png",
    fullPage: true,
  });
});

test("Phase 4 degraded recipe exposes a missing simulated boost capability", async ({
  page,
}) => {
  const vehicleResponse = await page.request.post("/api/domain/vehicles", {
    data: {
      manufacturer: "BMW",
      model: "335i",
      generation: "F30",
      model_year: 2015,
      engine_code: "N55",
      nickname: "Degraded acquisition fixture",
    },
  });
  expect(vehicleResponse.status()).toBe(201);
  const vehicle = await vehicleResponse.json();
  await page.goto("/");
  await page.getByLabel("Vehicle", { exact: true }).selectOption(vehicle.id);
  const live = page.getByRole("region", {
    name: "Plan a read-only acquisition",
  });
  await live
    .getByLabel("Synthetic scenario")
    .selectOption("missing_recommended");
  await live
    .getByRole("button", { name: "Run synthetic device preflight" })
    .click();
  await expect(live.getByText("DEGRADED", { exact: true })).toBeVisible();
  await expect(live.getByText(/Unavailable: .*boost_analysis/)).toBeVisible();
  await expect(live.getByLabel("Capability matrix")).not.toContainText(
    "engine.boost_pressure",
  );
});
