import { NextRequest } from "next/server";
import { failure, json } from "@/app/api/predictive/_response";
import {
  isAllowedVehicle,
  predictionApiGet,
  safeEvidence,
  verifySession,
} from "@/lib/predictive/server";
import { PredictiveError } from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ vehicleId: string; receiptId: string }> },
) {
  try {
    verifySession(request);
    const { vehicleId, receiptId } = await context.params;
    if (!isAllowedVehicle(vehicleId))
      throw new PredictiveError(
        404,
        "VEHICLE_UNAVAILABLE",
        "Vehicle is unavailable in this operator scope.",
      );
    if (!/^[0-9a-f-]{36}$/i.test(receiptId))
      throw new PredictiveError(
        404,
        "RECEIPT_UNAVAILABLE",
        "This receipt is unavailable for the selected vehicle.",
      );
    const value = await predictionApiGet(
      request,
      `/api/v1/prediction-service/vehicles/${vehicleId}/runs/${receiptId}/evidence`,
    );
    return json(safeEvidence(value, receiptId));
  } catch (error) {
    return failure(error);
  }
}
