import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GET, POST } from "../src/app/api/domain/[...path]/route";

function request(method = "GET") {
  return new NextRequest("http://localhost/api/domain/resource", {
    method,
    headers: {
      authorization: "Bearer browser-supplied",
      "x-investigation-token": "also-forwarded",
    },
  });
}

describe("generic domain proxy predictive-service fence", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it.each([
    ["prediction-service", "runs"],
    ["PREDICTION_SERVICE", "versions"],
    ["prediction%252dservice", "runs"],
    ["vehicles", "%2fprediction-service", "runs"],
    ["predictions", "runs"],
  ])("denies predictive alias %j before forwarding", async (...path) => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(request(), {
      params: Promise.resolve({ path }),
    });
    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({
      error: "domain resource not found",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("preserves an unrelated legacy domain request", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response("[]", { headers: { "content-type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("API_BASE_URL", "http://localhost:8000");
    const response = await GET(request(), {
      params: Promise.resolve({ path: ["vehicles"] }),
    });
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("[]");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const options = fetchMock.mock.calls[0]?.[1] ?? {};
    expect(new Headers(options.headers).get("authorization")).toBe(
      "Bearer browser-supplied",
    );
  });

  it("denies POST aliases as well as GET aliases", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request("POST"), {
      params: Promise.resolve({ path: ["prediction-service", "next-pull"] }),
    });
    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
