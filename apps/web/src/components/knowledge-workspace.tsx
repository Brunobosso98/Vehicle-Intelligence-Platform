"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import type { components } from "../../../../packages/contracts/generated/api";

type Catalog = components["schemas"]["KnowledgeCatalog"];
type Retrieval = components["schemas"]["RetrievalResult"];
type Topic = components["schemas"]["RetrievalIntent"]["topic"];

export function KnowledgeCitations({
  result,
  label = "Knowledge Evidence",
}: {
  result: Retrieval;
  label?: string;
}) {
  const evidence = result.evidence ?? [];
  const gaps = result.knowledge_gaps ?? [];
  return (
    <section aria-label={label}>
      <h3>Knowledge Evidence</h3>
      <p>Referências documentais, separadas das medições do veículo.</p>
      {!!result.source_conflicts?.length && (
        <aside aria-label="Conflitos documentais">
          <p>Referências com conflito em aberto:</p>
          <ul>
            {result.source_conflicts.map((conflict) => (
              <li key={conflict.id}>{conflict.explanation}</li>
            ))}
          </ul>
        </aside>
      )}
      {gaps.length > 0 && (
        <div role="status">
          <p>Referência técnica insuficiente para uma conclusão normativa.</p>
          <ul>
            {gaps.map((gap) => (
              <li key={gap}>{gap.replaceAll("_", " ")}</li>
            ))}
          </ul>
        </div>
      )}
      {!evidence.length && (
        <p>Nenhuma fonte suficientemente aplicável foi encontrada.</p>
      )}
      <ul>
        {evidence.map((item) => (
          <li key={item.id}>
            <details>
              <summary>
                {item.document.title} — {item.source.publisher}
              </summary>
              <p>
                {item.source.trust.replaceAll("_", " ")} ·{" "}
                {item.applicability.status}
              </p>
              <p>
                Seção: {item.section}
                {item.page
                  ? ` · Página ${item.page}`
                  : " · Documento web sem paginação"}
              </p>
              <blockquote>{item.snippet}</blockquote>
              {item.applicability.reasons.length > 0 && (
                <ul aria-label="Applicability warnings">
                  {item.applicability.reasons.map((reason) => (
                    <li key={reason}>{reason.replaceAll("_", " ")}</li>
                  ))}
                </ul>
              )}
              {(item.conflict_ids ?? []).length > 0 && (
                <p role="status">
                  Fonte com conflito aberto. Não estabelece alvo normativo.
                </p>
              )}
              <p>
                <a
                  href={item.source.canonical_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Consultar publicação original
                </a>
              </p>
              <p>
                Versão: {item.document.version_label ?? "não informada"} ·
                Recuperada em{" "}
                {new Date(item.document.retrieved_at).toLocaleDateString(
                  "pt-BR",
                )}
              </p>
              <details>
                <summary>Inspecionar recuperação e citação</summary>
                <dl>
                  <dt>Índice</dt>
                  <dd>{item.index_id}</dd>
                  <dt>Relevância lexical</dt>
                  <dd>{item.lexical_score.toFixed(4)}</dd>
                  <dt>Similaridade vetorial</dt>
                  <dd>{item.vector_score?.toFixed(4) ?? "indisponível"}</dd>
                  <dt>Aplicabilidade</dt>
                  <dd>{item.applicability.score.toFixed(2)}</dd>
                  <dt>Documento</dt>
                  <dd>{item.document.checksum}</dd>
                  <dt>Trecho</dt>
                  <dd>{item.chunk_checksum}</dd>
                </dl>
              </details>
            </details>
          </li>
        ))}
      </ul>
      {!result.vector_available && (
        <p>
          Busca vetorial indisponível nesta consulta; resultados lexicais podem
          estar disponíveis.
        </p>
      )}
    </section>
  );
}

export function KnowledgeWorkspace({ vehicleId }: { vehicleId: string }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogError, setCatalogError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState<Topic>("fuel");
  const [result, setResult] = useState<Retrieval | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const request = new AbortController();
    void fetch("/api/domain/knowledge", {
      signal: request.signal,
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Knowledge unavailable");
        setCatalog((await response.json()) as Catalog);
        setCatalogError(false);
      })
      .catch(() => !request.signal.aborted && setCatalogError(true));
    return () => request.abort();
  }, [attempt]);
  useEffect(() => () => controller.current?.abort(), []);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setBusy(true);
    setError(false);
    setResult(null);
    try {
      const response = await fetch(
        `/api/domain/vehicles/${vehicleId}/knowledge/query`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            intent: { query, topic, need: "principle", top_k: 5 },
          }),
          signal: current.signal,
        },
      );
      if (!response.ok) throw new Error("Retrieval unavailable");
      const value = (await response.json()) as Retrieval;
      if (!current.signal.aborted) setResult(value);
    } catch {
      if (!current.signal.aborted) setError(true);
    } finally {
      if (!current.signal.aborted) setBusy(false);
    }
  }

  return (
    <section
      className="telemetry-card agent-workspace knowledge-workspace"
      aria-labelledby="knowledge-heading"
    >
      <h2 id="knowledge-heading">Technical Knowledge</h2>
      <p>
        Fontes técnicas, estado de verificação e aplicabilidade à configuração
        do veículo.
      </p>
      {catalogError ? (
        <div role="alert">
          <p>Não foi possível carregar as fontes técnicas.</p>
          <button
            type="button"
            onClick={() => setAttempt((value) => value + 1)}
          >
            Recarregar fontes
          </button>
        </div>
      ) : !catalog ? (
        <p role="status">Carregando fontes técnicas…</p>
      ) : (
        <>
          <p>
            {catalog.sources.length} fontes · {catalog.documents.length}{" "}
            documentos · {catalog.chunks} trechos · {catalog.embeddings}{" "}
            embeddings
          </p>
          <p>
            Índice ativo:{" "}
            {catalog.indexes.find((item) => item.active)?.snapshot.id ??
              "nenhum — ingestão necessária"}
          </p>
          <details>
            <summary>Knowledge Sources e documentos</summary>
            {!catalog.sources.length && (
              <p>
                Nenhuma fonte cadastrada. Referências indisponíveis serão
                apresentadas como lacunas.
              </p>
            )}
            <ul>
              {catalog.sources.map((source) => (
                <li key={source.id}>
                  <a
                    href={source.canonical_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {source.publisher}
                  </a>{" "}
                  · {source.trust.replaceAll("_", " ")} · {source.status}
                  <ul>
                    {catalog.documents
                      .filter((document) => document.source_id === source.id)
                      .map((document) => (
                        <li key={document.id}>
                          {document.title} · {document.status} ·{" "}
                          {document.applicability.engine ??
                            "princípios genéricos"}{" "}
                          · {document.applicability.calibration}
                          <p>{document.license_note}</p>
                        </li>
                      ))}
                  </ul>
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
      <form onSubmit={(event) => void search(event)}>
        <label htmlFor="knowledge-query">Consultar referência técnica</label>
        <textarea
          id="knowledge-query"
          value={query}
          maxLength={1000}
          minLength={3}
          required
          rows={2}
          disabled={busy}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label htmlFor="knowledge-topic">Sistema</label>
        <select
          id="knowledge-topic"
          value={topic}
          disabled={busy}
          onChange={(event) => setTopic(event.target.value as Topic)}
        >
          <option value="fuel">Combustível / HPFP</option>
          <option value="boost">Ar / boost</option>
          <option value="thermal">Temperatura / arrefecimento</option>
          <option value="calibration">Calibração</option>
          <option value="architecture">Arquitetura</option>
          <option value="diagnostics">Diagnóstico documental</option>
        </select>
        <button
          type="submit"
          disabled={busy || query.trim().length < 3 || !vehicleId}
        >
          {busy ? "Consultando…" : "Consultar corpus"}
        </button>
      </form>
      {busy && <p role="status">Buscando fontes aplicáveis…</p>}
      {error && (
        <p role="alert">
          Consulta indisponível. Verifique o serviço de evidências e tente
          novamente.
        </p>
      )}
      {result && (
        <KnowledgeCitations result={result} label="Corpus Knowledge Evidence" />
      )}
    </section>
  );
}
