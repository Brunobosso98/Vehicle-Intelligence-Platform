import { NextRequest, NextResponse } from "next/server";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const base = process.env.API_BASE_URL ?? "http://api:8000";
  const target = new URL(`/api/v1/${path.join("/")}`, base);
  target.search = request.nextUrl.search;
  const liveStream = request.method === "GET" && path.at(-1) === "live";
  try {
    const authorization = request.headers.get("authorization");
    const response = await fetch(target, {
      method: request.method,
      cache: "no-store",
      headers: {
        ...(authorization ? { authorization } : {}),
        ...(request.method === "POST"
          ? { "content-type": "application/json" }
          : {}),
      },
      body: request.method === "POST" ? await request.text() : undefined,
      signal: liveStream ? undefined : AbortSignal.timeout(10_000),
    });
    return new NextResponse(
      liveStream ? response.body : await response.arrayBuffer(),
      {
        status: response.status,
        headers: {
          "content-type":
            response.headers.get("content-type") ?? "application/json",
          ...(liveStream
            ? { "cache-control": "no-store", "x-accel-buffering": "no" }
            : {}),
        },
      },
    );
  } catch {
    return NextResponse.json(
      { error: "domain API unavailable" },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
