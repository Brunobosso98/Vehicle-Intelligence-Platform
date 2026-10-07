import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("grounded vehicle question, evidence, modifications and insufficient causal evidence", async ({
  page,
}) => {
  // Two independently bounded 90-second runs plus 30 seconds for browser interaction.
  test.setTimeout(210_000);
  test.skip(
    !process.env.AGENT_E2E_FIXTURE_FILE,
    "Run make test-agent-e2e for isolated agent fixtures",
  );
  const fixture = JSON.parse(
    readFileSync(process.env.AGENT_E2E_FIXTURE_FILE!, "utf8"),
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
    .fill("O comportamento mudou depois da configuração nova?");
  await workspace.getByRole("button", { name: "Consultar agente" }).click();
  await expect(workspace.getByRole("status")).toHaveText(
    /Iniciando|Consultando|Contexto|Resposta/,
    { timeout: 15000 },
  );
  const result = workspace.getByTestId("agent-result");
  await expect(result).toBeVisible({ timeout: 90000 });
  await expect(result).toContainText("ASSOCIATION");
  await expect(result).toContainText("não provam causalidade mecânica");
  await expect(result).toContainText(/-10(?:\.0+)? K/);
  await workspace.getByText("Expandir evidências", { exact: true }).click();
  await expect(result).toContainText("compare_configurations");
  await expect(result).toContainText(fixture.configurations[0]);
  await expect(result).toContainText(fixture.configurations[1]);
  await expect(result).toContainText(fixture.latest_session);
  await workspace.getByText("Contexto e modificações", { exact: true }).click();
  await expect(result).toContainText("controlled intercooler");
  await expect(result).toContainText(fixture.modification);
  await expect(result).toContainText("removed fixture part");
  await expect(result).toContainText("F30");
  await expect(result).toContainText("N55");
  await expect(workspace.locator("img")).toHaveCount(0);
  const accessibility = await new AxeBuilder({ page })
    .include(".agent-workspace")
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await workspace
    .getByLabel("Pergunta sobre o veículo")
    .fill("Essa peça causou a melhora?");
  await workspace.getByRole("button", { name: "Consultar agente" }).click();
  await expect(workspace.getByRole("status")).toHaveText("Resposta validada.", {
    timeout: 90000,
  });
  await expect(result).toContainText("INSUFFICIENT_EVIDENCE");
  await expect(result).toContainText("Confiança: low");
  await expect(result).toContainText("mechanical_cause");
  await expect(result).toContainText("não provam causalidade mecânica");
  await expect(result).not.toContainText("SUPPORTED_CONCLUSION");
});
