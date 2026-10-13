import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { components } from "../../../packages/contracts/generated/api";
import { SpecialistResults } from "../src/components/specialist-results";

type Report = components["schemas"]["SupervisorReport"];

function report(): Report {
  return {
    schema_version: "1.0",
    prompt_version: "supervisor-v1",
    cache_hits: 0,
    routing_seconds: 0,
    model_turn_count: 0,
    retry_count: 0,
    sufficiency: "INSUFFICIENT",
    investigation_recommended: false,
    routing: {
      intent: "factual",
      considered: [],
      selected: [],
      skipped: [],
      data_quality_gate: false,
      hints: [],
      reason: "Factual query",
    },
  };
}

describe("Specialist findings", () => {
  it.each(["1.0", "1.1"] as const)(
    "keeps the zero specialist path readable for report version %s",
    (version) => {
      const value = report();
      value.schema_version = version;
      if (version === "1.1") value.prompt_version = "supervisor-v3";
      render(<SpecialistResults report={value} />);
      expect(
        screen.getByText("Consulta factual respondida sem especialistas."),
      ).toBeInTheDocument();
    },
  );

  it("renders findings as text and exposes warnings, conflicts and investigation", () => {
    const value = report();
    value.investigation_recommended = true;
    value.specialists = [
      {
        schema_version: "1.0",
        specialist: "thermal",
        supervisor_run_id: "run",
        vehicle_id: "vehicle",
        status: "completed",
        prompt_version: "thermal-v1",
        confidence: "low",
        model_turn_count: 1,
        tool_call_count: 0,
        telemetry_call_count: 0,
        cache_hits: 0,
        duration_seconds: 0,
        blocks_interpretation: false,
        data_quality_warnings: ["missing_temperature"],
        findings: [
          {
            finding_id: "finding",
            specialist: "thermal",
            classification: "OBSERVATION",
            strength: "low",
            template: "recorded_fact",
            statement: '<img src=x onerror="alert(1)">',
            bindings: [],
            evidence_ids: ["evidence"],
          },
        ],
      },
    ];
    value.conflicts = [
      {
        conflict_id: "conflict",
        finding_ids: ["first", "second"],
        type: "competing_hypotheses",
        severity: "warning",
        explanation: "Causa não isolada",
        requires_investigation: true,
        resolvable_with_existing_evidence: false,
      },
    ];
    const { container } = render(<SpecialistResults report={value} />);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x onerror=/)).toBeInTheDocument();
    expect(screen.getByText(/missing_temperature/)).toBeInTheDocument();
    expect(screen.getByText(/Evidências: evidence/)).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent("Causa não isolada");
    expect(screen.getByText(/Use a investigação abaixo/)).toBeInTheDocument();
  });

  it("shows isolated failures without fabricating findings", () => {
    const value = report();
    value.specialists = [
      {
        schema_version: "1.0",
        specialist: "performance",
        supervisor_run_id: "run",
        vehicle_id: "vehicle",
        status: "failed",
        prompt_version: "performance-v1",
        confidence: "low",
        model_turn_count: 0,
        tool_call_count: 0,
        telemetry_call_count: 0,
        cache_hits: 0,
        duration_seconds: 0,
        blocks_interpretation: false,
        error_category: "specialist_timeout",
      },
    ];
    render(<SpecialistResults report={value} />);
    expect(
      screen.getByText(/Análise indisponível: specialist_timeout/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Desempenho — failed/).tagName).toBe("SUMMARY");
  });
});
