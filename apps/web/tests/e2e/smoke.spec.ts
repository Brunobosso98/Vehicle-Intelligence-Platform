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
