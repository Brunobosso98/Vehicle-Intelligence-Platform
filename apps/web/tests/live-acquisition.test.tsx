import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { LiveAcquisition } from "../src/components/live-acquisition";

afterEach(() => vi.restoreAllMocks());

test("shows recipe requirements and structured readiness", async () => {
  const recipe = {
    key: "performance-pull",
    name: "Performance Pull",
    description: "Factual acquisition",
    objective: "performance_pull",
    version: 1,
    configuration_hash: "a".repeat(64),
    vehicle_scope: "generic-obd-ii",
    minimum_duration_seconds: 15,
    supported_modes: ["synthetic"],
    notes: [],
    requirements: [
      {
        signal: "engine.rpm",
        importance: "required",
        reason: "anchors operating state",
        minimum_hz: 5,
        preferred_hz: 10,
        priority: "critical_for_recipe",
        missing_effect: ["pull_detection"],
      },
    ],
  };
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify([recipe]), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          readiness: "ready",
          required_available: ["engine.rpm"],
          required_missing: [],
          recommended_available: [],
          optional_available: [],
          sampling_plan: [
            {
              signal: "engine.rpm",
              priority: "critical_for_recipe",
              target_hz: 10,
              estimated_hz: 10,
            },
          ],
          expected_capabilities: ["temporal_segmentation"],
          unavailable_capabilities: [],
          warnings: [],
        }),
        { status: 200 },
      ),
    );
  render(<LiveAcquisition />);
  expect(await screen.findByText("engine.rpm")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /preflight/i }));
  await waitFor(() => expect(screen.getByText("READY")).toBeInTheDocument());
  expect(screen.getByText(/lawful closed course/i)).toBeInTheDocument();
});
