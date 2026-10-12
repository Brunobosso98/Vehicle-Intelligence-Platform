import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("supervisor routing, structured specialists, conflict, grounded evidence and investigation", async ({
  page,
}) => {
  test.setTimeout(240_000);
  test.skip(
    !process.env.SUPERVISOR_E2E_FIXTURE_FILE,
    "Run make test-supervisor-e2e for isolated fixtures",
  );
  const fixture = JSON.parse(
    readFileSync(process.env.SUPERVISOR_E2E_FIXTURE_FILE!, "utf8"),
  );
  // Session selection is a supported API input; retain real UI/SSE/API/MCP execution.
  let session = fixture.recordings.thermal;
  await page.route("**/api/domain/vehicles/*/agent-runs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.continue({
      postData: JSON.stringify({
        ...route.request().postDataJSON(),
        session_id: session,
      }),
    });
  });
  await page.goto("/");
  await page
    .getByLabel("Vehicle", { exact: true })
    .selectOption(fixture.vehicle);
  const workspace = page.getByRole("region", {
    name: "Vehicle Intelligence Agent",
  });
  await workspace
    .getByLabel("Pergunta sobre o veículo")
    .fill("Why did performance degrade after repeated pulls?");
  await workspace.getByRole("button", { name: "Consultar agente" }).click();
  const result = workspace.getByTestId("agent-result");
  await expect(result).toBeVisible({ timeout: 95_000 });
  const specialists = result.getByRole("region", {
    name: "Especialistas consultados",
  });
  await expect(specialists).toContainText("Qualidade dos dados — completed");
  await expect(specialists).toContainText("Desempenho — completed");
  await expect(specialists).toContainText("Comportamento térmico — completed");
  await expect(specialists).not.toContainText(
    "Combustível, ar e pressão de carga — completed",
  );
  const progress = workspace
    .getByText("Progresso das consultas", { exact: true })
    .locator("..");
  await expect(progress).toContainText(
    "Especialistas selecionados: Desempenho, Comportamento térmico.",
  );
  await expect(progress).toContainText("Qualidade dos dados: concluído.");
  await specialists
    .getByText("Desempenho — completed", { exact: true })
    .click();
  await specialists
    .getByText("Comportamento térmico — completed", { exact: true })
    .click();
  await expect(specialists).toContainText("OBSERVATION");
  await expect(specialists).toContainText("Evidências:");
  await workspace.getByText("Expandir evidências", { exact: true }).click();
  await expect(result).toContainText("get_repeated_pull_analysis");
  await expect(result).not.toContainText("SUPPORTED_CONCLUSION");
  session = fixture.recordings.mixed;
  await workspace
    .getByLabel("Pergunta sobre o veículo")
    .fill("Why did performance degrade after repeated pulls?");
  await workspace.getByRole("button", { name: "Consultar agente" }).click();
  await expect(workspace.getByRole("status")).toHaveText("Resposta validada.", {
    timeout: 95_000,
  });
  await expect(specialists).toContainText(
    "Combustível, ar e pressão de carga — completed",
  );
  await expect(
    specialists.getByRole("note", { name: "Interpretações concorrentes" }),
  ).toBeVisible();
  await expect(specialists).toContainText("Evidência insuficiente ou limitada");
  await expect(result).toContainText("INSUFFICIENT_EVIDENCE");
  await expect(
    workspace.getByRole("button", { name: /investigação/i }).first(),
  ).toBeVisible();
  await expect(result).not.toContainText("SUPPORTED_CONCLUSION");
  await expect(workspace.locator("img")).toHaveCount(0);
  const accessibility = await new AxeBuilder({ page })
    .include(".agent-workspace")
    .analyze();
  expect(accessibility.violations).toEqual([]);
});
