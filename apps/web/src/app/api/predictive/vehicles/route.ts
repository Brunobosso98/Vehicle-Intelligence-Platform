import { NextRequest } from "next/server";
import { failure, json } from "../_response";
import { boundedVehicleIds, verifySession } from "@/lib/predictive/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET(request: NextRequest) {
  try {
    verifySession(request);
    return json({
      vehicles: boundedVehicleIds().map((vehicleId) => ({ vehicleId })),
    });
  } catch (error) {
    return failure(error);
  }
}
