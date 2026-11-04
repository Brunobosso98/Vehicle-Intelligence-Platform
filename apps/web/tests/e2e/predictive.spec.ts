import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const screenshotRoot = resolve(
  process.cwd(),
  process.env.PHASE9H_SCREENSHOT_DIR ?? "../../.validation/phase9h/screenshots",
);

async function save(page: Page, name: string, fullPage = true) {
  await mkdir(screenshotRoot, { recursive: true });
  if (fullPage) await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: resolve(screenshotRoot, name), fullPage });
}

async function saveBrowserMetrics(
  page: Page,
  name: string,
  details: Record<string, unknown>,
) {
  const browser = await page.evaluate(() => {
    const resources = performance.getEntriesByType(
      "resource",
    ) as PerformanceResourceTiming[];
    const sameOrigin = resources.filter(
      (entry) => new URL(entry.name).origin === location.origin,
    );
    const fixture = sameOrigin.find(
      (entry) => new URL(entry.name).pathname === "/api/predictive/demo",
    );
    const charts = Array.from(
      document.querySelectorAll(".predictive-chart svg"),
    );
    return {
      viewport: { width: innerWidth, height: innerHeight },
      documentWidth: document.documentElement.scrollWidth,
      horizontalOverflowPx: Math.max(
        0,
        document.documentElement.scrollWidth - innerWidth,
      ),
      resourceCount: sameOrigin.length,
      encodedTransferBytes: sameOrigin.reduce(
        (total, entry) => total + entry.transferSize,
        0,
      ),
      decodedResourceBytes: sameOrigin.reduce(
        (total, entry) => total + entry.decodedBodySize,
        0,
      ),
      clientScriptCount: sameOrigin.filter((entry) =>
        /\.m?js(?:\?|$)/.test(new URL(entry.name).pathname),
      ).length,
      clientBundleEncodedBytes: sameOrigin
        .filter((entry) => /\.m?js(?:\?|$)/.test(new URL(entry.name).pathname))
        .reduce((total, entry) => total + entry.transferSize, 0),
      clientBundleDecodedBytes: sameOrigin
        .filter((entry) => /\.m?js(?:\?|$)/.test(new URL(entry.name).pathname))
        .reduce((total, entry) => total + entry.decodedBodySize, 0),
      domNodeCount: document.querySelectorAll("*").length,
      fixtureEncodedBytes: fixture?.encodedBodySize ?? null,
      fixtureDecodedBytes: fixture?.decodedBodySize ?? null,
      chartCount: charts.length,
      charts: charts.map((chart) => ({
        accessibleName: chart.querySelector("title")?.textContent ?? "",
        axisTickCount: chart.querySelectorAll(".chart-axis").length,
        pointCount: chart.querySelectorAll(".chart-point").length,
        thresholdCount: chart.querySelectorAll(".chart-threshold").length,
      })),
    };
  });
  const artifactRoot = resolve(
    process.env.PHASE9H_ARTIFACT_DIR ?? "../../.validation/phase9h/playwright",
  );
  await mkdir(artifactRoot, { recursive: true });
  await writeFile(
    resolve(artifactRoot, name),
    `${JSON.stringify({ ...details, browser }, null, 2)}\n`,
  );
}

