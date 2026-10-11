import type { components } from "../../../../packages/contracts/generated/api";

type Report = components["schemas"]["SupervisorReport"];
type Specialist = components["schemas"]["Specialist"];

export const specialistLabels: Record<Specialist, string> = {
  data_quality: "Qualidade dos dados",
  performance: "Desempenho",
  thermal: "Comportamento térmico",
  fuel_air_boost: "Combustível, ar e pressão de carga",
};

export function SpecialistResults({ report }: { report: Report }) {
  const specialists = report.specialists ?? [];
  const conflicts = report.conflicts ?? [];
  return (
    <section aria-label="Especialistas consultados">
      <h3>Especialistas consultados</h3>
      {specialists.length === 0 ? (
        <p>Consulta factual respondida sem especialistas.</p>
      ) : (
        <ul>
          {specialists.map((result) => (
            <li key={result.specialist}>
              <details>
                <summary>
                  {specialistLabels[result.specialist]} — {result.status}
                </summary>
                <ul>
                  {(result.findings ?? []).map((finding) => (
                    <li key={finding.finding_id}>
                      <strong>{finding.classification}</strong>:{" "}
                      {finding.statement}
                      <p>
                        Evidências:{" "}
                        {finding.evidence_ids.join(", ") || "insuficientes"}
                      </p>
                      {(finding.limitations ?? []).length > 0 && (
                        <p>Limitações: {finding.limitations?.join("; ")}</p>
                      )}
                    </li>
                  ))}
                </ul>
                {(result.data_quality_warnings ?? []).length > 0 && (
                  <p>
                    Limitações dos dados:{" "}
                    {result.data_quality_warnings?.join("; ")}
                  </p>
                )}
                {result.error_category && (
                  <p>Análise indisponível: {result.error_category}.</p>
                )}
                {(result.evidence_gaps ?? []).length > 0 && (
                  <p>
                    Lacunas de evidência: {result.evidence_gaps?.join("; ")}
                  </p>
                )}
                <p>
                  {result.tool_call_count ?? 0} consultas;{" "}
                  {(result.duration_seconds ?? 0).toFixed(3)} s.
                </p>
              </details>
            </li>
          ))}
        </ul>
      )}
      {conflicts.length > 0 && (
        <div role="note" aria-label="Interpretações concorrentes">
          <h4>Interpretações concorrentes</h4>
          <ul>
            {conflicts.map((conflict) => (
              <li key={conflict.conflict_id}>{conflict.explanation}</li>
            ))}
          </ul>
        </div>
      )}
      {report.investigation_recommended && (
        <p>
          Evidência insuficiente ou limitada. Use a investigação abaixo para
          revisar as lacunas e aprovar uma coleta quando disponível.
        </p>
      )}
      <details>
        <summary>Detalhes da coordenação</summary>
        <p>{report.routing.reason}</p>
        <p>
          Análise da evidência: {report.sufficiency}. Especialistas dispensados:{" "}
          {report.routing.skipped.map((s) => specialistLabels[s]).join(", ") ||
            "nenhum"}
          .
        </p>
        <p>
          Versão: {report.prompt_version}. Reutilizações: {report.cache_hits}.
        </p>
        <pre
          role="region"
          aria-label="Auditoria dos especialistas"
          tabIndex={0}
        >
          {JSON.stringify(
            {
              configuration_hash: report.configuration_hash,
              limits: report.limits,
              model_turn_count: report.model_turn_count,
              retry_count: report.retry_count,
              specialists: specialists.map((s) => ({
                specialist: s.specialist,
                version: s.prompt_version,
                trace_id: s.trace_id,
                budget: s.budget,
                usage: s.usage,
              })),
            },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
