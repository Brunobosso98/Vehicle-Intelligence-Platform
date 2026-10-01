import type { components } from "../../../../packages/contracts/generated/api";
export type Ready = components["schemas"]["Ready"];
export type Version = components["schemas"]["Version"];
export type SystemStatus =
  | { kind: "healthy"; ready: Ready; version: Version }
  | { kind: "unavailable"; message: string }
  | { kind: "error"; message: string };

export async function getSystemStatus(
  signal?: AbortSignal,
): Promise<SystemStatus> {
  try {
    const response = await fetch("/api/status", { cache: "no-store", signal });
    if (!response.ok)
      return {
        kind: "unavailable",
        message: "A API está indisponível. Tente novamente.",
      };
    const data: unknown = await response.json();
    if (!isSystemStatus(data)) {
      return { kind: "error", message: "Resposta inesperada do sistema." };
    }
    return data;
  } catch {
    return { kind: "unavailable", message: "Não foi possível conectar à API." };
  }
}

export function isSystemStatus(value: unknown): value is SystemStatus {
  if (typeof value !== "object" || value === null || !("kind" in value))
    return false;
  if (value.kind === "unavailable" || value.kind === "error") {
    return "message" in value && typeof value.message === "string";
  }
  if (value.kind !== "healthy" || !("ready" in value) || !("version" in value))
    return false;
  const ready = value.ready;
  const version = value.version;
  return (
    typeof ready === "object" &&
    ready !== null &&
    "status" in ready &&
    ready.status === "ready" &&
    "database" in ready &&
    ready.database === "ready" &&
    typeof version === "object" &&
    version !== null &&
    "version" in version &&
    typeof version.version === "string" &&
    "environment" in version &&
    ["development", "test", "production"].includes(String(version.environment))
  );
}
