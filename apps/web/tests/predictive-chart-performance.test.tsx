import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { cleanup, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import demoFixture from "../src/lib/predictive/demo-fixture.json";
import {
  ScoreChart,
  type HistoryItem,
} from "../src/components/predictive-workspace";

const chartItems: HistoryItem[] = Array.from({ length: 500 }, (_, index) => {
  const source = demoFixture.items[0] as HistoryItem;
  const suffix = index.toString(16).padStart(12, "0");
  return {
    ...source,
    recorded_at: new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString(),
    prediction: {
      ...source.prediction,
      receipt_id: `00000000-0000-4000-8000-${suffix}`,
      engineering_validation_score: index / 1000,
      threshold: 0.25,
    },
  };
});

function percentile(values: number[], fraction: number): number {
  return (
    [...values].sort((left, right) => left - right)[
      Math.ceil(values.length * fraction) - 1
    ] ?? 0
  );
}

describe("Phase 9H chart rendering benchmark", () => {
  it("renders a bounded 500-point score chart and records repeatable render measurements", async () => {
    const renderTimesMs: number[] = [];
    let renderedNodeCount = 0;
    let chartPointCount = 0;
    const heapBeforeBytes = process.memoryUsage().heapUsed;
    for (let sample = 0; sample < 5; sample += 1) {
      const startedAt = performance.now();
      const view = render(
        <ScoreChart
          items={chartItems}
          heading="500-point controlled synthetic chart benchmark"
        />,
      );
      renderTimesMs.push(performance.now() - startedAt);
      renderedNodeCount = view.container.querySelectorAll("*").length;
      chartPointCount = view.container.querySelectorAll(".chart-point").length;
      expect(chartPointCount).toBe(500);
      expect(view.container.querySelectorAll(".chart-threshold")).toHaveLength(
        500,
      );
      expect(view.container.querySelectorAll(".chart-axis")).toHaveLength(3);
      view.unmount();
      cleanup();
    }
    const report = {
      mode: "synthetic-component-render",
      fixtureRecords: chartItems.length,
      chartPointCount,
      renderedNodeCount,
      sampleCount: renderTimesMs.length,
      renderTimesMs,
      p50RenderMs: percentile(renderTimesMs, 0.5),
      p95RenderMs: percentile(renderTimesMs, 0.95),
      approximateHeapDeltaBytes:
        process.memoryUsage().heapUsed - heapBeforeBytes,
      budgetMs: 5000,
      runtime: process.version,
      environment: "vitest-jsdom-local-render-approximation",
      productionSlaClaim: false,
    };
    expect(report.p95RenderMs).toBeLessThan(report.budgetMs);
    const root = resolve(
      process.env.PHASE9H_ARTIFACT_DIR ??
        "../../.validation/phase9h/playwright",
    );
    await mkdir(root, { recursive: true });
    await writeFile(
      resolve(root, "chart-500-render.json"),
      `${JSON.stringify(report, null, 2)}\n`,
    );
  }, 15_000);
});
