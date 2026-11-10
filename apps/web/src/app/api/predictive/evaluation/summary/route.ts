import { NextRequest } from "next/server";
import summary from "@/lib/predictive/research-summary.json";
import { failure, json } from "@/app/api/predictive/_response";
import { verifySession } from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET(request: NextRequest) {
  try {
    verifySession(request);
    return json(summary);
  } catch (error) {
    return failure(error);
  }
}
