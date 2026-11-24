import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("hostile agent answer and evidence render as inert text in Chromium", async ({
  page,
}) => {
  const vehicleId = "vehicle-hostile-rendering";
  const runId = "run-hostile-rendering";
  const payload =
    '<img src=x onerror=alert("agent-xss")> [click](javascript:alert("agent-xss"))';
  const vehicle = {
    id: vehicleId,
    manufacturer: "BMW",
    model: "335i",
    generation: "F30",
    model_year: 2015,
    engine_code: "N55",
    nickname: payload,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const run = {
    id: runId,
    status: "completed",
    user_question: "Render untrusted content safely",
    vehicle_id: vehicleId,
    started_at: "2026-01-01T00:00:00Z",
    model: "deterministic-test",
    provider: "test",
    agent_version: "test",
    prompt_version: "test",
    tool_call_count: 0,
    result: {
      schema_version: "1.0",
      answer: payload,
      confidence: "low",
      context: {
        vehicle_id: vehicleId,
        active_configuration_id: null,
        vehicle: { nickname: payload },
        configurations: [],
        modifications: [],
        sessions: [],
      },
      evidence: [
        {
          id: "evidence-hostile-rendering",
          evidence_type: "observation",
          run_id: runId,
          source_fingerprint: "f".repeat(64),
          source_tool: "get_session_summary",
          summary: payload,
          tool_call_id: "tool-call-hostile-rendering",
          facts: [{ path: "/hostile", value: payload, unit: null }],
        },
      ],
      findings: [
        {
          classification: "OBSERVATION",
          statement: payload,
          evidence_ids: [],
        },
      ],
      uncertainties: [payload],
      limitations: [],
      missing_evidence: [],
    },
  };
  await page.route("**/api/domain/**", (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname === "/api/domain/vehicles")
      return route.fulfill({ json: [vehicle] });
    if (requestUrl.pathname.endsWith(`/agent-runs/${runId}/audit`))
      return route.fulfill({
        json: { run_id: runId, evidence: [], tool_calls: [] },
      });
    if (requestUrl.pathname.endsWith(`/agent-runs/${runId}`))
      return route.fulfill({ json: run });
    if (
      requestUrl.pathname.endsWith("/agent-runs") &&
      requestUrl.searchParams.get("limit") === "5"
    )
      return route.fulfill({ json: [run] });
    return route.continue();
  });

  await page.goto(
    `/?vehicleId=${vehicleId}&agentRunId=${runId}#agent-workspace`,
  );
  const workspace = page.getByRole("region", {
    name: "Vehicle Intelligence Agent",
  });
  const result = workspace.getByTestId("agent-result");
  await expect(result).toBeVisible();
  await expect(result).toContainText(payload);
  await workspace.getByText("Expandir evidências", { exact: true }).click();
  await expect(result).toContainText("get_session_summary");
  await expect(workspace.locator("img, script, iframe, svg")).toHaveCount(0);
});

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
  await expect(
    workspace.getByRole("status").filter({ hasText: /^Resposta validada\.$/ }),
  ).toHaveText("Resposta validada.", { timeout: 90000 });
  await expect(result).toContainText("INSUFFICIENT_EVIDENCE");
  await expect(result).toContainText("Confiança: low");
  await expect(result).toContainText("mechanical_cause");
  await expect(result).toContainText("não provam causalidade mecânica");
  await expect(result).not.toContainText("SUPPORTED_CONCLUSION");
});
