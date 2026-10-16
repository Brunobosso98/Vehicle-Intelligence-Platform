import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("knowledge catalog, documentary citations, hybrid evidence and unknown map gap", async ({
  page,
}) => {
  test.setTimeout(240_000);
  test.skip(
    !process.env.KNOWLEDGE_E2E_FIXTURE_FILE,
    "Run make test-knowledge-e2e for isolated fixtures",
  );
  const fixtureFile = process.env.KNOWLEDGE_E2E_FIXTURE_FILE!;
  const fixture = JSON.parse(readFileSync(fixtureFile, "utf8"));
  const artifacts = dirname(fixtureFile);
  await page.setViewportSize({ width: 1366, height: 900 });
  await page.goto("/");
  await page
    .getByLabel("Vehicle", { exact: true })
    .selectOption(fixture.vehicle);
  const knowledge = page.getByRole("region", {
    name: "Technical Knowledge",
    exact: true,
  });
  await expect(knowledge).toContainText("7 fontes · 7 documentos · 7 trechos");
  await expect(knowledge).toContainText(fixture.knowledge_index);
  await knowledge
    .getByText("Knowledge Sources e documentos", { exact: true })
    .click();
  await expect(knowledge).toContainText("TIER 1 AUTHORITATIVE");
  await expect(knowledge).toContainText("UNVERIFIED");
  await knowledge
    .getByLabel("Consultar referência técnica")
    .fill("N55 HPFP fuel rail pressure");
  await knowledge.getByRole("button", { name: "Consultar corpus" }).click();
  const citations = knowledge.getByRole("region", {
    name: "Corpus Knowledge Evidence",
    exact: true,
  });
  await expect(citations).toBeVisible({ timeout: 30_000 });
  await citations
    .locator("summary")
    .filter({ hasText: "Synthetic fixture n55" })
    .click();
  await expect(citations).toContainText("Synthetic acceptance fixture");
  await expect(citations).toContainText("Synthetic fuel reference");
  await expect(citations).toContainText("stock reference not tune target");
  await expect(
    citations.getByRole("link", { name: "Consultar publicação original" }),
  ).toHaveAttribute("href", /example\.com\/vip-synthetic\/n55/);
  await knowledge.scrollIntoViewIfNeeded();
  await knowledge.screenshot({
    path: join(artifacts, "knowledge-panel-desktop.png"),
  });
  await page.screenshot({
    path: join(artifacts, "knowledge-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await knowledge.scrollIntoViewIfNeeded();
  await expect(knowledge).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await knowledge.screenshot({
    path: join(artifacts, "knowledge-panel-mobile.png"),
  });
  await page.screenshot({
    path: join(artifacts, "knowledge-mobile.png"),
    fullPage: true,
  });
  const accessibility = await new AxeBuilder({ page })
    .include(".knowledge-workspace")
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.setViewportSize({ width: 1366, height: 900 });
  const workspace = page.getByRole("region", {
    name: "Vehicle Intelligence Agent",
    exact: true,
  });
  const question = workspace.getByLabel("Pergunta sobre o veículo");
  const submit = workspace.getByRole("button", {
    name: "Consultar agente",
    exact: true,
  });
  const result = workspace.getByTestId("agent-result");
  const agentKnowledge = workspace.getByRole("region", {
    name: "Knowledge Evidence",
    exact: true,
  });
  await question.fill(
    "How does the N55 high pressure fuel system regulate pressure?",
  );
  await submit.click();
  await expect(
    workspace.getByRole("region", { name: "Knowledge Evidence", exact: true }),
  ).toBeVisible({ timeout: 90_000 });
  await expect(result).toContainText("Referência documental");
  await expect(result).toContainText("Vehicle Evidence");
  await question.fill(
    "Is the observed HPFP behavior expected for this vehicle?",
  );
  await submit.click();
  await expect(result).toContainText("Stage 2 não define", { timeout: 90_000 });
  await result.getByText("Expandir evidências", { exact: true }).click();
  await expect(result).toContainText("get_session_summary");
  await expect(
    workspace.getByRole("region", { name: "Knowledge Evidence", exact: true }),
  ).toBeVisible();
  await expect(agentKnowledge).toContainText(
    "exact tuner map target unavailable",
  );
  await expect(result).not.toContainText("SUPPORTED_CONCLUSION");
  await question.fill(
    "Is this boost behavior normal for my Stage 2 configuration?",
  );
  await submit.click();
  await expect(agentKnowledge).toContainText("Synthetic fixture boost", {
    timeout: 90_000,
  });
  await expect(result).toContainText("Stage 2 não define", { timeout: 90_000 });
  await expect(agentKnowledge).toContainText(
    "exact tuner map target unavailable",
  );
  await expect(result).not.toContainText("write_ecu");
  await expect(workspace.locator("script, img")).toHaveCount(0);
  const agentAccessibility = await new AxeBuilder({ page })
    .include(".agent-workspace")
    .analyze();
  expect(agentAccessibility.violations).toEqual([]);
});
