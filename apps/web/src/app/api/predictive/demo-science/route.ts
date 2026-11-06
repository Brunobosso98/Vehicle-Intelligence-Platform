import summary from "@/lib/predictive/research-summary.json";
import { failure, json } from "@/app/api/predictive/_response";
import { demoEnabled, PredictiveError } from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET() {
  try {
    if (!demoEnabled())
      throw new PredictiveError(
        404,
        "DEMO_DISABLED",
        "Synthetic demonstration is disabled.",
      );
    return json(summary);
  } catch (error) {
    return failure(error);
  }
}
