import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { AnalyticsWorkspace } from "../src/components/analytics-workspace";

afterEach(() => vi.restoreAllMocks());

const pull = (id: string, configuration_id = "config-a") => ({
  id,
  configuration_id,
  min_rpm: 3000,
  max_rpm: 5000,
});
const configs = [
  { id: "config-a", description: "Stock" },
  { id: "config-b", description: "Recorded change" },
];

test("compares selected pulls and exposes evidence provenance", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "vehicle" }])))
    .mockResolvedValueOnce(new Response(JSON.stringify(configs)))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          pull("pull-a"),
          pull("pull-b"),
          pull("pull-c"),
          pull("pull-d"),
        ]),
      ),
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
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "repeated",
          status: "completed",
          result: {
            sufficiency: "sufficient",
            limitations: ["limited coverage"],
            sequence: [
              {
                index: 1,
                pull_id: "pull-a",
                start_iat: 300,
                median_boost: 100000,
                minimum_fuel_pressure: 19000000,
                median_speed: 20,
                event_count: 0,
              },
              {
                index: 2,
                pull_id: "pull-b",
                start_iat: null,
                median_boost: null,
                minimum_fuel_pressure: null,
                median_speed: null,
                event_count: 0,
              },
            ],
            repeatability: { median_boost: { median: 100000, mad: 0, iqr: 0 } },
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
  expect(
    await screen.findByText("RPM-normalized comparison"),
  ).toBeInTheDocument();
  expect(screen.getByText("3000–5000")).toBeInTheDocument();
  expect(screen.getByRole("img")).toHaveAccessibleName(/Boost pressure/);
  expect(
    screen.getByText(/Observed association is not root-cause/),
  ).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Analyze repeated pulls" }),
  );
  expect(
    await screen.findByText("Repeated-pull progression"),
  ).toBeInTheDocument();
  expect(screen.getByRole("table")).toHaveTextContent("100000");
});

test("shows insufficient history and sanitized request failure", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "vehicle" }])))
    .mockResolvedValueOnce(new Response(JSON.stringify(configs)))
    .mockResolvedValueOnce(
      new Response(JSON.stringify([pull("one"), pull("two")])),
    )
    .mockResolvedValueOnce(new Response("no", { status: 422 }));
  render(<AnalyticsWorkspace />);
  const choices = await screen.findAllByRole("checkbox");
  fireEvent.click(choices[0]);
  fireEvent.click(choices[0]);
  fireEvent.click(choices[0]);
  fireEvent.click(choices[1]);
  fireEvent.click(screen.getByRole("button", { name: "Compare pulls" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not be compared",
  );
});

test("shows a load failure and empty normalized curve without interpolation", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
    new Error("private detail"),
  );
  const { unmount } = render(<AnalyticsWorkspace />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Analytics data is unavailable",
  );
  unmount();
});

test("handles an empty vehicle collection", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(JSON.stringify([])),
  );
  render(<AnalyticsWorkspace />);
  expect(
    await screen.findByText(/Only one or no comparable pull/),
  ).toBeInTheDocument();
  expect(globalThis.fetch).toHaveBeenCalledTimes(1);
});

