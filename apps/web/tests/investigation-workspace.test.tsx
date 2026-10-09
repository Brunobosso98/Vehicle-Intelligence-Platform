import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { components } from "../../../packages/contracts/generated/api";
import { InvestigationWorkspace } from "../src/components/investigation-workspace";

type AgentRun = components["schemas"]["AgentRun"];
type Investigation = components["schemas"]["InvestigationPlan"];

const run = {
  id: "run-1",
  status: "completed",
  result: {
    findings: [{ classification: "INSUFFICIENT_EVIDENCE" }],
    missing_evidence: ["signal_or_measurement"],
  },
} as AgentRun;

const plan = {
  id: "plan-1",
  agent_run_id: "run-1",
  vehicle_id: "vehicle-1",
  cycle_count: 0,
  prompt_version: "investigation-v1",
  question: "Why did it slow down?",
  schema_version: "1.0",
  source_id: "local-source",
  status: "AWAITING_APPROVAL",
  version: 4,
  goal: "Compare measured behavior",
  findings_summary: "Timing was not measured",
  hypotheses: [
    {
      id: "hyp-1",
      category: "THERMAL",
      created_by: "agent",
      statement: "Thermal conditions may be associated",
      status: "CANDIDATE",
      support_level: "unknown",
      discriminating_goal: "Compare temperatures",
      evidence_for: ["e-1"],
      evidence_against: [],
    },
  ],
  gaps: [
    {
      id: "gap-1",
      category: "signal_or_measurement",
      required: true,
      description: "Missing measurement",
      status: "NEEDS_NEW_CAPTURE",
      why_it_matters: "Discriminates explanations",
    },
  ],
  signal_needs: [
    {
      id: "need-1",
      gap_ids: ["gap-1"],
      provenance: "phase4_recipe_catalog",
      resolution: "MEDIUM",
      role: "timing_behavior",
      canonical_signal: "engine.ignition_timing",
      availability: "UNAVAILABLE",
      required: false,
      source_support: "UNAVAILABLE",
      unavailable_reason: "No Phase 4 mapping",
    },
  ],
  recipe: {
    key: "performance-pull",
    version: 1,
    configuration_hash: "a".repeat(64),
    feasibility: "FEASIBLE_WITH_DEGRADATION",
    minimum_duration_seconds: 30,
    vehicle_scope: "generic-obd-ii",
    supported_modes: ["synthetic", "obd"],
    sampling_algorithm_version: "v1",
    source: "synthetic-live-v1",
    required_missing: [],
    rate_compromises: ["engine.rpm"],
  },
  approval: { status: "PENDING" },
  linked_session_ids: [],
} as Investigation;

const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status });

afterEach(() => vi.restoreAllMocks());

function open() {
  render(
    <InvestigationWorkspace
      vehicleId="vehicle-1"
      run={run}
      onFollowUp={vi.fn()}
    />,
  );
  fireEvent.change(screen.getByLabelText("Credencial do operador"), {
    target: { value: "operator-secret" },
  });
  fireEvent.change(screen.getByLabelText("Identificação da fonte"), {
    target: { value: "local-source" },
  });
}

test("offers investigation only for material insufficient evidence", () => {
  const ordinary = {
    ...run,
    result: { ...run.result!, missing_evidence: ["mechanical_cause"] },
  } as AgentRun;
  render(
    <InvestigationWorkspace
      vehicleId="vehicle-1"
      run={ordinary}
      onFollowUp={vi.fn()}
    />,
  );
  expect(screen.queryByText("Investigar evidências insuficientes")).toBeNull();
});

test("reviews exact recipe, approves explicitly, links and retains the follow-up", async () => {
  const followUp = vi.fn();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith("/approve"))
        return json({
          ...plan,
          status: "ACQUISITION_READY",
          version: 6,
          approval: { status: "APPROVED" },
        });
      if (path.endsWith("/sessions"))
        return json({
          ...plan,
          status: "INCONCLUSIVE",
          version: 8,
          reanalysis_run_id: "run-2",
          linked_session_ids: ["session-1"],
          approval: { status: "APPROVED" },
          outcome: {
            conclusion: "Still inconclusive",
            classification: "INCONCLUSIVE",
            confidence: "low",
            limitations: ["Timing absent"],
            resolved_gap_ids: [],
            unresolved_gap_ids: ["gap-1"],
          },
        });
      if (init?.method === "POST") return json(plan, 201);
      return json(plan);
    });
  render(
    <InvestigationWorkspace
      vehicleId="vehicle-1"
      run={run}
      onFollowUp={followUp}
    />,
  );
  fireEvent.change(screen.getByLabelText("Credencial do operador"), {
    target: { value: "operator-secret" },
  });
  fireEvent.change(screen.getByLabelText("Identificação da fonte"), {
    target: { value: "local-source" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Criar investigação" }));
  expect(await screen.findByText("Hash de configuração:")).toBeInTheDocument();
  expect(screen.getByText(/timing_behavior/)).toHaveTextContent("UNAVAILABLE");
  expect(screen.getByText(/duração mínima/)).toHaveTextContent("30 s");
  expect(
    screen.getByText(/Thermal conditions may be associated/).closest("li"),
  ).toHaveTextContent("CANDIDATE");
  fireEvent.click(
    screen.getByRole("button", { name: "Aprovar esta versão e receita" }),
  );
  expect(
    await screen.findByText(/Recipe ready for acquisition/),
  ).toBeInTheDocument();
  const approval = fetch.mock.calls.find(([path]) =>
    String(path).endsWith("/approve"),
  );
  expect(JSON.parse(String(approval?.[1]?.body))).toEqual({
    version: 4,
    recipe_hash: "a".repeat(64),
  });
  expect(approval?.[1]?.headers).toMatchObject({
    "X-Investigation-Token": "operator-secret",
  });
  fireEvent.change(screen.getByLabelText("ID da sessão finalizada"), {
    target: { value: "session-1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Vincular sessão" }));
  expect(await screen.findByText("Still inconclusive")).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Abrir resposta de acompanhamento" }),
  );
  expect(followUp).toHaveBeenCalledWith("run-2");
});

test("handles operator rejection, stale plans and cancellation", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith("/approve")) return json({}, 409);
      if (path.endsWith("/reject"))
        return json({ ...plan, status: "REJECTED", version: 5 });
      if (path.endsWith("/cancel"))
        return json({ ...plan, status: "CANCELLED", version: 6 });
      if (init?.method === "POST") return json(plan, 201);
      return json(plan);
    });
  open();
  fireEvent.click(screen.getByRole("button", { name: "Criar investigação" }));
  await screen.findByText("Hash de configuração:");
  fireEvent.click(
    screen.getByRole("button", { name: "Aprovar esta versão e receita" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("O plano mudou");
  fireEvent.click(screen.getByRole("button", { name: "Rejeitar" }));
  await waitFor(() => expect(screen.getByText(/REJECTED/)).toBeInTheDocument());
  expect(
    fetch.mock.calls.some(([path]) => String(path).endsWith("/reject")),
  ).toBe(true);
});

test("requires a valid operator token and shows unavailable source refresh", async () => {
  const unknown = {
    ...plan,
    status: "CAPABILITIES_RESOLVED",
    recipe: null,
    signal_needs: [],
    hypotheses: [],
    gaps: [],
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("/refresh")) return json(plan);
    if (init?.method === "POST") return json({}, 401);
    return json(unknown);
  });
  open();
  fireEvent.click(screen.getByRole("button", { name: "Criar investigação" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Credencial de operador inválida",
  );
});
