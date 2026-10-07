import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { AgentWorkspace } from "../src/components/agent-workspace";

class Stream {
  static instances: Stream[] = [];
  listeners = new Map<string, (event: MessageEvent<string>) => void>();
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {
    Stream.instances.push(this);
  }
  addEventListener(
    type: string,
    listener: (event: MessageEvent<string>) => void,
  ) {
    this.listeners.set(type, listener);
  }
  emit(type: string, sequence: number, data: object = {}, run_id = "run-1") {
    this.listeners.get(type)?.(
      new MessageEvent("message", {
        data: JSON.stringify({
          type,
          sequence,
          data,
          run_id,
          schema_version: "1.0",
        }),
      }),
    );
  }
}

const result = {
  answer: "IAT medida: 310 K. Associação temporal não prova causa.",
  confidence: "low",
  findings: [
    {
      classification: "OBSERVATION",
      statement: "IAT: 310 K",
      evidence_ids: ["e-1"],
    },
  ],
  evidence: [
    {
      id: "e-1",
      source_tool: "get_session_summary",
      session_id: "s-1",
      pull_id: "p-1",
      event_id: null,
      configuration_id: "c-1",
      facts: [{ path: "/iat", value: 310, unit: "K" }],
    },
  ],
  context: {
    vehicle_id: "vehicle-1",
    active_configuration_id: "c-1",
    vehicle: { model: "<img src=x onerror=alert(1)>" },
    configurations: [],
    modifications: [],
    sessions: [],
  },
  uncertainties: ["Causa não demonstrada"],
  limitations: ["missing_signal"],
  missing_evidence: ["mechanical_cause"],
};
const run = (status = "running") => ({
  id: "run-1",
  status,
  user_question: "IAT?",
  error_category: status === "failed" ? "provider_unavailable" : null,
  result: status === "completed" ? result : null,
});
const audit = {
  tool_calls: [
    {
      id: "t-1",
      tool_name: "get_session_summary",
      status: "completed",
      duration_seconds: 0.2,
    },
  ],
};
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status });

beforeEach(() => {
  Stream.instances = [];
  vi.stubGlobal("EventSource", Stream);
});

async function start() {
  fireEvent.change(screen.getByLabelText("Pergunta sobre o veículo"), {
    target: { value: "IAT?" },
  });
  fireEvent.click(screen.getByText("Consultar agente"));
  await waitFor(() => expect(Stream.instances).toHaveLength(1));
  return Stream.instances[0];
}

test("streams grounded results, deduplicates replay and renders untrusted data as text", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(run()))
    .mockResolvedValueOnce(json(run("completed")))
    .mockResolvedValueOnce(json(audit))
    .mockResolvedValueOnce(json([run("completed")]))
    .mockResolvedValueOnce(json(run()));
  const { container, unmount } = render(
    <AgentWorkspace vehicleId="vehicle-1" />,
  );
  expect(screen.getByText("Consultar agente")).toBeDisabled();
  const source = await start();
  act(() => {
    source.emit("tool_started", 1, { tool_name: "get_session_summary" });
    source.emit("tool_started", 1, { tool_name: "duplicate" });
    source.emit("context_resolved", 2);
    source.emit("answer_chunk", 3, { text: "validated chunk" });
    source.emit("answer_chunk", 4, { text: "foreign" }, "other-run");
  });
  expect(screen.getByLabelText("Resposta em transmissão")).toHaveTextContent(
    "validated chunk",
  );
  expect(screen.queryByText("duplicate")).not.toBeInTheDocument();
  act(() => source.emit("run_completed", 5));
  expect(await screen.findByTestId("agent-result")).toHaveTextContent(
    "OBSERVATION",
  );
  expect(screen.getByTestId("agent-result")).toHaveTextContent(
    "missing_signal",
  );
  expect(container.querySelector("img")).toBeNull();
  expect(container.textContent).toContain("<img src=x onerror=alert(1)>");
  expect(container.textContent).toContain(
    "get_session_summary: completed (0.200 s)",
  );
  fireEvent.click(screen.getByText("Consultar agente"));
  await waitFor(() => expect(Stream.instances).toHaveLength(2));
  expect(JSON.parse(String(fetch.mock.calls[4][1]?.body))).toEqual({
    question: "IAT?",
    previous_run_id: "run-1",
  });
  unmount();
  expect(Stream.instances[1].close).toHaveBeenCalled();
  expect((fetch.mock.calls[4][1]?.signal as AbortSignal).aborted).toBe(true);
});

test("a disconnected stream resumes from its last sequence and can be cancelled", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(run()))
    .mockResolvedValueOnce(json(run()))
    .mockResolvedValueOnce(json(audit))
    .mockResolvedValueOnce(json([]))
    .mockResolvedValueOnce(json(run("cancelled")))
    .mockResolvedValueOnce(json(run("cancelled")))
    .mockResolvedValueOnce(json(audit))
    .mockResolvedValueOnce(json([]));
  render(<AgentWorkspace vehicleId="vehicle-1" />);
  const source = await start();
  act(() => {
    source.emit("context_resolved", 7);
    source.onerror?.();
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Conexão interrompida");
  fireEvent.click(screen.getByText("Recuperar execução"));
  await waitFor(() => expect(Stream.instances).toHaveLength(2));
  expect(Stream.instances[1].url).toContain("after=7");
  fireEvent.click(screen.getByText("Cancelar consulta"));
  expect(await screen.findByRole("alert")).toHaveTextContent("cancelled");
});

test("reports a malformed event and failed recovery", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(run()))
    .mockResolvedValue(json({}, 503));
  render(<AgentWorkspace vehicleId="vehicle-1" />);
  const source = await start();
  act(() =>
    source.listeners.get("answer_chunk")?.(
      new MessageEvent("message", { data: "{" }),
    ),
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Evento inesperado");
  fireEvent.click(screen.getByText("Recuperar execução"));
  await waitFor(() =>
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Execução indisponível",
    ),
  );
});

test("failed provider run stays recoverable and history can be opened", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(run()))
    .mockResolvedValueOnce(json(run("failed")))
    .mockResolvedValueOnce(json(audit))
    .mockResolvedValueOnce(json([run("failed")]))
    .mockResolvedValueOnce(json(run("completed")))
    .mockResolvedValueOnce(json(audit))
    .mockResolvedValueOnce(json([]));
  render(<AgentWorkspace vehicleId="vehicle-1" />);
  const source = await start();
  act(() => source.emit("run_failed", 1));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "provider_unavailable",
  );
  fireEvent.click(screen.getByText("IAT? — failed"));
  expect(await screen.findByTestId("agent-result")).toBeInTheDocument();
});

test("reports start and cancellation failures", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({}, 503));
  const first = render(<AgentWorkspace vehicleId="vehicle-1" />);
  fireEvent.change(screen.getByLabelText("Pergunta sobre o veículo"), {
    target: { value: "IAT?" },
  });
  fireEvent.click(screen.getByText("Consultar agente"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "agente está indisponível",
  );
  first.unmount();
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(run()))
    .mockResolvedValueOnce(json({}, 503));
  render(<AgentWorkspace vehicleId="vehicle-1" />);
  await start();
  fireEvent.click(screen.getByText("Cancelar consulta"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Não foi possível cancelar",
  );
});
