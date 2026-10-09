"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";
import { InvestigationWorkspace } from "./investigation-workspace";

type AgentRun = components["schemas"]["AgentRun"];
type Audit = components["schemas"]["RunAudit"];
type AgentEvent = components["schemas"]["StreamEvent"];

export function AgentWorkspace({ vehicleId }: { vehicleId: string }) {
  const [question, setQuestion] = useState("");
  const [run, setRun] = useState<AgentRun | null>(null);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [history, setHistory] = useState<AgentRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Pronto para uma pergunta.");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string[]>([]);
  const [chunks, setChunks] = useState("");
  const stream = useRef<EventSource | null>(null);
  const cursor = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const base = `/api/domain/vehicles/${encodeURIComponent(vehicleId)}/agent-runs`;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      stream.current?.close();
      controller.current?.abort();
    };
  }, []);

  async function loadRun(id: string) {
    const responses = await Promise.all([
      fetch(`${base}/${id}`, { cache: "no-store" }),
      fetch(`${base}/${id}/audit`, { cache: "no-store" }),
      fetch(`${base}?limit=5`, { cache: "no-store" }),
    ]);
    if (responses.some((r) => !r.ok)) throw new Error("Run unavailable");
    const current = (await responses[0].json()) as AgentRun;
    const currentAudit = (await responses[1].json()) as Audit;
    const recent = (await responses[2].json()) as AgentRun[];
    if (!mounted.current) return current;
    setRun(current);
    setAudit(currentAudit);
    setHistory(recent);
    setBusy(current.status === "running");
    if (current.status === "failed" || current.status === "cancelled") {
      setError(
        `Execução ${current.status}: ${current.error_category ?? "indisponível"}.`,
      );
    }
    return current;
  }

  function observe(id: string) {
    stream.current?.close();
    const source = new EventSource(
      `${base}/${id}/stream?after=${cursor.current}`,
    );
    stream.current = source;
    const types: AgentEvent["type"][] = [
      "run_started",
      "context_resolved",
      "tool_started",
      "tool_completed",
      "evidence_added",
      "answer_chunk",
      "run_completed",
      "run_failed",
      "run_cancelled",
    ];
    for (const type of types) {
      source.addEventListener(type, (message: MessageEvent<string>) => {
        try {
          const event = JSON.parse(message.data) as AgentEvent;
          if (!mounted.current) return;
          if (
            event.schema_version !== "1.0" ||
            event.run_id !== id ||
            !Number.isInteger(event.sequence) ||
            event.sequence < 1 ||
            event.sequence > 400 ||
            event.sequence <= cursor.current
          )
            return;
          cursor.current = event.sequence;
          const data = event.data ?? {};
          if (
            event.type === "tool_started" &&
            typeof data.tool_name === "string"
          ) {
            const name = data.tool_name;
            setProgress((items) => [...items.slice(-31), name]);
            setStatus(`Consultando ${name}…`);
          }
          if (event.type === "context_resolved")
            setStatus("Contexto do veículo resolvido.");
          if (event.type === "answer_chunk" && typeof data.text === "string") {
            const text = data.text;
            setChunks((value) => (value + text).slice(0, 48000));
          }
          if (
            event.type === "run_completed" ||
            event.type === "run_failed" ||
            event.type === "run_cancelled"
          ) {
            source.close();
            setStatus(
              event.type === "run_completed"
                ? "Resposta validada."
                : "Execução encerrada.",
            );
            void loadRun(id).catch(() => {
              setError("Não foi possível recuperar a execução.");
              setBusy(false);
            });
          }
        } catch {
          source.close();
          setError("Evento inesperado. Recupere a execução para continuar.");
          setBusy(false);
        }
      });
    }
    source.onerror = () => {
      source.close();
      setError("Conexão interrompida. A execução pode ser recuperada.");
      setBusy(false);
    };
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setAudit(null);
    setProgress([]);
    setChunks("");
    cursor.current = 0;
    setStatus("Iniciando consulta…");
    controller.current?.abort();
    controller.current = new AbortController();
    try {
      const response = await fetch(base, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          question,
          previous_run_id: run?.status === "completed" ? run.id : null,
        }),
        signal: controller.current.signal,
      });
      if (!response.ok) throw new Error("Agent unavailable");
      const current = (await response.json()) as AgentRun;
      if (!mounted.current) return;
      setRun(current);
      observe(current.id);
    } catch {
      if (!mounted.current) return;
      setBusy(false);
      setError(
        "O agente está indisponível. Confira a configuração e tente novamente.",
      );
    }
  }

  const result = run?.result;
  return (
    <section
      className="telemetry-card agent-workspace"
      aria-labelledby="agent-heading"
    >
      <h2 id="agent-heading">Vehicle Intelligence Agent</h2>
      <p>
        Consulta por evidências do veículo selecionado. Associação temporal não
        prova causa mecânica.
      </p>
      <form onSubmit={(event) => void submit(event)}>
        <label htmlFor="agent-question">Pergunta sobre o veículo</label>
        <textarea
          id="agent-question"
          value={question}
          maxLength={2000}
          required
          rows={3}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={busy}
        />
        <button type="submit" disabled={busy || !question.trim()}>
          Consultar agente
        </button>
      </form>
      <p role="status" aria-live="polite">
        {status}
      </p>
      {error && <p role="alert">{error}</p>}
      {run && (
        <div>
          <button
            type="button"
            onClick={() => {
              setError(null);
              void loadRun(run.id)
                .then((current) => {
                  if (current.status === "running") {
                    setBusy(true);
                    observe(current.id);
                  }
                })
                .catch(() => setError("Execução indisponível."));
            }}
          >
            Recuperar execução
          </button>
          {run.status === "running" && (
            <button
              type="button"
              onClick={() => {
                void fetch(`${base}/${run.id}/cancel`, { method: "POST" })
                  .then((response) => {
                    if (!response.ok)
                      throw new Error("Cancellation unavailable");
                    return loadRun(run.id);
                  })
                  .catch(() => setError("Não foi possível cancelar."));
              }}
            >
              Cancelar consulta
            </button>
          )}
        </div>
      )}
      {progress.length > 0 && (
        <details open>
          <summary>Progresso das consultas</summary>
          <ol>
            {progress.map((name, i) => (
              <li key={`${i}-${name}`}>{name}</li>
            ))}
          </ol>
        </details>
      )}
      {chunks && !result && (
        <p aria-label="Resposta em transmissão">{chunks}</p>
      )}
      {result && (
        <div data-testid="agent-result">
          <p>
            Confiança: <strong>{result.confidence}</strong>
          </p>
          <p style={{ whiteSpace: "pre-wrap" }}>{result.answer}</p>
          <h3>Achados</h3>
          <ul>
            {result.findings.map((finding, index) => (
              <li key={index}>
                <strong>{finding.classification}</strong>: {finding.statement}
                <span>
                  {" "}
                  Evidências:{" "}
                  {finding.evidence_ids.join(", ") || "insuficientes"}
                </span>
              </li>
            ))}
          </ul>
          <details>
            <summary>Contexto e modificações</summary>
            <p>Veículo: {result.context.vehicle_id}</p>
            <p>
              Configuração ativa:{" "}
              {result.context.active_configuration_id ?? "não estabelecida"}
            </p>
            <pre role="region" aria-label="Contexto registrado" tabIndex={0}>
              {JSON.stringify(
                {
                  vehicle: result.context.vehicle,
                  configurations: result.context.configurations,
                  modifications: result.context.modifications,
                  sessions: result.context.sessions,
                },
                null,
                2,
              )}
            </pre>
          </details>
          <details>
            <summary>Expandir evidências</summary>
            {result.evidence.map((evidence) => (
              <article key={evidence.id}>
                <h3>{evidence.source_tool}</h3>
                <p>Referência: {evidence.id}</p>
                <p>
                  Sessão: {evidence.session_id ?? "—"}; pull:{" "}
                  {evidence.pull_id ?? "—"}; evento: {evidence.event_id ?? "—"};
                  configuração: {evidence.configuration_id ?? "—"}
                </p>
                <pre
                  role="region"
                  aria-label={`Fatos observados: ${evidence.id}`}
                  tabIndex={0}
                >
                  {JSON.stringify(evidence.facts, null, 2)}
                </pre>
              </article>
            ))}
          </details>
          <details>
            <summary>Linha do tempo de ferramentas</summary>
            <ol>
              {audit?.tool_calls.map((call) => (
                <li key={call.id}>
                  {call.tool_name}: {call.status} (
                  {call.duration_seconds?.toFixed(3) ?? "—"} s)
                </li>
              ))}
            </ol>
          </details>
          <h3>Incertezas e limitações</h3>
          <ul>
            {[
              ...result.uncertainties,
              ...result.limitations,
              ...result.missing_evidence,
            ].map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
          <InvestigationWorkspace
            vehicleId={vehicleId}
            run={run}
            onFollowUp={(id) => {
              stream.current?.close();
              void loadRun(id).catch(() =>
                setError("Acompanhamento indisponível."),
              );
            }}
          />
        </div>
      )}
      {history.length > 0 && (
        <details>
          <summary>Consultas recentes</summary>
          <ul>
            {history.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    stream.current?.close();
                    void loadRun(item.id).catch(() =>
                      setError("Histórico indisponível."),
                    );
                  }}
                >
                  {item.user_question} — {item.status}
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
