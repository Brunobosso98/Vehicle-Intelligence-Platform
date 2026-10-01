import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SystemStatusPanel } from "../src/components/system-status";
import { getSystemStatus, isSystemStatus } from "../src/lib/api";
import { apiBaseUrl, serverStatus } from "../src/lib/server-status";

const version = {
  application: "vehicle-intelligence-platform",
  version: "0.1.0",
  environment: "test",
  git_sha: null,
  build_timestamp: null,
};
const healthy = {
  kind: "healthy",
  ready: { status: "ready", database: "ready" },
  version,
};
function response(value: unknown, ok = true) {
  return { ok, json: async () => value };
}

describe("browser status", () => {
  it("renders loading, ready and reload states", async () => {
    let resolve: ((value: ReturnType<typeof response>) => void) | undefined;
    const fetcher = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((r) => {
            resolve = r;
          }),
      )
      .mockResolvedValue(response(healthy));
    vi.stubGlobal("fetch", fetcher);
    render(<SystemStatusPanel />);
    expect(screen.getByRole("status")).toHaveTextContent("Consultando");
    resolve?.(response(healthy));
    await screen.findByText("Operacional");
    expect(screen.getByText("0.1.0")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Atualizar status" }),
    );
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  });
  it("handles unreachable backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("network failure")),
    );
    render(<SystemStatusPanel />);
    expect(
      await screen.findByText("Não foi possível conectar à API."),
    ).toBeInTheDocument();
  });
  it("does not update an unmounted component", async () => {
    let resolve: ((value: ReturnType<typeof response>) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise((r) => {
            resolve = r;
          }),
      ),
    );
    const result = render(<SystemStatusPanel />);
    result.unmount();
    resolve?.(response(healthy));
    await Promise.resolve();
  });
  it("handles HTTP errors and malformed response", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(response({}, false))
        .mockResolvedValueOnce(response({ kind: "invalid" }))
        .mockResolvedValueOnce(response(null)),
    );
    expect((await getSystemStatus()).kind).toBe("unavailable");
    expect((await getSystemStatus()).kind).toBe("error");
    expect((await getSystemStatus()).kind).toBe("error");
  });
});

describe("server proxy", () => {
  it("requires valid URL without credentials", () => {
    vi.stubEnv("API_BASE_URL", "");
    expect(apiBaseUrl).toThrow("required");
    for (const value of ["ftp://localhost", "http://user:pass@localhost"]) {
      vi.stubEnv("API_BASE_URL", value);
      expect(apiBaseUrl).toThrow("HTTP(S)");
    }
  });
  it("loads real contract fields", async () => {
    vi.stubEnv("API_BASE_URL", "http://localhost:8000");
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(response(healthy.ready))
        .mockResolvedValueOnce(response(version)),
    );
    expect(await serverStatus()).toEqual(healthy);
  });
  it("handles readiness failure and transport failure", async () => {
    vi.stubEnv("API_BASE_URL", "http://localhost:8000");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({}, false)));
    expect((await serverStatus()).kind).toBe("unavailable");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network")));
    expect((await serverStatus()).kind).toBe("unavailable");
  });
  it("rejects malformed health and version", async () => {
    vi.stubEnv("API_BASE_URL", "http://localhost:8000");
    for (const [ready, build] of [
      [{ status: "unknown" }, version],
      [{ status: "ready", database: "wrong" }, version],
      [healthy.ready, { version: 2 }],
    ]) {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValueOnce(response(ready))
          .mockResolvedValueOnce(response(build)),
      );
      expect((await serverStatus()).kind).toBe("error");
    }
  });
});

it("rejects malformed browser contracts", () => {
  for (const value of [
    null,
    "bad",
    {},
    { kind: "unavailable" },
    { kind: "error", message: 3 },
    { kind: "healthy" },
    { kind: "healthy", ready: null, version },
    { kind: "healthy", ready: {}, version },
    { kind: "healthy", ready: { status: "wrong" }, version },
    { kind: "healthy", ready: { status: "ready" }, version },
    { kind: "healthy", ready: { status: "ready", database: "wrong" }, version },
    { kind: "healthy", ready: healthy.ready, version: null },
    { kind: "healthy", ready: healthy.ready, version: {} },
    { kind: "healthy", ready: healthy.ready, version: { version: 1 } },
    { kind: "healthy", ready: healthy.ready, version: { version: "x" } },
    {
      kind: "healthy",
      ready: healthy.ready,
      version: { version: "x", environment: "unknown" },
    },
  ]) {
    expect(isSystemStatus(value)).toBe(false);
  }
  expect(isSystemStatus({ kind: "error", message: "error" })).toBe(true);
  expect(isSystemStatus({ kind: "unavailable", message: "outage" })).toBe(true);
  expect(isSystemStatus(healthy)).toBe(true);
});
