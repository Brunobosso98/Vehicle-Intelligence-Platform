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
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
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
  await expect(
    page.getByRole("heading", { name: "E2E reference" }),
  ).toBeVisible();
  await expect(page.getByRole("img", { name: /engine.rpm/ })).toBeVisible();
  await page.getByLabel("Signal").selectOption("vehicle.speed");
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
  const vehicleResponse = await request.get(
    "http://127.0.0.1:8000/api/v1/vehicles",
  );
  const vehicles = (await vehicleResponse.json()) as { id: string }[];
  const vehicle = vehicles[0];
  expect(vehicle).toBeDefined();
  const createSession = async (startedAt: string, anomalous: boolean) => {
    const sessionStartedAt = new Date(
      Date.parse(startedAt) + (Date.now() % 86_400_000),
    ).toISOString();
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
    const [header, ...csvRows] = phase3Csv(anomalous, sessionStartedAt).split(
      "\n",
    );
    for (let offset = 0; offset < csvRows.length; offset += 200) {
      const imported = await request.post(
        `http://127.0.0.1:8000/api/v1/sessions/${session.id}/imports/csv`,
        {
          multipart: {
            file: {
              name: `phase3-${offset}.csv`,
              mimeType: "text/csv",
              buffer: Buffer.from(
                [header, ...csvRows.slice(offset, offset + 200)].join("\n"),
              ),
            },
          },
        },
      );
      expect(imported.ok(), await imported.text()).toBeTruthy();
    }
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
  await expect(page.getByRole("button", { name: /boost drop/i })).toBeVisible();
  await page.getByRole("button", { name: /boost drop/i }).click();
  await expect(page.getByText("Structured factual evidence")).toBeVisible();
  await expect(page.getByText("pull-behavior-detector 1.0.0")).toBeVisible();
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

test("Phase 5 real-stack analytics workspace", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Analytics workspace" }),
  ).toBeVisible();
  await expect(
    page.getByText(/Observed association is not root-cause/),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/phase5-analytics-workspace.png",
    fullPage: true,
  });
});
