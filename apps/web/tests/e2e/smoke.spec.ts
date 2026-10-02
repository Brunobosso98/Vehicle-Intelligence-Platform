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
  await expect(page.getByText("E2E reference")).toBeVisible();
  await expect(page.getByRole("img", { name: /engine.rpm/ })).toBeVisible();
  await page.getByLabel("Signal").selectOption("vehicle.speed");
  await expect(page.getByRole("img", { name: /vehicle.speed/ })).toBeVisible();
});

function phase3Csv(anomalous: boolean): string {
  const rows = ["timestamp,signal,value,unit,record_id,sequence"];
  let sequence = 0;
  for (let tick = 0; tick <= 180; tick += 1) {
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
            ["oil_temp", 365, "K"],
            ["coolant_temp", 360, "K"],
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
            ["oil_temp", 365, "K"],
            ["coolant_temp", 360, "K"],
            ["hpfp", 8000000, "Pa"],
          ];
    const timestamp = new Date(
      Date.parse("2027-01-01T00:00:00Z") + tick * 200,
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
        generation: "F30",
        model_year: 2015,
        engine_code: "N55",
        nickname: "Phase 3 synthetic reference",
      },
    },
  );
  const vehicle = (await vehicleResponse.json()) as { id: string };
  const createSession = async (startedAt: string, anomalous: boolean) => {
    const response = await request.post(
      "http://127.0.0.1:8000/api/v1/sessions",
      {
        data: {
          vehicle_id: vehicle.id,
          source_type: "csv",
          source_reference: "synthetic-phase-3",
          started_at: startedAt,
          metadata: { synthetic: true },
        },
      },
    );
    const session = (await response.json()) as { id: string };
    expect(
      (
        await request.post(
          `http://127.0.0.1:8000/api/v1/sessions/${session.id}/imports/csv`,
          {
            multipart: {
              file: {
                name: "phase3.csv",
                mimeType: "text/csv",
                buffer: Buffer.from(phase3Csv(anomalous)),
              },
            },
          },
        )
      ).ok(),
    ).toBeTruthy();
    expect(
      (
        await request.post(
          `http://127.0.0.1:8000/api/v1/sessions/${session.id}/analysis`,
          { data: { profile: "generic-v1" } },
        )
      ).ok(),
    ).toBeTruthy();
    expect(
      (
        await request.post(
          `http://127.0.0.1:8000/api/v1/sessions/${session.id}/events/analyze`,
          { data: {} },
        )
      ).ok(),
    ).toBeTruthy();
    return session;
  };

  await createSession("2027-01-01T00:00:00Z", true);
  await page.goto("/");
  await expect(page.getByText("Phase 3 synthetic reference")).toBeVisible();
  await expect(page.getByRole("button", { name: /boost drop/i })).toBeVisible();
  await page.getByRole("button", { name: /boost drop/i }).click();
  await expect(page.getByText("Structured factual evidence")).toBeVisible();
  await expect(page.getByText("pull-behavior-detector 1.0.0")).toBeVisible();
  await page.getByLabel("Filter by event type").selectOption("boost_drop");
  await page.getByLabel("Filter by severity").selectOption("high");
  await page.getByRole("button", { name: "Pull 3" }).click();
  await expect(
    page.getByLabel("Events associated with selected pull"),
  ).toContainText("boost drop");

  await createSession("2028-01-01T00:00:00Z", false);
  await page.reload();
  await expect(
    page.getByText(
      "No configured anomaly events were detected in this session.",
    ),
  ).toBeVisible();
});
