import { NextRequest } from "next/server";
import { failure, json } from "@/app/api/predictive/_response";
import {
  isAllowedVehicle,
  predictionApiGet,
  safeHistory,
  verifySession,
} from "@/lib/predictive/server";
import { PredictiveError } from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ vehicleId: string }> },
) {
  try {
    verifySession(request);
    const { vehicleId } = await context.params;
    if (!isAllowedVehicle(vehicleId))
      throw new PredictiveError(
        404,
        "VEHICLE_UNAVAILABLE",
        "Vehicle is unavailable in this operator scope.",
      );
    const value = await predictionApiGet(
      request,
      `/api/v1/prediction-service/vehicles/${vehicleId}/runs`,
    );
    return json(safeHistory(value, vehicleId));
  } catch (error) {
    return failure(error);
  }
}
