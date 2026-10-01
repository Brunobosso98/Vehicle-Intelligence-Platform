import type { Ready, SystemStatus, Version } from "./api";

export function apiBaseUrl(): string {
  const value = process.env.API_BASE_URL;
  if (!value) throw new Error("API_BASE_URL is required");
  const parsed = new URL(value);
  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    parsed.username ||
    parsed.password
  ) {
    throw new Error("API_BASE_URL must be an HTTP(S) URL without credentials");
  }
  return parsed.origin;
}

export async function serverStatus(): Promise<SystemStatus> {
  const base = apiBaseUrl();
  try {
    const [health, build] = await Promise.all([
      fetch(`${base}/health/ready`, {
        cache: "no-store",
        signal: AbortSignal.timeout(3000),
      }),
      fetch(`${base}/version`, {
        cache: "no-store",
        signal: AbortSignal.timeout(3000),
      }),
    ]);
    if (!health.ok || !build.ok)
      return {
        kind: "unavailable",
        message: "API ou banco de dados indisponível.",
      };
    const ready: Ready = await health.json();
    const version: Version = await build.json();
    if (
      ready.status !== "ready" ||
      ready.database !== "ready" ||
      typeof version.version !== "string"
    ) {
      return { kind: "error", message: "Resposta inesperada do sistema." };
    }
    return { kind: "healthy", ready, version };
  } catch {
    return { kind: "unavailable", message: "Não foi possível conectar à API." };
  }
}
