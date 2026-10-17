import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { expect, test, vi } from "vitest";
import {
  KnowledgeCitations,
  KnowledgeWorkspace,
} from "../src/components/knowledge-workspace";
import type { components } from "../../../packages/contracts/generated/api";

type Retrieval = components["schemas"]["RetrievalResult"];
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status });
const catalog = {
  sources: [],
  documents: [],
  indexes: [],
  chunks: 0,
  embeddings: 0,
};
const result: Retrieval = {
  id: "retrieval",
  index_id: "fixture-index",
  candidate_count: 0,
  wrong_platform_rejections: 0,
  latency_seconds: 0,
  scope: {
    vehicle_id: "vehicle-a",
    as_of: "2026-10-15T00:00:00Z",
    calibration: "tuned",
    temporal_valid: true,
  },
  intent: {
    query: "Unknown Stage 2 map target",
    topic: "calibration",
    need: "principle",
    top_k: 5,
  },
  evidence: [],
  knowledge_gaps: ["exact_tuner_map_target_unavailable"],
  vector_available: false,
};

test("catalog failure retries and an unknown map remains a visible documentation gap", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({}, 503))
    .mockImplementation(async (path) =>
      String(path).endsWith("/knowledge") ? json(catalog) : json(result),
    );
  render(<KnowledgeWorkspace vehicleId="vehicle-a" />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "carregar as fontes",
  );
  fireEvent.click(screen.getByRole("button", { name: "Recarregar fontes" }));
  expect(await screen.findByText(/0 fontes · 0 documentos/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Consultar referência técnica"), {
    target: { value: "Unknown Stage 2 map target" },
  });
  fireEvent.change(screen.getByLabelText("Sistema"), {
    target: { value: "calibration" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Consultar corpus" }));
  expect(
    await screen.findByText(
      "Referência técnica insuficiente para uma conclusão normativa.",
    ),
  ).toBeVisible();
  expect(screen.getByText("exact tuner map target unavailable")).toBeVisible();
  expect(screen.getByText(/Busca vetorial indisponível/)).toBeVisible();
  const posted = fetcher.mock.calls.find(
    ([, options]) => options?.method === "POST",
  );
  expect(posted?.[0]).toBe("/api/domain/vehicles/vehicle-a/knowledge/query");
  expect(JSON.parse(String(posted?.[1]?.body))).toEqual({
    intent: {
      query: "Unknown Stage 2 map target",
      topic: "calibration",
      need: "principle",
      top_k: 5,
    },
  });
});

test("query failure can be retried, and unmount cancels a pending request", async () => {
  let queryCount = 0;
  let requestSignal: AbortSignal | null | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path, options) => {
    if (String(path).endsWith("/knowledge")) return json(catalog);
    queryCount += 1;
    requestSignal = options?.signal;
    if (queryCount === 1) return json({}, 503);
    return new Promise<Response>(() => {});
  });
  const view = render(<KnowledgeWorkspace vehicleId="vehicle-a" />);
  await screen.findByText(/0 fontes · 0 documentos/);
  fireEvent.change(screen.getByLabelText("Consultar referência técnica"), {
    target: { value: "N55 fuel pressure" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Consultar corpus" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Consulta indisponível",
  );
  fireEvent.click(screen.getByRole("button", { name: "Consultar corpus" }));
  await waitFor(() => expect(queryCount).toBe(2));
  expect(screen.getByRole("button", { name: "Consultando…" })).toBeDisabled();
  act(() => view.unmount());
  expect(requestSignal?.aborted).toBe(true);
});

test("citations tolerate omitted optional arrays and keep source text inert", () => {
  const evidence: NonNullable<Retrieval["evidence"]>[number] = {
    id: "e-1",
    retrieval_run_id: "retrieval",
    index_id: "fixture-index",
    vehicle_id: "vehicle-a",
    scope_hash: "scope",
    source: {
      id: "source",
      publisher: "Synthetic supplier",
      canonical_url: "https://example.com/reference",
      source_type: "supplier",
      trust: "TIER_1_AUTHORITATIVE",
      status: "VERIFIED",
      version: 1,
    },
    document: {
      id: "version",
      document_id: "doc",
      source_id: "source",
      source_version: 1,
      title: "<img src=x onerror=alert(1)>",
      retrieved_at: "2026-10-15T00:00:00Z",
      checksum: "doc-checksum",
      mime: "text/plain",
      applicability: { calibration: "principle" },
      license_note: "Synthetic fixture",
      status: "EXTRACTED",
      extraction_version: "selection-v1",
      language: "en",
      redistribution: "synthetic",
    },
    chunk_id: "chunk",
    chunk_checksum: "chunk-checksum",
    page: 3,
    section: "Fuel system",
    heading_path: ["Fuel system"],
    snippet: "<script>alert('unsafe')</script>",
    applicability: {
      status: "PARTIAL",
      score: 0.4,
      reasons: ["exact_tune_unknown"],
      normative: false,
    },
    lexical_score: 0.2,
    vector_score: 0.8,
    fused_score: 0.1,
    quality: "reviewed",
    conflict_ids: ["conflict"],
  };
  const view = render(
    <KnowledgeCitations
      result={{
        ...result,
        evidence: [evidence],
        knowledge_gaps: undefined,
        vector_available: true,
      }}
    />,
  );
  fireEvent.click(screen.getByText(/<img src=x/));
  expect(screen.getByText(/Página 3/)).toBeVisible();
  expect(screen.getByText("exact tune unknown")).toBeVisible();
  expect(screen.getByText(/Fonte com conflito aberto/)).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Consultar publicação original" }),
  ).toHaveAttribute("href", "https://example.com/reference");
  expect(view.container.querySelector("script, img")).toBeNull();
});

test("catalog and agent citations expose distinct landmarks and reviewed conflicts", () => {
  render(
    <>
      <KnowledgeCitations result={result} label="Corpus Knowledge Evidence" />
      <KnowledgeCitations
        result={{
          ...result,
          source_conflicts: [
            {
              id: "conflict",
              left_version_id: "stock",
              right_version_id: "tune",
              topic: "fuel",
              status: "OPEN",
              explanation:
                "Synthetic stock and tune conditions remain separate.",
            },
          ],
        }}
      />
    </>,
  );
  expect(
    screen.getByRole("region", {
      name: "Corpus Knowledge Evidence",
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("region", { name: "Knowledge Evidence" }),
  ).toBeVisible();
  expect(screen.getByLabelText("Conflitos documentais")).toHaveTextContent(
    "Synthetic stock and tune conditions remain separate.",
  );
});
