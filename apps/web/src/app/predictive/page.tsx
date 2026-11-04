import type { Metadata } from "next";
import { PredictiveWorkspace } from "@/components/predictive-workspace";

export const metadata: Metadata = {
  title: "Predictive Intelligence · N55 Intelligence Lab",
  description:
    "Controlled review of persisted vehicle prediction receipts and scientific limits.",
};

export default async function PredictivePage({
  searchParams,
}: {
  searchParams: Promise<{ vehicleId?: string; receiptId?: string }>;
}) {
  const params = await searchParams;
  return (
    <PredictiveWorkspace
      initialVehicleId={params.vehicleId}
      initialReceiptId={params.receiptId}
    />
  );
}
