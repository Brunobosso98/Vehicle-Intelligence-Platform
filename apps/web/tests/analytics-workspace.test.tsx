import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { AnalyticsWorkspace } from "../src/components/analytics-workspace";

afterEach(() => vi.restoreAllMocks());

const pull = (id: string) => ({ id, min_rpm: 3000, max_rpm: 5000 });

test("compares selected pulls and exposes evidence provenance", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "vehicle" }])))
    .mockResolvedValueOnce(
      new Response(JSON.stringify([pull("pull-a"), pull("pull-b"), pull("pull-c"), pull("pull-d")])),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "run-id",
          status: "completed",
          result: {
            sufficiency: "sufficient",
            common_rpm_range: [3000, 5000],
            profiles: [
              { curves: { boost: [{ rpm_start: 3000, median: 100000 }] } },
              { curves: { boost: [{ rpm_start: 3000, median: 101000 }] } },
            ],
          },
          algorithm_version: "1.0.0",
          configuration_hash: "1234567890abcdef",
          source_fingerprint: "fingerprint",
          generated_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );
  render(<AnalyticsWorkspace />);
  const choices = await screen.findAllByRole("checkbox");
  fireEvent.click(choices[0]);
  fireEvent.click(choices[1]);
  fireEvent.click(choices[2]);
  expect(choices[3]).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Compare pulls" }));
  expect(await screen.findByText("RPM-normalized comparison")).toBeInTheDocument();
  expect(screen.getByText("3000–5000")).toBeInTheDocument();
  expect(screen.getByRole("img")).toHaveAccessibleName(/Boost pressure/);
  expect(screen.getByText(/Observed association is not root-cause/)).toBeInTheDocument();
});

test("shows insufficient history and sanitized request failure", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "vehicle" }])))
    .mockResolvedValueOnce(new Response(JSON.stringify([pull("one"), pull("two")])))
    .mockResolvedValueOnce(new Response("no", { status: 422 }));
  render(<AnalyticsWorkspace />);
  const choices = await screen.findAllByRole("checkbox");
  fireEvent.click(choices[0]);
  fireEvent.click(choices[0]);
  fireEvent.click(choices[0]);
  fireEvent.click(choices[1]);
  fireEvent.click(screen.getByRole("button", { name: "Compare pulls" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("could not be compared");
});

test("shows a load failure and empty normalized curve without interpolation", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("private detail"));
  const { unmount } = render(<AnalyticsWorkspace />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Analytics data is unavailable");
  unmount();
});

test("handles an empty vehicle collection", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify([])));
  render(<AnalyticsWorkspace />);
  expect(await screen.findByText(/Only one or no comparable pull/)).toBeInTheDocument();
  expect(globalThis.fetch).toHaveBeenCalledTimes(1);
});
