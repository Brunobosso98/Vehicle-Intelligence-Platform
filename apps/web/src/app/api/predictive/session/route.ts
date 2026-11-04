import { NextRequest } from "next/server";
import { failure, json } from "../_response";
import {
  demoEnabled,
  predictiveEnabled,
  verifySession,
} from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET(request: NextRequest) {
  if (!predictiveEnabled())
    return json(
      { enabled: false, authenticated: false, demoEnabled: demoEnabled() },
      200,
    );
  try {
    const session = verifySession(request);
    return json({
      enabled: true,
      authenticated: true,
      csrfToken: session.csrf,
      expiresAt: session.expiresAt,
    });
  } catch (error) {
    const result =
      error instanceof Error && "status" in error
        ? Number((error as Error & { status: number }).status)
        : 500;
    if (result === 401)
      return json(
        { enabled: true, authenticated: false, demoEnabled: demoEnabled() },
        200,
      );
    return failure(error);
  }
}
