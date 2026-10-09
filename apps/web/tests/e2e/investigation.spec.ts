import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("approve, capture, link, and inspect a grounded follow-up", async ({
  page,
  request,
}) => {
  test.setTimeout(240_000);
  test.skip(
    !process.env.INVESTIGATION_E2E_FIXTURE_FILE ||
      !process.env.INVESTIGATION_E2E_TOKEN,
    "Run make test-investigation-e2e with isolated fixtures",
  );
  const fixture = JSON.parse(
    readFileSync(process.env.INVESTIGATION_E2E_FIXTURE_FILE!, "utf8"),
  );
  await page.goto("/");
  await page
    .getByLabel("Vehicle", { exact: true })
    .selectOption(fixture.vehicle);
  const workspace = page.getByRole("region", {
    name: "Vehicle Intelligence Agent",
  });
  await workspace
    .getByLabel("Pergunta sobre o veículo")
    .fill("Why did the third pull get slower with timing missing?");
  await workspace.getByRole("button", { name: "Consultar agente" }).click();
  await expect(workspace.getByTestId("agent-result")).toBeVisible({
    timeout: 90_000,
  });
  const investigation = workspace.getByRole("region", {
    name: "Investigar evidências insuficientes",
  });
  await expect(investigation).toBeVisible();
  await investigation
    .getByLabel("Credencial do operador")
    .fill(process.env.INVESTIGATION_E2E_TOKEN!);
  await investigation.getByLabel("Fonte de leitura").selectOption("synthetic");
  await investigation
    .getByLabel("Identificação da fonte")
    .fill("browser-fixture");
  await investigation
    .getByRole("button", { name: "Criar investigação" })
    .click();
  await expect(investigation).toContainText("AWAITING_APPROVAL", {
    timeout: 30_000,
  });
  await expect(investigation).toContainText("timing_behavior");
  await expect(investigation).toContainText("UNAVAILABLE");
  await expect(investigation).toContainText("performance-pull");
  await expect(investigation).toContainText("Hash de configuração");
  const accessibility = await new AxeBuilder({ page })
    .include(".investigation-workspace")
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await investigation
    .getByRole("button", { name: "Aprovar esta versão e receita" })
    .click();
  await expect(investigation).toContainText("ACQUISITION_READY");
  await expect(investigation).toContainText("Recipe ready for acquisition");
  const api = process.env.INVESTIGATION_E2E_API!;
  const operator = {
    "X-Investigation-Token": process.env.INVESTIGATION_E2E_TOKEN!,
  };
  const list = await request.get(
    `${api}/api/v1/vehicles/${fixture.vehicle}/investigations`,
    {
      headers: operator,
    },
  );
  expect(list.ok()).toBeTruthy();
  const [plan] = await list.json();
  expect(plan.status).toBe("ACQUISITION_READY");
  const created = await request.post(`${api}/api/v1/acquisitions`, {
    data: {
      vehicle_id: fixture.vehicle,
      configuration_id: plan.configuration_id,
      recipe_key: plan.recipe.key,
      adapter: "synthetic",
      source_id: "browser-fixture",
    },
  });
  expect(created.status(), await created.text()).toBe(201);
  const acquisition = await created.json();
  const acquisitionHeaders = {
    Authorization: `Bearer ${acquisition.ingestion_token}`,
  };
  const capture = await request.post(
    `${api}/api/v1/acquisitions/${acquisition.id}/synthetic?scenario=boost_drop`,
    { headers: acquisitionHeaders, timeout: 90_000 },
  );
  expect(capture.status(), await capture.text()).toBe(202);
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `${api}/api/v1/acquisitions/${acquisition.id}`,
        );
        return (await response.json()).quality.collector?.adapter_state;
      },
      { timeout: 90_000 },
    )
    .toBe("disconnected");
  const stopped = await request.post(
    `${api}/api/v1/acquisitions/${acquisition.id}/stop`,
    { headers: acquisitionHeaders },
  );
  expect(stopped.ok(), await stopped.text()).toBeTruthy();
  const finalized = await request.post(
    `${api}/api/v1/acquisitions/${acquisition.id}/finalize`,
    { timeout: 90_000 },
  );
  expect(finalized.ok(), await finalized.text()).toBeTruthy();
  expect((await finalized.json()).state).toBe("completed");
  await investigation
    .getByLabel("ID da sessão finalizada")
    .fill(acquisition.driving_session_id);
  await investigation.getByRole("button", { name: "Vincular sessão" }).click();
  await expect(investigation).toContainText(acquisition.driving_session_id, {
    timeout: 60_000,
  });
  await expect(investigation).toContainText("Resultado da investigação", {
    timeout: 60_000,
  });
  await expect(investigation).toContainText("Classificação: ASSOCIATION");
  await expect(investigation).toContainText(
    "mechanical cause and failed components are not established",
  );
  await expect(investigation).toContainText("SUPPORTED");
  await investigation
    .getByRole("button", { name: "Abrir resposta de acompanhamento" })
    .click();
  await expect(workspace.getByTestId("agent-result")).toBeVisible();
  await expect(workspace).toContainText(/timing/i);
  await workspace.getByText("Expandir evidências").click();
  await expect(
    workspace.getByRole("region", { name: /Fatos observados:/ }).first(),
  ).toBeVisible();
});

test("documentation gap stays outside telemetry capture", async ({ page }) => {
  test.setTimeout(120_000);
  test.skip(
    !process.env.INVESTIGATION_E2E_FIXTURE_FILE ||
      !process.env.INVESTIGATION_E2E_TOKEN,
    "Run make test-investigation-e2e with isolated fixtures",
  );
  const fixture = JSON.parse(
    readFileSync(process.env.INVESTIGATION_E2E_FIXTURE_FILE!, "utf8"),
  );
  await page.goto("/");
  await page
    .getByLabel("Vehicle", { exact: true })
    .selectOption(fixture.vehicle);
  const workspace = page.getByRole("region", {
    name: "Vehicle Intelligence Agent",
  });
  await workspace
    .getByLabel("Pergunta sobre o veículo")
    .fill("Why is the factory specification absent from the manual?");
  await workspace.getByRole("button", { name: "Consultar agente" }).click();
  const investigation = workspace.getByRole("region", {
    name: "Investigar evidências insuficientes",
  });
  await expect(investigation).toBeVisible({ timeout: 90_000 });
  await investigation
    .getByLabel("Credencial do operador")
    .fill(process.env.INVESTIGATION_E2E_TOKEN!);
  await investigation.getByLabel("Fonte de leitura").selectOption("synthetic");
  await investigation.getByLabel("Identificação da fonte").fill("browser-doc");
  await investigation
    .getByRole("button", { name: "Criar investigação" })
    .click();
  await expect(investigation).toContainText("INCONCLUSIVE", {
    timeout: 30_000,
  });
  await expect(investigation.getByText("Receita proposta")).toHaveCount(0);
});
