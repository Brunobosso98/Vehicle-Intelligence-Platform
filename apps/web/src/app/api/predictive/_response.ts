import { NextResponse } from "next/server";
import { errorPayload } from "@/lib/predictive/server";

export function json(body: unknown, status = 200): NextResponse {
  return NextResponse.json(body, {
    status,
    headers: {
      "Cache-Control": "private, no-store, max-age=0",
      Pragma: "no-cache",
      Vary: "Cookie",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "same-origin",
      "X-Frame-Options": "DENY",
      "Cross-Origin-Resource-Policy": "same-origin",
      "Content-Security-Policy":
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    },
  });
}

export function failure(error: unknown): NextResponse {
  const result = errorPayload(error);
  const response = json(result.body, result.status);
  if (result.status === 429)
    response.headers.set("Retry-After", String(result.retryAfterSeconds ?? 1));
  return response;
}
