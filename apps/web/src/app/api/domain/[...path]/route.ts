import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const base = process.env.API_BASE_URL ?? "http://api:8000";
  const target = new URL(`/api/v1/${path.join("/")}`, base);
  target.search = request.nextUrl.search;
  try {
    const response = await fetch(target, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "domain API unavailable" }, { status: 503 });
  }
}
