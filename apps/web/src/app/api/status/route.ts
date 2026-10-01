import { serverStatus } from "../../../lib/server-status";
export const dynamic = "force-dynamic";
export async function GET() {
  const status = await serverStatus();
  return Response.json(status, { headers: { "Cache-Control": "no-store" } });
}
