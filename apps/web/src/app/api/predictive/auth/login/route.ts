import { NextRequest } from "next/server";
import { failure, json } from "../../_response";
import {
  assertSameOrigin,
  authenticateOperator,
  clearLoginFailures,
  cookieOptions,
  createSession,
  predictiveEnabled,
  revokeSession,
  sessionCookieName,
  takeLoginFailureSlot,
} from "@/lib/predictive/server";
import { PredictiveError } from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    if (!predictiveEnabled())
      throw new PredictiveError(
        404,
        "PREDICTIVE_UNAVAILABLE",
        "Predictive workspace is unavailable.",
      );
    assertSameOrigin(request);
    if (
      !request.headers
        .get("content-type")
        ?.toLowerCase()
        .startsWith("application/json")
    ) {
      throw new PredictiveError(
        415,
        "UNSUPPORTED_MEDIA_TYPE",
        "Send a JSON operator credential.",
      );
    }
    const contentLength = Number(request.headers.get("content-length") ?? 0);
    if (contentLength > 4096)
      throw new PredictiveError(
        413,
        "REQUEST_TOO_LARGE",
        "Operator credential request is too large.",
      );
    const body = await request.text();
    if (Buffer.byteLength(body, "utf8") > 4096)
      throw new PredictiveError(
        413,
        "REQUEST_TOO_LARGE",
        "Operator credential request is too large.",
      );
    let parsed: unknown;
    try {
      parsed = JSON.parse(body) as unknown;
    } catch {
      throw new PredictiveError(
        400,
        "INVALID_REQUEST",
        "Operator credential request was malformed.",
      );
    }
    if (
      !parsed ||
      typeof parsed !== "object" ||
      Array.isArray(parsed) ||
      Object.keys(parsed).length !== 1 ||
      typeof (parsed as { credential?: unknown }).credential !== "string"
    ) {
      throw new PredictiveError(
        400,
        "INVALID_REQUEST",
        "Operator credential request was malformed.",
      );
    }
    if (!takeLoginFailureSlot())
      throw new PredictiveError(
        429,
        "LOGIN_RATE_LIMITED",
        "Sign-in is temporarily rate limited.",
      );
    if (!authenticateOperator((parsed as { credential: string }).credential)) {
      throw new PredictiveError(
        401,
        "INVALID_CREDENTIAL",
        "Operator credential was not accepted.",
      );
    }
    clearLoginFailures();
    revokeSession(request);
    const session = createSession();
    const response = json({
      authenticated: true,
      csrfToken: session.csrf,
      expiresIn: session.maxAge,
    });
    response.cookies.set(
      sessionCookieName,
      session.token,
      cookieOptions(session.maxAge, new URL(request.url).protocol === "https:"),
    );
    return response;
  } catch (error) {
    return failure(error);
  }
}
