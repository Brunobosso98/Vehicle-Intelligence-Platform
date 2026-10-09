"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type AgentRun = components["schemas"]["AgentRun"];
type Investigation = components["schemas"]["InvestigationPlan"];

const terminal = new Set([
  "COMPLETED",
  "INCONCLUSIVE",
  "REJECTED",
  "CANCELLED",
  "FAILED",
]);

export function InvestigationWorkspace({
  vehicleId,
  run,
  onFollowUp,
}: {
  vehicleId: string;
  run: AgentRun;
  onFollowUp: (runId: string) => void;
}) {
  const [token, setToken] = useState("");
  const [adapter, setAdapter] = useState<"obd" | "replay" | "synthetic">("obd");
  const [sourceId, setSourceId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [plan, setPlan] = useState<Investigation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const base = `/api/domain/vehicles/${encodeURIComponent(vehicleId)}/investigations`;
  const eligible =
    run.status === "completed" &&
    run.result?.findings.some(
      (finding) => finding.classification === "INSUFFICIENT_EVIDENCE",
    ) &&
    run.result?.missing_evidence.some((item) =>
      [
        "signal_or_measurement",
        "comparable_history",
        "technical_documentation",
        "data_quality",
        "configuration_context",
      ].includes(item),
    );

  const request = useCallback(
    async (
      path: string,
      method = "GET",
      body?: object,
    ): Promise<Investigation> => {
      const response = await fetch(`${base}${path}`, {
        method,
        cache: "no-store",
        headers: {
          "X-Investigation-Token": token,
          ...(body ? { "content-type": "application/json" } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!response.ok) {
        if (response.status === 401)
          throw new Error("Credencial de operador inválida.");
        if (response.status === 409)
          throw new Error("O plano mudou. Recarregue antes de continuar.");
        throw new Error(
          "Investigação indisponível. Confira o serviço e tente novamente.",
        );
      }
      return (await response.json()) as Investigation;
    },
    [base, token],
  );

  async function action(path: string, body?: object) {
    setBusy(true);
    setError(null);
    try {
      const current = await request(path, body ? "POST" : "GET", body);
      setPlan(current);
      setNotice(`Plano ${current.status.toLowerCase().replaceAll("_", " ")}.`);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Investigação indisponível.",
      );
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!plan || !token || terminal.has(plan.status)) return;
    const id = window.setInterval(() => {
      void request(`/${encodeURIComponent(plan.id)}`)
        .then((current) => setPlan(current))
        .catch(() => setError("Atualização interrompida. Recupere o plano."));
    }, 4000);
    return () => window.clearInterval(id);
  }, [plan, request, token]);

  if (!eligible && !plan) return null;

  const canApprove =
    plan?.status === "AWAITING_APPROVAL" &&
    (plan.recipe?.feasibility === "FEASIBLE" ||
      plan.recipe?.feasibility === "FEASIBLE_WITH_DEGRADATION");
  const approved = plan?.approval?.status === "APPROVED";

  return (
    <section
      className="investigation-workspace"
      aria-labelledby="investigation-heading"
    >
      <h3 id="investigation-heading">Investigar evidências insuficientes</h3>
      <p>
        Hipóteses são candidatas para comparação. A aprovação prepara uma
        receita de leitura e nunca inicia o veículo ou o coletor.
      </p>
      <label htmlFor="investigation-token">Credencial do operador</label>
      <input
        id="investigation-token"
        type="password"
        autoComplete="off"
        value={token}
        onChange={(event) => setToken(event.target.value)}
      />
      {!plan && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void action("", {
              agent_run_id: run.id,
              adapter,
              source_id: sourceId.trim(),
            });
          }}
        >
          <label htmlFor="investigation-adapter">Fonte de leitura</label>
          <select
            id="investigation-adapter"
            value={adapter}
            onChange={(event) =>
              setAdapter(event.target.value as typeof adapter)
            }
          >
            <option value="obd">OBD somente leitura</option>
            <option value="replay">Arquivo de replay</option>
            <option value="synthetic">Simulação local</option>
          </select>
          <label htmlFor="investigation-source">Identificação da fonte</label>
          <input
            id="investigation-source"
            value={sourceId}
            maxLength={80}
            onChange={(event) => setSourceId(event.target.value)}
            required
          />
          <button type="submit" disabled={busy || !token || !sourceId.trim()}>
            Criar investigação
          </button>
        </form>
      )}
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}</p>}
      {plan && (
        <div>
          <p>
            <strong>Estado:</strong> {plan.status} · <strong>Versão:</strong>{" "}
            {plan.version}
          </p>
          <p>
            <strong>Objetivo:</strong> {plan.goal}
          </p>
          <p>
            <strong>Por que faltam evidências:</strong> {plan.findings_summary}
          </p>
          <button
            type="button"
            disabled={busy || !token}
            onClick={() => void action(`/${plan.id}`)}
          >
            Recuperar plano
          </button>
          {[
            "CAPABILITIES_RESOLVED",
            "AWAITING_APPROVAL",
            "APPROVED",
            "ACQUISITION_READY",
          ].includes(plan.status) && (
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void action(`/${plan.id}/refresh`, { version: plan.version })
              }
            >
              Atualizar capacidades
            </button>
          )}
          <h4>Hipóteses candidatas</h4>
          <ul>
            {(plan.hypotheses ?? []).map((item) => (
              <li key={item.id}>
                <strong>{item.statement}</strong> — {item.status}.{" "}
                {item.discriminating_goal}
                <div>
                  Evidências a favor:{" "}
                  {item.evidence_for?.join(", ") || "nenhuma"}
                </div>
                <div>
                  Evidências contra:{" "}
                  {item.evidence_against?.join(", ") || "nenhuma"}
                </div>
              </li>
            ))}
          </ul>
          <h4>Lacunas de evidência</h4>
          <ul>
            {(plan.gaps ?? []).map((gap) => (
              <li key={gap.id}>
                {gap.description} — {gap.status}. {gap.why_it_matters}
              </li>
            ))}
          </ul>
          <h4>Sinais necessários e disponibilidade</h4>
          <ul>
            {(plan.signal_needs ?? []).map((need) => (
              <li key={need.id}>
                {need.role}: {need.canonical_signal ?? "sem canal coletável"} —{" "}
                {need.availability}
                {need.required ? " (necessário)" : " (opcional)"}
                {need.unavailable_reason ? `; ${need.unavailable_reason}` : ""}
              </li>
            ))}
          </ul>
          {plan.recipe && (
            <div>
              <h4>Receita proposta</h4>
              <p>
                {plan.recipe.key} · versão {plan.recipe.version} ·{" "}
                {plan.recipe.feasibility}
              </p>
              <p>
                Hash de configuração:{" "}
                <code>{plan.recipe.configuration_hash}</code>
              </p>
              <p>
                Escopo: captura local somente leitura, iniciada pelo operador;
                configuração {plan.recipe.vehicle_scope}; duração mínima{" "}
                {plan.recipe.minimum_duration_seconds} s; modos{" "}
                {plan.recipe.supported_modes.join(", ")}.
              </p>
              <p>
                Ausentes: {plan.recipe.required_missing?.join(", ") || "nenhum"}
              </p>
              <p>
                Taxas reduzidas:{" "}
                {plan.recipe.rate_compromises?.join(", ") || "nenhuma"}
              </p>
            </div>
          )}
          {plan.approval?.status === "INVALIDATED" && (
            <p role="alert">
              A aprovação anterior perdeu validade após a revisão da receita ou
              fonte.
            </p>
          )}
          {canApprove && plan.recipe && (
            <div>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  void action(`/${plan.id}/approve`, {
                    version: plan.version,
                    recipe_hash: plan.recipe?.configuration_hash,
                  })
                }
              >
                Aprovar esta versão e receita
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  void action(`/${plan.id}/reject`, { version: plan.version })
                }
              >
                Rejeitar
              </button>
            </div>
          )}
          {approved && (
            <p>
              Recipe ready for acquisition. Inicie o coletor local
              explicitamente.
            </p>
          )}
          {(plan.status === "ACQUISITION_READY" ||
            plan.status === "AWAITING_DATA") && (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void action(`/${plan.id}/sessions`, {
                  version: plan.version,
                  session_id: sessionId.trim(),
                });
              }}
            >
              <label htmlFor="investigation-session">
                ID da sessão finalizada
              </label>
              <input
                id="investigation-session"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                required
              />
              <button type="submit" disabled={busy || !sessionId.trim()}>
                Vincular sessão
              </button>
            </form>
          )}
          {plan.linked_session_ids?.length ? (
            <p>Sessão vinculada: {plan.linked_session_ids.join(", ")}</p>
          ) : null}
          {plan.status === "DATA_RECEIVED" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void action(`/${plan.id}/reanalyze`, {})}
            >
              Reanalisar dados recebidos
            </button>
          )}
          {plan.reanalysis_run_id && (
            <button
              type="button"
              onClick={() => onFollowUp(plan.reanalysis_run_id!)}
            >
              Abrir resposta de acompanhamento
            </button>
          )}
          {plan.outcome && (
            <div>
              <h4>Resultado da investigação</h4>
              <p>{plan.outcome.conclusion}</p>
              <p>
                Classificação: {plan.outcome.classification}; confiança:{" "}
                {plan.outcome.confidence}
              </p>
              <p>
                Lacunas resolvidas: {plan.outcome.resolved_gap_ids?.length ?? 0}
                ; pendentes: {plan.outcome.unresolved_gap_ids?.length ?? 0}
              </p>
              <ul>
                {(plan.outcome.limitations ?? []).map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {!terminal.has(plan.status) && (
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void action(`/${plan.id}/cancel`, { version: plan.version })
              }
            >
              Cancelar investigação
            </button>
          )}
        </div>
      )}
    </section>
  );
}