test("renders baseline, segmented trends and factual before-after evidence", async () => {
  const response = (result: object) =>
    new Response(
      JSON.stringify({
        id: "run",
        status: "completed",
        algorithm_version: "1.0.0",
        configuration_hash: "abcdef1234567890",
        source_fingerprint: "sources",
        generated_at: "2026-01-01T00:00:00Z",
        result,
      }),
    );
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "vehicle" }])))
    .mockResolvedValueOnce(new Response(JSON.stringify(configs)))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify([pull("a", "config-a"), pull("b", "config-b")]),
      ),
    )
    .mockResolvedValueOnce(
      response({
        sufficiency: "sufficient",
        session_count: 3,
        pull_count: 6,
        excluded_pull_count: 1,
        envelopes: {
          boost: [
            {
              rpm_start: 3000,
              rpm_end: 3250,
              p25: 99000,
              median: 100000,
              p75: 101000,
              unit: "Pa",
            },
          ],
        },
      }),
    )
    .mockResolvedValueOnce(
      response({
        sufficiency: "sufficient",
        point_count: 2,
        segments_by_configuration: {
          "config-a": [
            { observed_at: "2026-01-01T00:00:00Z", value: 100000, unit: "Pa" },
          ],
          "config-b": [
            { observed_at: "2026-02-01T00:00:00Z", value: 105000, unit: "Pa" },
          ],
        },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify([pull("a1"), pull("a2"), pull("a3")])),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          pull("b1", "config-b"),
          pull("b2", "config-b"),
          pull("b3", "config-b"),
          pull("b4", "config-b"),
        ]),
      ),
    )
    .mockResolvedValueOnce(
      response({
        sufficiency: "sufficient",
        language:
          "Observed before/after difference; association is not root-cause diagnosis.",
        sample_sizes: { before: 3, after: 4 },
        before: { sufficiency: "sufficient" },
        after: { sufficiency: "sufficient" },
      }),
    )
    .mockResolvedValueOnce(
      response({
        sufficiency: "insufficient",
        point_count: 0,
        limitations: ["insufficient_comparable_history"],
      }),
    )
    .mockResolvedValueOnce(
      response({
        sufficiency: "insufficient",
        session_count: 0,
        pull_count: 0,
        excluded_pull_count: 2,
        envelopes: {},
      }),
    );
  render(<AnalyticsWorkspace />);
  await screen.findByLabelText("Vehicle configuration");
  fireEvent.click(
    screen.getByRole("button", { name: "Build historical baseline" }),
  );
  expect(
    await screen.findByText("Observed historical baseline"),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/3 sessions · 6 contributing pulls/),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "View boost history" }));
  expect(
    await screen.findByText("Configuration-segmented history"),
  ).toBeInTheDocument();
  expect(screen.getByText("Configuration config-b")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Before configuration"), {
    target: { value: "config-a" },
  });
  fireEvent.change(screen.getByLabelText("After configuration"), {
    target: { value: "config-b" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Compare configurations" }),
  );
  expect(
    await screen.findByText("Observed before/after difference", {
      selector: "h3",
    }),
  ).toBeInTheDocument();
  expect(screen.getAllByText(/3 pulls/).length).toBeGreaterThan(0);
  const comparison = fetch.mock.calls.find(([url]) =>
    String(url).startsWith("/api/domain/analytics/configurations/compare?"),
  );
  expect(comparison).toBeDefined();
  expect(JSON.parse(String(comparison?.[1]?.body))).toEqual({
    pull_ids: ["a1", "a2", "a3"],
  });
  expect(
    new URL(String(comparison?.[0]), "http://localhost").searchParams.getAll(
      "after_pull_ids",
    ),
  ).toEqual(["b1", "b2", "b3", "b4"]);
  fireEvent.click(screen.getByRole("button", { name: "View boost history" }));
  expect(
    await screen.findByText("Insufficient comparable history for this trend."),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Vehicle configuration"), {
    target: { value: "config-b" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Build historical baseline" }),
  );
  expect(
    await screen.findByText(/0 sessions · 0 contributing pulls/),
  ).toBeInTheDocument();
});

test("requires two explicit distinct configurations before comparing", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "vehicle" }])))
    .mockResolvedValueOnce(new Response(JSON.stringify(configs)))
    .mockResolvedValueOnce(
      new Response(JSON.stringify([pull("a"), pull("b")])),
    );
  render(<AnalyticsWorkspace />);
  await screen.findAllByRole("checkbox");
  fireEvent.change(screen.getByLabelText("Before configuration"), {
    target: { value: "config-a" },
  });
  fireEvent.change(screen.getByLabelText("After configuration"), {
    target: { value: "config-a" },
  });
  expect(
    screen.getByRole("button", { name: "Compare configurations" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("After configuration"), {
    target: { value: "" },
  });
  expect(
    screen.getByRole("button", { name: "Compare configurations" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Before configuration"), {
    target: { value: "" },
  });
  expect(
    screen.getByRole("button", { name: "Compare configurations" }),
  ).toBeDisabled();
  expect(fetch).toHaveBeenCalledTimes(3);
});

test.each([
  { label: "Empty", options: [] },
  { label: "Single configuration", options: configs.slice(0, 1) },
])(
  "$label history cannot start a configuration comparison",
  async ({ options }) => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "vehicle" }])))
      .mockResolvedValueOnce(new Response(JSON.stringify(options)))
      .mockResolvedValueOnce(new Response(JSON.stringify([])));
    render(<AnalyticsWorkspace />);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    expect(
      screen.getByRole("button", { name: "Compare configurations" }),
    ).toBeDisabled();
  },
);