test.describe("Phase 9H explicit synthetic UI", () => {
  test("operator gate and synthetic overview, results, evidence and science", async ({
    page,
  }) => {
    const navigationStartedAt = Date.now();
    let operatorGateReadyMs = 0;
    let demoInteractiveMs = 0;
    const browserErrors: string[] = [];
    page.on("pageerror", (error) => browserErrors.push(error.message));
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/predictive", { waitUntil: "networkidle" });
    await expect(
      page.getByRole("heading", { name: "Predictive intelligence" }),
    ).toBeVisible();
    operatorGateReadyMs = Date.now() - navigationStartedAt;
    await expect(
      page.getByRole("button", { name: "Abrir demonstração sintética" }),
    ).toBeVisible();
    await save(page, "operator-gate-desktop.png");

    const demoStartedAt = Date.now();
    await page
      .getByRole("button", { name: "Abrir demonstração sintética" })
      .click();
    await expect(
      page.getByText("DADOS SIMULADOS PARA DEMONSTRAÇÃO"),
    ).toBeVisible();
    demoInteractiveMs = Date.now() - demoStartedAt;
    await expect(page.getByText("Requests de serving")).toBeVisible();
    await expect(
      page.locator(".overview-ledger > div").nth(2).locator("strong"),
    ).toHaveText("0");
    await expect(
      page.getByRole("table", { name: /Fixture sintética de demonstração/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("img", { name: /synthetic demonstration/i }).first(),
    ).toBeVisible();
    await save(page, "synthetic-overview-desktop.png");
    await save(page, "synthetic-history-desktop.png");

    const rows = page.locator(".receipt-table tbody tr");
    await rows.nth(1).locator(".table-select").click();
    await expect(page.getByText("1.72").first()).toBeVisible();
    await expect(page.getByText("AFTER_PULL_OFFLINE").first()).toBeVisible();
    await page.locator(".demo-record").scrollIntoViewIfNeeded();
    await save(page, "synthetic-anomaly-desktop.png", false);
    await rows.nth(2).locator(".table-select").click();
    await expect(page.getByText("Sem sinal suficiente").last()).toBeVisible();
    await expect(page.locator(".demo-record dd").first()).toHaveText("—");
    await page.locator(".demo-record").scrollIntoViewIfNeeded();
    await save(page, "synthetic-abstained-desktop.png", false);
    await rows.nth(0).locator(".table-select").click();
    await expect(page.getByText("PARTIAL")).toBeVisible();
    await page.locator(".demo-record").scrollIntoViewIfNeeded();
    await save(page, "synthetic-partial-evidence-desktop.png", false);

    await page.getByRole("button", { name: "Carregar resumo" }).click();
    await expect(
      page.getByText(/Real-world calibration: NOT_ESTABLISHED/i),
    ).toBeVisible();
    await save(page, "synthetic-research-desktop.png");

    await page.setViewportSize({ width: 768, height: 1024 });
    await page.reload({ waitUntil: "networkidle" });
    await page
      .getByRole("button", { name: "Abrir demonstração sintética" })
      .click();
    await expect(
      page.getByText("DADOS SIMULADOS PARA DEMONSTRAÇÃO"),
    ).toBeVisible();
    await save(page, "synthetic-tablet.png");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload({ waitUntil: "networkidle" });
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).toHaveAttribute("href", "#main");
    await page
      .getByRole("button", { name: "Abrir demonstração sintética" })
      .click();
    await expect(
      page.getByText("DADOS SIMULADOS PARA DEMONSTRAÇÃO"),
    ).toBeVisible();
    await expect
      .poll(async () =>
        page.evaluate(
          () => document.documentElement.scrollWidth - window.innerWidth,
        ),
      )
      .toBeLessThanOrEqual(0);
    await save(page, "synthetic-mobile.png");

    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(accessibility.violations).toEqual([]);
    expect(browserErrors).toEqual([]);
    const responsiveOverflow: Array<{ width: number; overflowPx: number }> = [];
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      responsiveOverflow.push({
        width,
        overflowPx: await page.evaluate(() =>
          Math.max(0, document.documentElement.scrollWidth - innerWidth),
        ),
      });
    }
    expect(
      responsiveOverflow.every((measurement) => measurement.overflowPx === 0),
    ).toBe(true);
    await saveBrowserMetrics(page, "synthetic-ui-metrics.json", {
      mode: "synthetic-demo",
      operatorGateReadyMs,
      demoInteractiveMs,
      responsiveOverflow,
      axeViolationCount: accessibility.violations.length,
      browserConsoleErrors: browserErrors,
      screenshots: [
        "operator-gate-desktop.png",
        "synthetic-overview-desktop.png",
        "synthetic-history-desktop.png",
        "synthetic-anomaly-desktop.png",
        "synthetic-abstained-desktop.png",
        "synthetic-partial-evidence-desktop.png",
        "synthetic-research-desktop.png",
        "synthetic-tablet.png",
        "synthetic-mobile.png",
      ],
    });
  });

  test("authorized live BFF values match immutable 9D/9E database receipts", async ({
    page,
  }) => {
    const oraclePath = process.env.PHASE9H_ORACLE;
    expect(oraclePath, "independent database oracle is required").toBeTruthy();
    const oracle = JSON.parse(await readFile(oraclePath!, "utf8")) as {
      vehicle_id: string;
      supervised_tasks: string[];
      anomaly_families: string[];
      records: Array<{
        receipt_id: string;
        result_type: string;
        task: string | null;
        family: string | null;
        horizon: string;
        status: string;
        source_role: string;
        requested_cutoff: string;
        effective_cutoff: string | null;
        score: number | null;
        threshold: number | null;
        decision: boolean | null;
        model_version_id: string | null;
        detector_version_id: string | null;
        evidence_id: string | null;
        evidence_completeness: string | null;
        evidence_integrity: string | null;
        quality: unknown;
        session_id: string;
        pull_id: string;
        recorded_at: string;
      }>;
    };
    const baseURL = process.env.WEB_BASE_URL ?? "http://127.0.0.1:3000";
    const apiSecret = process.env.PREDICTION_OPERATOR_TOKEN ?? "";
    const browserRequests: Array<{
      url: string;
      body: string;
      authorization: string | undefined;
    }> = [];
    const browserErrors: string[] = [];
    page.on("pageerror", (error) => browserErrors.push(error.message));
    page.on("request", (request) =>
      browserRequests.push({
        url: request.url(),
        body: request.postData() ?? "",
        authorization: request.headers()["authorization"],
      }),
    );

    const unauthenticated = await page.request.get(
      `${baseURL}/api/predictive/vehicles`,
    );
    expect(unauthenticated.status()).toBe(401);
    expect(JSON.stringify(await unauthenticated.json())).not.toContain(
      oracle.vehicle_id,
    );

    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(
      `/predictive?vehicleId=${encodeURIComponent(oracle.vehicle_id)}`,
      { waitUntil: "networkidle" },
    );
    await expect(
      page.getByRole("heading", { name: "Predictive intelligence" }),
    ).toBeVisible();
    await save(page, "persisted-operator-gate.png");
    await page
      .getByLabel("Credencial local do operador")
      .fill("intentionally-invalid-operator-credential");
    await page.getByRole("button", { name: "Entrar no workspace" }).click();
    await expect(page.getByRole("alert")).toContainText(
      /credential|unauthorized|inválid/i,
    );
    await save(page, "persisted-login-denied.png");
    await page
      .getByLabel("Credencial local do operador")
      .fill(process.env.PREDICTIVE_UI_OPERATOR_SECRET ?? "");
    await page.getByRole("button", { name: "Entrar no workspace" }).click();
    await expect(
      page.getByRole("heading", { name: "Visão geral" }),
    ).toBeVisible();
    await expect(
      page.getByRole("table", { name: /Histórico persistido/i }),
    ).toBeVisible();
    const historyResponse = (await page.evaluate(async (vehicleId) => {
      const response = await fetch(
        `/api/predictive/vehicles/${encodeURIComponent(vehicleId)}/receipts?limit=20&offset=0`,
        { cache: "no-store" },
      );
      return { status: response.status, value: await response.json() };
    }, oracle.vehicle_id)) as {
      status: number;
      value: {
        items: Array<{
          prediction: Record<string, unknown>;
          evidence_available: boolean;
          evidence_completeness: string | null;
          evidence_integrity: string | null;
          session_id: string;
          pull_id: string;
          recorded_at: string;
        }>;
      };
    };
    expect(historyResponse.status).toBe(200);
    const sourceItems = new Map(
      historyResponse.value.items.map((item) => [
        String(item.prediction.receipt_id),
        item,
      ]),
    );
    const sourceEvidence = new Map<string, Record<string, unknown>>();
    for (const expected of oracle.records) {
      const item = sourceItems.get(expected.receipt_id);
      expect(
        item,
        `receipt ${expected.receipt_id} must be in the authorized history`,
      ).toBeTruthy();
      const prediction = item!.prediction;
      expect(prediction.result_type).toBe(expected.result_type);
      expect(prediction.task).toBe(expected.task);
      expect(prediction.family).toBe(expected.family);
      expect(prediction.horizon).toBe(expected.horizon);
      expect(prediction.status).toBe(expected.status);
      expect(prediction.source_role).toBe(expected.source_role);
      expect(prediction.requested_cutoff).toBe(expected.requested_cutoff);
      expect(prediction.effective_cutoff).toBe(expected.effective_cutoff);
      expect(
        prediction.engineering_validation_score ?? prediction.anomaly_score,
      ).toBe(expected.score);
      expect(prediction.threshold).toBe(expected.threshold);
      expect(prediction.decision).toBe(expected.decision);
      expect(prediction.model_version_id).toBe(expected.model_version_id);
      expect(prediction.detector_version_id).toBe(expected.detector_version_id);
      expect(prediction.quality).toEqual(expected.quality);
      expect(item!.session_id).toBe(expected.session_id);
      expect(item!.pull_id).toBe(expected.pull_id);
      expect(item!.recorded_at).toBe(expected.recorded_at);
      expect(item!.evidence_available).toBe(expected.evidence_id !== null);
      expect(item!.evidence_completeness).toBe(expected.evidence_completeness);
      expect(item!.evidence_integrity).toBe(expected.evidence_integrity);
      if (expected.evidence_id) {
        const evidenceResponse = (await page.evaluate(
          async ({ vehicleId, receiptId }) => {
            const response = await fetch(
              `/api/predictive/vehicles/${encodeURIComponent(vehicleId)}/receipts/${encodeURIComponent(receiptId)}/evidence`,
              { cache: "no-store" },
            );
            return { status: response.status, value: await response.json() };
          },
          { vehicleId: oracle.vehicle_id, receiptId: expected.receipt_id },
        )) as { status: number; value: Record<string, unknown> };
        expect(evidenceResponse.status).toBe(200);
        expect(evidenceResponse.value.evidence_id).toBe(expected.evidence_id);
        expect(evidenceResponse.value.receipt_id).toBe(expected.receipt_id);
        expect(evidenceResponse.value.result_type).toBe(expected.result_type);
        expect(evidenceResponse.value.task).toBe(expected.task);
        expect(evidenceResponse.value.family).toBe(expected.family);
        expect(evidenceResponse.value.horizon).toBe(expected.horizon);
        expect(evidenceResponse.value.source_role).toBe(expected.source_role);
        expect(evidenceResponse.value.score).toBe(expected.score);
        expect(evidenceResponse.value.threshold).toBe(expected.threshold);
        expect(evidenceResponse.value.completeness).toBe(
          expected.evidence_completeness,
        );
        expect(evidenceResponse.value.integrity).toBe(
          expected.evidence_integrity,
        );
        sourceEvidence.set(expected.receipt_id, evidenceResponse.value);
      }
    }
    expect(
      oracle.records
        .filter((item) => item.result_type === "next_pull")
        .map((item) => item.task)
        .filter(Boolean).length,
    ).toBe(3);
    expect(
      oracle.records
        .filter((item) => item.result_type === "anomaly")
        .map((item) => item.family)
        .filter(Boolean).length,
    ).toBe(4);
    await save(page, "persisted-overview-desktop.png");
    await expect(page.getByText("NOT_ESTABLISHED").first()).toBeVisible();

    const foreignVehicle = "00000000-0000-4000-8000-000000000001";
    const foreign = await page.request.get(
      `${baseURL}/api/predictive/vehicles/${foreignVehicle}/receipts`,
    );
    expect(foreign.status()).toBe(404);
    const guessed = await page.request.get(
      `${baseURL}/api/predictive/vehicles/${oracle.vehicle_id}/receipts/00000000-0000-4000-8000-000000000002`,
    );
    expect(guessed.status()).toBe(404);
    const proxyBypass = await page.request.get(
      `${baseURL}/api/domain/prediction-service/vehicles/${oracle.vehicle_id}/runs`,
      { headers: { authorization: `Bearer ${apiSecret}` } },
    );
    expect(proxyBypass.status()).toBe(404);
    expect(JSON.stringify(await proxyBypass.json())).not.toContain(
      oracle.vehicle_id,
    );
    const badCsrf = await page.request.post(
      `${baseURL}/api/predictive/auth/logout`,
      { headers: { origin: baseURL, "x-csrf-token": "wrong" } },
    );
    expect(badCsrf.status()).toBe(403);

    const firstScored = oracle.records.find(
      (item) => item.status === "READY_SCORE" && item.score !== null,
    );
    expect(firstScored).toBeTruthy();
    const rowFor = (receiptId: string) =>
      historyResponse.value.items.findIndex(
        (item) => item.prediction.receipt_id === receiptId,
      );
    await page
      .locator(".receipt-table tbody tr")
      .nth(rowFor(firstScored!.receipt_id))
      .locator(".table-select")
      .click();
    await expect(
      page.getByText(String(firstScored!.score), { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page
        .getByText(`threshold ${firstScored!.threshold}`, { exact: false })
        .first(),
    ).toBeVisible();
    await page.locator("#evidence").scrollIntoViewIfNeeded();
    await save(page, "persisted-scored-receipt.png", false);

    const partial = oracle.records.find(
      (item) => item.evidence_completeness === "PARTIAL",
    );
    if (partial) {
      await page
        .locator(".receipt-table tbody tr")
        .nth(rowFor(partial.receipt_id))
        .locator(".table-select")
        .click();
      await expect(page.getByText("PARTIAL").first()).toBeVisible();
      await page.locator("#evidence").scrollIntoViewIfNeeded();
      await save(page, "persisted-partial-evidence.png", false);
    }
    const abstained = oracle.records.find((item) =>
      item.status.startsWith("ABSTAINED"),
    );
    if (abstained) {
      await page
        .locator(".receipt-table tbody tr")
        .nth(rowFor(abstained.receipt_id))
        .locator(".table-select")
        .click();
      await expect(page.getByText("No score was produced.")).toBeVisible();
      await page.locator("#evidence").scrollIntoViewIfNeeded();
      await save(page, "persisted-abstained.png", false);
    }

    await page
      .getByRole("button", { name: "Carregar resumo científico" })
      .click();
    await expect(
      page.getByText(/Real-world calibration: NOT_ESTABLISHED/i),
    ).toBeVisible();
    await save(page, "persisted-research-desktop.png");

    const mismatch = oracle.records.find((item) =>
      sourceEvidence.has(item.receipt_id),
    );
    expect(mismatch).toBeTruthy();
    const selectedIndex = await page
      .locator(".receipt-table tbody tr.is-selected")
      .evaluate((row) =>
        Array.from(row.parentElement?.children ?? []).indexOf(row),
      );
    if (
      historyResponse.value.items[selectedIndex]?.prediction.receipt_id ===
      mismatch!.receipt_id
    ) {
      const alternate = oracle.records.find(
        (item) => item.receipt_id !== mismatch!.receipt_id,
      );
      expect(alternate).toBeTruthy();
      await page
        .locator(".receipt-table tbody tr")
        .nth(rowFor(alternate!.receipt_id))
        .locator(".table-select")
        .click();
    }
    await page.route(
      `**/api/predictive/vehicles/${oracle.vehicle_id}/receipts/${mismatch!.receipt_id}/evidence`,
      async (route) => {
        const source = sourceEvidence.get(mismatch!.receipt_id)!;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...source,
            receipt_id: "00000000-0000-4000-8000-000000000099",
          }),
        });
      },
    );
    await page
      .locator(".receipt-table tbody tr")
      .nth(rowFor(mismatch!.receipt_id))
      .locator(".table-select")
      .click();
    await expect(
      page.getByText(
        "Projeção não confere com o escopo da receipt. Detalhes foram ocultados.",
      ),
    ).toBeVisible();
    await page.locator("#evidence").scrollIntoViewIfNeeded();
    await save(page, "persisted-proof-mismatch.png", false);

    await page.setViewportSize({ width: 390, height: 844 });
    await expect
      .poll(async () =>
        page.evaluate(
          () => document.documentElement.scrollWidth - window.innerWidth,
        ),
      )
      .toBeLessThanOrEqual(0);
    await save(page, "persisted-mobile.png");
    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(accessibility.violations).toEqual([]);
    const serverSecrets = [
      apiSecret,
      process.env.PREDICTIVE_UI_SESSION_SECRET ?? "",
    ].filter(Boolean);
    const browserSurfaces = [
      page.url(),
      await page.content(),
      ...browserRequests.flatMap((request) => [
        request.url,
        request.body,
        request.authorization ?? "",
      ]),
      ...(await page.evaluate(async () => {
        const scripts = Array.from(document.scripts)
          .map((script) => script.src)
          .filter((src) => src && new URL(src).origin === location.origin);
        const scriptBodies = await Promise.all(
          scripts.map(async (src) => {
            const response = await fetch(src, { cache: "no-store" });
            return response.ok ? response.text() : "";
          }),
        );
        return [
          ...scriptBodies,
          document.cookie,
          JSON.stringify(Object.entries(localStorage)),
          JSON.stringify(Object.entries(sessionStorage)),
        ];
      })),
    ];
    const serverSecretDisclosureCount = serverSecrets.filter((secret) =>
      browserSurfaces.some((surface) => surface.includes(secret)),
    ).length;
    expect(serverSecretDisclosureCount).toBe(0);
    expect(
      browserRequests.every(
        (request) => !apiSecret || !request.body.includes(apiSecret),
      ),
    ).toBe(true);
    expect(
      browserRequests.every(
        (request) => !request.authorization?.includes(apiSecret),
      ),
    ).toBe(true);
    expect(
      browserRequests.every(
        (request) =>
          !request.url.startsWith(
            process.env.API_BASE_URL ?? "http://api:8000",
          ),
      ),
    ).toBe(true);
    await saveBrowserMetrics(page, "persisted-ui-metrics.json", {
      mode: "protected-persisted-read-only",
      sourceRecordCount: oracle.records.length,
      supervisedTaskCount: oracle.supervised_tasks?.length ?? 3,
      anomalyFamilyCount: oracle.anomaly_families?.length ?? 4,
      browserRequestCount: browserRequests.length,
      internalApiHostRequests: browserRequests.filter((request) =>
        request.url.startsWith(process.env.API_BASE_URL ?? "http://api:8000"),
      ).length,
      bearerDisclosureCount: browserRequests.filter(
        (request) =>
          request.authorization?.includes(apiSecret) ||
          request.body.includes(apiSecret),
      ).length,
      serverSecretDisclosureCount,
      responsiveOverflow: [
        {
          width: 390,
          overflowPx: await page.evaluate(() =>
            Math.max(0, document.documentElement.scrollWidth - innerWidth),
          ),
        },
      ],
      axeViolationCount: accessibility.violations.length,
      browserConsoleErrors: browserErrors,
      screenshots: [
        "persisted-operator-gate.png",
        "persisted-login-denied.png",
        "persisted-overview-desktop.png",
        "persisted-scored-receipt.png",
        "persisted-partial-evidence.png",
        "persisted-abstained.png",
        "persisted-proof-mismatch.png",
        "persisted-research-desktop.png",
        "persisted-mobile.png",
      ],
    });
    await page.getByRole("button", { name: "Encerrar sessão" }).click();
    await expect(page.getByLabel("Credencial local do operador")).toBeVisible();
    await page.goBack();
    await expect(page.getByLabel("Credencial local do operador")).toBeVisible();
  });
});
