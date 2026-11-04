import { NextRequest } from "next/server";
import { failure, json } from "../../_response";
import {
  assertSameOrigin,
  cookieOptions,
  revokeSession,
  sessionCookieName,
  verifyCsrf,
  verifySession,
} from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function POST(request: NextRequest) {
  try {
    assertSameOrigin(request);
    const session = verifySession(request);
    verifyCsrf(request, session);
    revokeSession(request);
    const response = json({ authenticated: false });
    response.cookies.set(
      sessionCookieName,
      "",
      cookieOptions(0, new URL(request.url).protocol === "https:"),
    );
    return response;
  } catch (error) {
    return failure(error);
  }
}
