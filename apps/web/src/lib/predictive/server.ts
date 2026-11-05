import "server-only";

import {
  createHash,
  createHmac,
  randomBytes,
  timingSafeEqual,
} from "node:crypto";
import { isIP } from "node:net";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = "vip_predictive_session";
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MAX_RESPONSE_BYTES = 1_000_000;
const MAX_SESSION_MS = 30 * 60 * 1000;
const MAX_REQUESTS_PER_MINUTE = 180;
const MAX_CONCURRENT_REQUESTS = 4;
const HISTORY_QUERY_KEYS = new Set([
  "limit",
  "offset",
  "receipt_id",
  "result_kind",
  "task",
  "family",
  "horizon",
  "source_role",
  "status",
  "session_id",
  "pull_id",
  "configuration_id",
  "recorded_from",
  "recorded_to",
  "evidence_completeness",
  "evidence_integrity",
]);
const UUID_PATTERN_CASE_INSENSITIVE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PREDICTION_STATUSES = new Set([
  "READY_SCORE",
  "ABSTAINED_INSUFFICIENT_SIGNAL",
  "ABSTAINED_LOW_QUALITY",
  "ABSTAINED_INSUFFICIENT_REFERENCE",
  "ABSTAINED_INCOMPATIBLE_CONTEXT",
  "ABSTAINED_UNSUPPORTED_SOURCE",
  "ABSTAINED_CUTOFF",
]);
const SOURCE_ROLES = new Set([
  "synthetic",
  "real_vehicle",
  "imported",
  "imported_fixture",
]);
const SERVING_STATES = new Set([
  "APPROVED",
  "ACTIVATED",
  "REVOKED",
  "SUPERSEDED",
  "ROLLED_BACK",
]);
const PRIVATE_EVIDENCE_FIELD =
  /(?:vin|plate|license|gps|latitude|longitude|\blat\b|\blon\b|owner|user|email)/i;

type Session = { expiresAt: number; csrf: string };
type RuntimeState = {
  sessions: Map<string, Session>;
  requests: number[];
  loginFailures: number[];
  inFlight: number;
};

const globalState = globalThis as typeof globalThis & {
  __vipPredictiveState?: RuntimeState;
};
const state = (globalState.__vipPredictiveState ??= {
  sessions: new Map<string, Session>(),
  requests: [],
  loginFailures: [],
  inFlight: 0,
});

export type PredictiveProblem = {
  status: number;
  code: string;
  message: string;
};

export class PredictiveError extends Error {
  status: number;
  code: string;
  retryAfterSeconds: number | null;

  constructor(
    status: number,
    code: string,
    message: string,
    retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

function requiredSecret(name: string): string | null {
  const value = process.env[name];
  return value && value.length >= 43 && !/\s/.test(value) ? value : null;
}

function configuredOrigin(): string | null {
  const raw = process.env.PREDICTIVE_UI_ORIGIN;
  if (!raw) return null;
  try {
    const url = new URL(raw);
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.pathname !== "/" ||
      url.search ||
      url.hash
    )
      return null;
    return url.origin;
  } catch {
    return null;
  }
}

function isAwareTimestamp(value: string): boolean {
  return (
    /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) &&
    Number.isFinite(Date.parse(value))
  );
}

function vehicleAllowlist(): string[] {
  const values = (process.env.PREDICTIVE_UI_ALLOWED_VEHICLE_IDS ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  if (values.length > 20 || values.some((value) => !UUID_PATTERN.test(value))) {
    return [];
  }
  return [...new Set(values.map((value) => value.toLowerCase()))];
}

function safeApiOrigin(): URL | null {
  const raw = process.env.API_BASE_URL;
  if (!raw) return null;
  try {
    const url = new URL(raw);
    const allowedHosts = (
      process.env.PREDICTIVE_UI_API_ALLOWED_HOSTS ??
      "api,localhost,127.0.0.1,::1"
    )
      .split(",")
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);
    const hostname = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
    const hostAllowed = allowedHosts.includes(hostname);
    const loopbackHttp =
      url.protocol === "http:" &&
      (hostname === "localhost" ||
        hostname === "127.0.0.1" ||
        hostname === "::1");
    const privateServiceHttp =
      url.protocol === "http:" && hostAllowed && isIP(hostname) === 0;
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      (url.pathname !== "/" && url.pathname !== "") ||
      !hostAllowed ||
      (url.protocol === "http:" && !loopbackHttp && !privateServiceHttp)
    )
      return null;
    return new URL(url.origin);
  } catch {
    return null;
  }
}

export function predictiveEnabled(): boolean {
  const environment = process.env.ENVIRONMENT ?? process.env.APP_ENV;
  return (
    process.env.NODE_ENV !== "production" &&
    environment !== "production" &&
    (environment === "development" || environment === "test") &&
    process.env.PREDICTIVE_UI_ENABLED === "true" &&
    process.env.PREDICTION_SERVICE_ENABLED === "true" &&
    requiredSecret("PREDICTION_OPERATOR_TOKEN") !== null &&
    requiredSecret("PREDICTIVE_UI_OPERATOR_SECRET") !== null &&
    requiredSecret("PREDICTIVE_UI_SESSION_SECRET") !== null &&
    configuredOrigin() !== null &&
    vehicleAllowlist().length > 0 &&
    safeApiOrigin() !== null
  );
}

export function demoEnabled(): boolean {
  const environment = process.env.ENVIRONMENT ?? process.env.APP_ENV;
  return (
    process.env.NODE_ENV !== "production" &&
    environment !== "production" &&
    (environment === "development" || environment === "test") &&
    process.env.PREDICTIVE_UI_DEMO_ENABLED === "true"
  );
}

export function isAllowedVehicle(vehicleId: string): boolean {
  return (
    UUID_PATTERN.test(vehicleId) &&
    vehicleAllowlist().includes(vehicleId.toLowerCase())
  );
}

export function assertSameOrigin(request: NextRequest): void {
  const expectedOrigin = configuredOrigin();
  if (!expectedOrigin || new URL(request.url).origin !== expectedOrigin) {
    throw new PredictiveError(
      403,
      "SAME_ORIGIN_REQUIRED",
      "Same-origin request required.",
    );
  }
  const origin = request.headers.get("origin");
  const referer = request.headers.get("referer");
  let supplied: string | null = origin;
  if (!supplied && referer) {
    try {
      supplied = new URL(referer).origin;
    } catch {
      supplied = null;
    }
  }
  if (!supplied || supplied !== expectedOrigin) {
    throw new PredictiveError(
      403,
      "SAME_ORIGIN_REQUIRED",
      "Same-origin request required.",
    );
  }
  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") {
    throw new PredictiveError(
      403,
      "SAME_ORIGIN_REQUIRED",
      "Same-origin request required.",
    );
  }
}

function equalSecret(candidate: string, expected: string): boolean {
  const candidateDigest = createHash("sha256").update(candidate).digest();
  const expectedDigest = createHash("sha256").update(expected).digest();
  return timingSafeEqual(candidateDigest, expectedDigest);
}

function sessionMac(id: string, expiresAt: number, secret: string): string {
  return createHmac("sha256", secret)
    .update(`${id}.${expiresAt}`)
    .digest("base64url");
}

export type VerifiedSession = { id: string; csrf: string; expiresAt: number };

export function verifySession(request: NextRequest): VerifiedSession {
  if (!predictiveEnabled()) {
    throw new PredictiveError(
      404,
      "PREDICTIVE_UNAVAILABLE",
      "Predictive workspace is unavailable.",
    );
  }
  const secret = requiredSecret("PREDICTIVE_UI_SESSION_SECRET");
  if (!secret)
    throw new PredictiveError(
      404,
      "PREDICTIVE_UNAVAILABLE",
      "Predictive workspace is unavailable.",
    );
  const token = request.cookies.get(SESSION_COOKIE)?.value ?? "";
  const match = /^([A-Za-z0-9_-]{32})\.(\d{13})\.([A-Za-z0-9_-]{43})$/.exec(
    token,
  );
  if (!match)
    throw new PredictiveError(
      401,
      "SESSION_REQUIRED",
      "Sign in to view predictive results.",
    );
  const [, id, expiryString, signature] = match;
  const expiresAt = Number(expiryString);
  const expected = sessionMac(id, expiresAt, secret);
  if (!equalSecret(signature, expected) || expiresAt <= Date.now()) {
    state.sessions.delete(id);
    throw new PredictiveError(
      401,
      "SESSION_EXPIRED",
      "Your predictive session expired. Sign in again.",
    );
  }
  const session = state.sessions.get(id);
  if (!session || session.expiresAt !== expiresAt) {
    throw new PredictiveError(
      401,
      "SESSION_EXPIRED",
      "Your predictive session expired. Sign in again.",
    );
  }
  return { id, csrf: session.csrf, expiresAt };
}

export function verifyCsrf(
  request: NextRequest,
  session: VerifiedSession,
): void {
  const supplied = request.headers.get("x-csrf-token") ?? "";
  if (!equalSecret(supplied, session.csrf)) {
    throw new PredictiveError(
      403,
      "CSRF_REJECTED",
      "Request security check failed.",
    );
  }
}

export function createSession(): {
  token: string;
  csrf: string;
  maxAge: number;
} {
  const sessionSecret = requiredSecret("PREDICTIVE_UI_SESSION_SECRET");
  if (!sessionSecret)
    throw new PredictiveError(
      404,
      "PREDICTIVE_UNAVAILABLE",
      "Predictive workspace is unavailable.",
    );
  const now = Date.now();
  const expiresAt = now + MAX_SESSION_MS;
  const id = randomBytes(24).toString("base64url");
  const csrf = randomBytes(32).toString("base64url");
  state.sessions.set(id, { expiresAt, csrf });
  for (const [existingId, session] of state.sessions) {
    if (session.expiresAt <= now) state.sessions.delete(existingId);
  }
  while (state.sessions.size > 128) {
    const oldest = state.sessions.keys().next().value;
    if (!oldest) break;
    state.sessions.delete(oldest);
  }
  return {
    token: `${id}.${expiresAt}.${sessionMac(id, expiresAt, sessionSecret)}`,
    csrf,
    maxAge: Math.floor(MAX_SESSION_MS / 1000),
  };
}

export function cookieOptions(maxAge: number, secureRequest = false) {
  return {
    httpOnly: true,
    sameSite: "strict" as const,
    secure: secureRequest || process.env.PREDICTIVE_UI_COOKIE_SECURE === "true",
    path: "/api/predictive",
    maxAge,
  };
}

export function revokeSession(request: NextRequest): void {
  const token = request.cookies.get(SESSION_COOKIE)?.value ?? "";
  const secret = requiredSecret("PREDICTIVE_UI_SESSION_SECRET");
  const match = /^([A-Za-z0-9_-]{32})\.(\d{13})\.([A-Za-z0-9_-]{43})$/.exec(
    token,
  );
  if (!secret || !match) return;
  const [, id, expiryString, signature] = match;
  const expiresAt = Number(expiryString);
  const session = state.sessions.get(id);
  if (
    session?.expiresAt === expiresAt &&
    expiresAt > Date.now() &&
    equalSecret(signature, sessionMac(id, expiresAt, secret))
  )
    state.sessions.delete(id);
}

function admitRequest(): () => void {
  const now = Date.now();
  state.requests = state.requests.filter((time) => time > now - 60_000);
  if (state.requests.length >= MAX_REQUESTS_PER_MINUTE) {
    throw new PredictiveError(
      429,
      "RATE_LIMITED",
      "Predictive request limit reached. Try again shortly.",
      60,
    );
  }
  if (state.inFlight >= MAX_CONCURRENT_REQUESTS) {
    throw new PredictiveError(
      429,
      "CAPACITY_LIMITED",
      "Predictive workspace is busy. Try again shortly.",
      1,
    );
  }
  state.requests.push(now);
  state.inFlight += 1;
  return () => {
    state.inFlight = Math.max(0, state.inFlight - 1);
  };
}

function boundedRetryAfter(value: string | null, fallbackSeconds = 60): number {
  if (!value) return fallbackSeconds;
  const seconds = Number(value);
  if (Number.isFinite(seconds))
    return Math.max(1, Math.min(300, Math.ceil(seconds)));
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp)
    ? Math.max(1, Math.min(300, Math.ceil((timestamp - Date.now()) / 1000)))
    : fallbackSeconds;
}

async function boundedResponseText(response: Response): Promise<string> {
  const length = Number(response.headers.get("content-length") ?? 0);
  if (length > MAX_RESPONSE_BYTES)
    throw new PredictiveError(
      502,
      "UPSTREAM_TOO_LARGE",
      "Predictive data exceeded the response limit.",
    );
  if (!response.body) return "";
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_RESPONSE_BYTES) {
        await reader.cancel();
        throw new PredictiveError(
          502,
          "UPSTREAM_TOO_LARGE",
          "Predictive data exceeded the response limit.",
        );
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(bytes);
}

export async function predictionApiGet(
  request: NextRequest,
  path: string,
): Promise<unknown> {
  const release = admitRequest();
  try {
    const origin = safeApiOrigin();
    const token = requiredSecret("PREDICTION_OPERATOR_TOKEN");
    if (!origin || !token || !predictiveEnabled()) {
      throw new PredictiveError(
        404,
        "PREDICTIVE_UNAVAILABLE",
        "Predictive workspace is unavailable.",
      );
    }
    if (
      !/^\/api\/v1\/prediction-service\/[a-zA-Z0-9/_-]{1,400}$/.test(path) ||
      path.includes("..")
    ) {
      throw new PredictiveError(
        400,
        "INVALID_UPSTREAM_PATH",
        "Invalid predictive request.",
      );
    }
    const query = request.nextUrl.searchParams;
    if (
      request.nextUrl.search.length > 2048 ||
      query.size > HISTORY_QUERY_KEYS.size
    ) {
      throw new PredictiveError(
        400,
        "INVALID_UPSTREAM_QUERY",
        "Predictive query is too large.",
      );
    }
    const historyPath = path.includes("/vehicles/") && path.endsWith("/runs");
    const seenKeys = new Set<string>();
    for (const [key, value] of query) {
      if (
        !historyPath ||
        !HISTORY_QUERY_KEYS.has(key) ||
        seenKeys.has(key) ||
        value.length > 128
      ) {
        throw new PredictiveError(
          400,
          "INVALID_UPSTREAM_QUERY",
          "Predictive query fields are not supported.",
        );
      }
      validateHistoryFilter(key, value);
      seenKeys.add(key);
    }
    const from = query.get("recorded_from");
    const to = query.get("recorded_to");
    if (from && to && Date.parse(from) > Date.parse(to)) {
      throw new PredictiveError(
        400,
        "INVALID_UPSTREAM_QUERY",
        "Predictive date range is invalid.",
      );
    }
    const url = new URL(path, origin);
    for (const [key, value] of query) url.searchParams.append(key, value);
    const response = await fetch(url, {
      method: "GET",
      headers: { authorization: `Bearer ${token}`, accept: "application/json" },
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(8_000)]),
    });
    if (response.status >= 300 && response.status < 400) {
      throw new PredictiveError(
        502,
        "UPSTREAM_REDIRECT_REJECTED",
        "Predictive service response was rejected.",
      );
    }
    const text = await boundedResponseText(response);
    if (!response.ok) {
      if (response.status === 404)
        throw new PredictiveError(
          404,
          "RECEIPT_UNAVAILABLE",
          "This receipt is unavailable for the selected vehicle.",
        );
      if (response.status === 429)
        throw new PredictiveError(
          429,
          "UPSTREAM_RATE_LIMITED",
          "Predictive service is busy. Try again shortly.",
          boundedRetryAfter(response.headers.get("retry-after")),
        );
      if (response.status === 503 || response.status === 504)
        throw new PredictiveError(
          503,
          "SERVICE_UNAVAILABLE",
          "Predictive service is temporarily unavailable.",
        );
      throw new PredictiveError(
        502,
        "UPSTREAM_REJECTED",
        "Predictive service could not provide this result.",
      );
    }
    if (!response.headers.get("content-type")?.includes("application/json")) {
      throw new PredictiveError(
        502,
        "UPSTREAM_INVALID_CONTENT",
        "Predictive service returned an unsupported response.",
      );
    }
    try {
      return JSON.parse(text) as unknown;
    } catch {
      throw new PredictiveError(
        502,
        "UPSTREAM_INVALID_JSON",
        "Predictive service returned invalid data.",
      );
    }
  } catch (error) {
    if (error instanceof PredictiveError) throw error;
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new PredictiveError(
        504,
        "UPSTREAM_TIMEOUT",
        "Predictive service took too long to respond.",
      );
    }
    throw new PredictiveError(
      503,
      "SERVICE_UNAVAILABLE",
      "Predictive service is temporarily unavailable.",
    );
  } finally {
    release();
  }
}

function validateHistoryFilter(key: string, value: string): void {
  const enums: Record<string, Set<string>> = {
    result_kind: new Set(["next_pull", "anomaly"]),
    task: new Set([
      "NEXT_PULL_FUEL_DEVIATION",
      "NEXT_PULL_PERFORMANCE_DEGRADATION",
      "NEXT_PULL_THERMAL_DEGRADATION",
    ]),
    family: new Set(["thermal", "boost_air", "performance", "fuel"]),
    horizon: new Set(["NEXT_PULL", "AFTER_PULL_OFFLINE"]),
    source_role: SOURCE_ROLES,
    status: PREDICTION_STATUSES,
    evidence_completeness: new Set(["COMPLETE", "PARTIAL", "ABSTAINED"]),
    evidence_integrity: new Set([
      "VERIFIED",
      "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
      "FAILED_SOURCE_MISMATCH",
      "NOT_VERIFIABLE",
      "UNSUPPORTED_SCHEMA",
    ]),
  };
  if (enums[key] && !enums[key]?.has(value)) {
    throw new PredictiveError(
      400,
      "INVALID_UPSTREAM_QUERY",
      "Predictive filter value is not supported.",
    );
  }
  if (
    ["receipt_id", "session_id", "pull_id", "configuration_id"].includes(key) &&
    !UUID_PATTERN_CASE_INSENSITIVE.test(value)
  ) {
    throw new PredictiveError(
      400,
      "INVALID_UPSTREAM_QUERY",
      "Predictive identifier filter is invalid.",
    );
  }
  if (
    key === "limit" &&
    (!/^\d+$/.test(value) || Number(value) < 1 || Number(value) > 20)
  ) {
    throw new PredictiveError(
      400,
      "INVALID_UPSTREAM_QUERY",
      "Predictive page size is invalid.",
    );
  }
  if (key === "offset" && (!/^\d+$/.test(value) || Number(value) > 500)) {
    throw new PredictiveError(
      400,
      "INVALID_UPSTREAM_QUERY",
      "Predictive page offset is invalid.",
    );
  }
  if (
    ["recorded_from", "recorded_to"].includes(key) &&
    !isAwareTimestamp(value)
  ) {
    throw new PredictiveError(
      400,
      "INVALID_UPSTREAM_QUERY",
      "Predictive date filter must be a timezone-aware timestamp.",
    );
  }
}

export function errorPayload(error: unknown): {
  status: number;
  body: { error: string; code: string };
  retryAfterSeconds: number | null;
} {
  if (error instanceof PredictiveError) {
    return {
      status: error.status,
      body: { error: error.message, code: error.code },
      retryAfterSeconds: error.retryAfterSeconds,
    };
  }
  return {
    status: 500,
    body: { error: "Predictive request failed.", code: "INTERNAL_ERROR" },
    retryAfterSeconds: null,
  };
}

export function takeLoginFailureSlot(): boolean {
  const now = Date.now();
  state.loginFailures = state.loginFailures.filter(
    (time) => time > now - 60_000,
  );
  if (state.loginFailures.length >= 5) return false;
  state.loginFailures.push(now);
  return true;
}

export function clearLoginFailures(): void {
  state.loginFailures = [];
}

export function authenticateOperator(candidate: string): boolean {
  const expected = requiredSecret("PREDICTIVE_UI_OPERATOR_SECRET");
  return expected !== null && equalSecret(candidate, expected);
}

export function boundedVehicleIds(): string[] {
  return predictiveEnabled() ? vehicleAllowlist() : [];
}

export function safePrediction(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new PredictiveError(
      502,
      "INVALID_RECEIPT",
      "Receipt data was malformed.",
    );
  const input = value as Record<string, unknown>;
  if (input.schema_version !== "phase9d-prediction-response-v1") {
    throw new PredictiveError(
      422,
      "UNSUPPORTED_RECEIPT_SCHEMA",
      "Receipt schema is not supported.",
    );
  }
  if (
    typeof input.receipt_id !== "string" ||
    !UUID_PATTERN.test(input.receipt_id) ||
    !["next_pull", "anomaly"].includes(String(input.result_type))
  ) {
    throw new PredictiveError(
      502,
      "INVALID_RECEIPT",
      "Receipt data was malformed.",
    );
  }
  const nextPull = input.result_type === "next_pull";
  const uuidOrNull = (candidate: unknown): boolean =>
    candidate === null ||
    (typeof candidate === "string" &&
      UUID_PATTERN_CASE_INSENSITIVE.test(candidate));
  if (
    input.horizon !== (nextPull ? "NEXT_PULL" : "AFTER_PULL_OFFLINE") ||
    input.score_is_probability !== false ||
    (nextPull &&
      (!new Set([
        "NEXT_PULL_FUEL_DEVIATION",
        "NEXT_PULL_PERFORMANCE_DEGRADATION",
        "NEXT_PULL_THERMAL_DEGRADATION",
      ]).has(String(input.task)) ||
        input.family !== null ||
        input.anomaly_score !== null ||
        (input.decision !== null && typeof input.decision !== "boolean"))) ||
    (!nextPull &&
      (!new Set(["thermal", "boost_air", "performance", "fuel"]).has(
        String(input.family),
      ) ||
        input.task !== null ||
        input.engineering_validation_score !== null ||
        (input.decision !== null &&
          !["ANOMALOUS", "INLIER"].includes(String(input.decision))))) ||
    !SOURCE_ROLES.has(String(input.source_role)) ||
    !PREDICTION_STATUSES.has(String(input.status)) ||
    !uuidOrNull(input.model_version_id) ||
    !uuidOrNull(input.detector_version_id) ||
    typeof input.requested_cutoff !== "string" ||
    !isAwareTimestamp(input.requested_cutoff) ||
    (input.effective_cutoff !== null &&
      (typeof input.effective_cutoff !== "string" ||
        !isAwareTimestamp(input.effective_cutoff))) ||
    (input.status === "READY_SCORE" &&
      nextPull &&
      typeof input.decision !== "boolean") ||
    (input.status === "READY_SCORE" &&
      !nextPull &&
      !["ANOMALOUS", "INLIER"].includes(String(input.decision))) ||
    typeof input.interpretation !== "string" ||
    input.interpretation.length > 240 ||
    typeof input.limitation !== "string" ||
    input.limitation.length > 400
  ) {
    throw new PredictiveError(
      409,
      "INVALID_RECEIPT_SCOPE",
      "Receipt scope fields are inconsistent.",
    );
  }
  const score = nextPull
    ? input.engineering_validation_score
    : input.anomaly_score;
  if (
    (score !== null &&
      (typeof score !== "number" || !Number.isFinite(score) || score < 0)) ||
    (input.threshold !== null &&
      (typeof input.threshold !== "number" ||
        !Number.isFinite(input.threshold) ||
        input.threshold < 0)) ||
    (input.status === "READY_SCORE" && score === null) ||
    (input.status !== "READY_SCORE" && score !== null)
  ) {
    throw new PredictiveError(
      502,
      "INVALID_RECEIPT_SCORE",
      "Receipt score fields are invalid.",
    );
  }
  const common = [
    "schema_version",
    "result_type",
    "task",
    "family",
    "horizon",
    "status",
    "reason_code",
    "receipt_id",
    "requested_cutoff",
    "effective_cutoff",
    "source_role",
    "model_version_id",
    "detector_version_id",
    "feature_set_version",
    "decision",
    "engineering_validation_score",
    "anomaly_score",
    "threshold",
    "score_is_probability",
    "interpretation",
    "limitation",
  ];
  const result: Record<string, unknown> = {};
  for (const key of common) result[key] = input[key] ?? null;
  if (!isRecord(input.quality)) {
    throw new PredictiveError(
      502,
      "INVALID_RECEIPT",
      "Receipt quality data was malformed.",
    );
  }
  const quality = input.quality;
  if (
    !["high", "degraded", "insufficient", "unavailable"].includes(
      String(quality.quality_class),
    ) ||
    !isBoundedInteger(quality.observed_feature_count, 0, 128) ||
    !isBoundedInteger(quality.expected_feature_count, 0, 128) ||
    typeof quality.coverage !== "number" ||
    !Number.isFinite(quality.coverage) ||
    quality.coverage < 0 ||
    quality.coverage > 1 ||
    !isRecord(quality.missing_reason_counts) ||
    Object.keys(quality.missing_reason_counts).length > 16 ||
    Object.values(quality.missing_reason_counts).some(
      (count) => !isBoundedInteger(count, 0, 128),
    )
  )
    throw new PredictiveError(
      502,
      "INVALID_RECEIPT",
      "Receipt quality data was malformed.",
    );
  result.quality = {
    quality_class: quality.quality_class,
    observed_feature_count: quality.observed_feature_count,
    expected_feature_count: quality.expected_feature_count,
    coverage: quality.coverage,
    missing_reason_counts: quality.missing_reason_counts,
  };
  return result;
}

export function safeEvidence(
  value: unknown,
  expectedReceiptId: string,
): Record<string, unknown> {
  if (!isRecord(value))
    throw new PredictiveError(
      502,
      "INVALID_EVIDENCE",
      "Evidence data was malformed.",
    );
  const input = value;
  if (input.schema_version !== "phase9e-safe-projection-v1") {
    throw new PredictiveError(
      422,
      "UNSUPPORTED_EVIDENCE_SCHEMA",
      "Evidence schema is not supported.",
    );
  }
  if (
    input.receipt_id !== expectedReceiptId ||
    typeof input.evidence_id !== "string" ||
    !UUID_PATTERN_CASE_INSENSITIVE.test(input.evidence_id)
  ) {
    throw new PredictiveError(
      409,
      "EVIDENCE_RECEIPT_MISMATCH",
      "Evidence does not match this receipt.",
    );
  }
  const allowed = [
    "schema_version",
    "evidence_id",
    "receipt_id",
    "result_type",
    "horizon",
    "task",
    "family",
    "source_role",
    "cutoff",
    "status",
    "reason_code",
    "score",
    "threshold",
    "decision",
    "score_is_probability",
    "completeness",
    "integrity",
    "coverage",
    "observed_feature_count",
    "expected_feature_count",
    "source_type",
    "missing_reason_counts",
    "available_signals",
    "invalid_observation_count",
    "duplicate_timestamp_count",
    "pull_completeness",
    "artifact_availability",
    "facts",
    "gaps",
    "claims",
    "omitted_count",
    "node_count",
    "edge_count",
    "fact_count",
    "interpretation",
    "limitations",
  ];
  if (
    !SOURCE_ROLES.has(String(input.source_role)) ||
    !["next_pull", "anomaly"].includes(String(input.result_type)) ||
    input.horizon !==
      (input.result_type === "next_pull"
        ? "NEXT_PULL"
        : "AFTER_PULL_OFFLINE") ||
    !["COMPLETE", "PARTIAL", "ABSTAINED"].includes(
      String(input.completeness),
    ) ||
    ![
      "VERIFIED",
      "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
      "FAILED_SOURCE_MISMATCH",
      "NOT_VERIFIABLE",
      "UNSUPPORTED_SCHEMA",
    ].includes(String(input.integrity)) ||
    typeof input.coverage !== "number" ||
    !Number.isFinite(input.coverage) ||
    input.coverage < 0 ||
    input.coverage > 1 ||
    !isBoundedInteger(input.observed_feature_count, 0, 128) ||
    !isBoundedInteger(input.expected_feature_count, 0, 128) ||
    typeof input.cutoff !== "string" ||
    !isAwareTimestamp(input.cutoff) ||
    input.score_is_probability !== false ||
    (input.score !== null &&
      (typeof input.score !== "number" ||
        !Number.isFinite(input.score) ||
        input.score < 0)) ||
    (input.threshold !== null &&
      (typeof input.threshold !== "number" ||
        !Number.isFinite(input.threshold) ||
        input.threshold < 0)) ||
    !Array.isArray(input.limitations) ||
    input.limitations.length < 1 ||
    input.limitations.length > 12 ||
    input.limitations.some(
      (item) => typeof item !== "string" || item.length > 500,
    )
  )
    throw new PredictiveError(
      502,
      "INVALID_EVIDENCE",
      "Evidence provenance data was malformed.",
    );
  if (
    !Array.isArray(input.available_signals) ||
    input.available_signals.length > 32 ||
    input.available_signals.some(
      (signal) => typeof signal !== "string" || signal.length > 160,
    ) ||
    !isRecord(input.missing_reason_counts) ||
    Object.keys(input.missing_reason_counts).length > 16 ||
    Object.values(input.missing_reason_counts).some(
      (count) => !isBoundedInteger(count, 0, 128),
    ) ||
    (input.source_type !== null &&
      (typeof input.source_type !== "string" || input.source_type.length > 24))
  )
    throw new PredictiveError(
      502,
      "INVALID_EVIDENCE",
      "Evidence quality summary was malformed.",
    );
  const output: Record<string, unknown> = {};
  for (const key of allowed) output[key] = input[key] ?? null;
  if (
    !Array.isArray(input.facts) ||
    input.facts.length > 48 ||
    !Array.isArray(input.gaps) ||
    input.gaps.length > 16 ||
    !Array.isArray(input.claims) ||
    input.claims.length > 8 ||
    !Array.isArray(input.limitations) ||
    input.limitations.length > 12
  ) {
    throw new PredictiveError(
      502,
      "INVALID_EVIDENCE",
      "Evidence data was malformed.",
    );
  }
  output.facts = input.facts.map((fact) => {
    if (
      !isRecord(fact) ||
      typeof fact.id !== "string" ||
      fact.id.length > 80 ||
      typeof fact.key !== "string" ||
      fact.key.length > 160 ||
      typeof fact.type !== "string" ||
      typeof fact.quality !== "string" ||
      typeof fact.meaning !== "string" ||
      fact.meaning.length > 240 ||
      (fact.unit !== null &&
        (typeof fact.unit !== "string" || fact.unit.length > 48))
    )
      throw new PredictiveError(
        502,
        "INVALID_EVIDENCE",
        "Evidence facts were malformed.",
      );
    const item = fact;
    const privateKey = PRIVATE_EVIDENCE_FIELD.test(String(item.key));
    const sanitizedFact = sanitizeEvidenceFactValue(item.value);
    if (!sanitizedFact.valid)
      throw new PredictiveError(
        502,
        "INVALID_EVIDENCE",
        "Evidence fact values were malformed.",
      );
    const value = privateKey ? null : sanitizedFact.value;
    return {
      fact_id: item.id,
      key: item.key,
      fact_type: item.type,
      value,
      unit: item.unit,
      quality: item.quality,
      missing_reason:
        privateKey || sanitizedFact.redacted
          ? "REDACTED_FOR_OPERATOR_UI"
          : typeof item.missing_reason === "string"
            ? item.missing_reason
            : null,
      meaning: item.meaning,
    };
  });
  output.gaps = input.gaps.map((gap) => {
    if (!isRecord(gap) || typeof gap.code !== "string")
      throw new PredictiveError(
        502,
        "INVALID_EVIDENCE",
        "Evidence gaps were malformed.",
      );
    const item = gap;
    return { code: item.code, reason_code: item.reason_code };
  });
  output.claims = input.claims.map((claim) => {
    if (!isRecord(claim))
      throw new PredictiveError(
        502,
        "INVALID_EVIDENCE",
        "Evidence claims were malformed.",
      );
    const item = claim;
    return {
      claim_id: item.id,
      template: item.template,
      category: item.category,
      validation: item.validation,
    };
  });
  return output;
}

export function safeHistory(
  value: unknown,
  expectedVehicleId: string,
): Record<string, unknown> {
  if (
    !isRecord(value) ||
    value.schema_version !== "phase9h-receipt-history-v1" ||
    !Array.isArray(value.items) ||
    value.items.length > 20 ||
    !isBoundedInteger(value.total, 0, 500) ||
    !isBoundedInteger(value.limit, 1, 20) ||
    !isBoundedInteger(value.offset, 0, 500) ||
    typeof value.has_more !== "boolean"
  ) {
    throw new PredictiveError(
      502,
      "INVALID_HISTORY",
      "Receipt history was malformed.",
    );
  }
  const items = value.items.map((item) => {
    if (
      !isRecord(item) ||
      typeof item.vehicle_id !== "string" ||
      item.vehicle_id.toLowerCase() !== expectedVehicleId.toLowerCase() ||
      !isUuid(item.session_id) ||
      !isUuid(item.pull_id) ||
      !nullableUuid(item.configuration_id) ||
      !nullableString(item.source_type) ||
      (typeof item.source_type === "string" && item.source_type.length > 24) ||
      typeof item.evidence_available !== "boolean" ||
      !SERVING_STATES.has(String(item.captured_binding_state)) ||
      !SERVING_STATES.has(String(item.current_binding_state)) ||
      typeof item.recorded_at !== "string" ||
      !isAwareTimestamp(item.recorded_at)
    ) {
      throw new PredictiveError(
        409,
        "VEHICLE_SCOPE_MISMATCH",
        "Receipt did not match the selected vehicle.",
      );
    }
    const completeness = item.evidence_completeness;
    const integrity = item.evidence_integrity;
    if (
      (completeness !== null &&
        !["COMPLETE", "PARTIAL", "ABSTAINED"].includes(String(completeness))) ||
      (integrity !== null &&
        ![
          "VERIFIED",
          "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
          "FAILED_SOURCE_MISMATCH",
          "NOT_VERIFIABLE",
          "UNSUPPORTED_SCHEMA",
        ].includes(String(integrity))) ||
      (!item.evidence_available &&
        (completeness !== null || integrity !== null)) ||
      (item.evidence_available && (completeness === null || integrity === null))
    ) {
      throw new PredictiveError(
        502,
        "INVALID_HISTORY",
        "Receipt evidence status was malformed.",
      );
    }
    return {
      prediction: safePrediction(item.prediction),
      recorded_at: item.recorded_at,
      vehicle_id: item.vehicle_id,
      session_id: item.session_id,
      pull_id: item.pull_id,
      configuration_id: item.configuration_id,
      source_type: item.source_type,
      evidence_available: item.evidence_available,
      evidence_completeness: completeness,
      evidence_integrity: integrity,
      captured_binding_state: item.captured_binding_state,
      current_binding_state: item.current_binding_state,
    };
  });
  return {
    schema_version: value.schema_version,
    items,
    total: value.total,
    limit: value.limit,
    offset: value.offset,
    has_more: value.has_more,
  };
}

export function safeAgentContext(
  value: unknown,
  expectedReceiptId: string,
): Record<string, unknown> {
  if (
    !isRecord(value) ||
    value.schema_version !== "phase9h-agent-context-v1" ||
    value.receipt_id !== expectedReceiptId ||
    !Array.isArray(value.items) ||
    value.items.length > 20
  ) {
    throw new PredictiveError(
      409,
      "AGENT_RECEIPT_MISMATCH",
      "Agent context did not match this receipt.",
    );
  }
  const items = value.items.map((item) => {
    if (
      !isRecord(item) ||
      !isUuid(item.run_id) ||
      typeof item.started_at !== "string" ||
      !isAwareTimestamp(item.started_at) ||
      !["running", "completed", "failed", "cancelled"].includes(
        String(item.status),
      ) ||
      !SOURCE_ROLES.has(String(item.source_role)) ||
      !["NEXT_PULL", "AFTER_PULL_OFFLINE"].includes(String(item.horizon)) ||
      !["COMPLETE", "PARTIAL", "ABSTAINED"].includes(
        String(item.completeness),
      ) ||
      !["VERIFIED", "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE"].includes(
        String(item.integrity),
      )
    ) {
      throw new PredictiveError(
        502,
        "INVALID_AGENT_CONTEXT",
        "Agent context was malformed.",
      );
    }
    return {
      run_id: item.run_id,
      started_at: item.started_at,
      status: item.status,
      source_role: item.source_role,
      horizon: item.horizon,
      completeness: item.completeness,
      integrity: item.integrity,
    };
  });
  return {
    schema_version: value.schema_version,
    receipt_id: expectedReceiptId,
    items,
  };
}

type SanitizedFactValue = {
  valid: boolean;
  value: unknown;
  redacted: boolean;
};

function sanitizeEvidenceFactValue(value: unknown): SanitizedFactValue {
  return sanitizeEvidenceJsonValue(value, 0, { nodes: 0 });
}

function sanitizeEvidenceJsonValue(
  value: unknown,
  depth: number,
  budget: { nodes: number },
): SanitizedFactValue {
  budget.nodes += 1;
  if (depth > 8 || budget.nodes > 2048)
    return { valid: false, value: null, redacted: false };
  if (value === null || typeof value === "boolean")
    return { valid: true, value, redacted: false };
  if (typeof value === "number")
    return Number.isFinite(value)
      ? { valid: true, value, redacted: false }
      : { valid: false, value: null, redacted: false };
  if (typeof value === "string")
    return value.length <= 4096
      ? { valid: true, value, redacted: false }
      : { valid: false, value: null, redacted: false };
  if (Array.isArray(value)) {
    if (value.length > 64)
      return { valid: false, value: null, redacted: false };
    const sanitized: unknown[] = [];
    let redacted = false;
    for (const item of value) {
      const child = sanitizeEvidenceJsonValue(item, depth + 1, budget);
      if (!child.valid) return child;
      sanitized.push(child.value);
      redacted ||= child.redacted;
    }
    return { valid: true, value: sanitized, redacted };
  }
  if (!isRecord(value) || Object.keys(value).length > 32)
    return { valid: false, value: null, redacted: false };
  const sanitized: Record<string, unknown> = Object.create(null) as Record<
    string,
    unknown
  >;
  let redacted = false;
  for (const [key, item] of Object.entries(value)) {
    if (key.length > 160) return { valid: false, value: null, redacted: false };
    if (PRIVATE_EVIDENCE_FIELD.test(key)) {
      sanitized[key] = null;
      redacted = true;
      continue;
    }
    const child = sanitizeEvidenceJsonValue(item, depth + 1, budget);
    if (!child.valid) return child;
    sanitized[key] = child.value;
    redacted ||= child.redacted;
  }
  return { valid: true, value: sanitized, redacted };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isBoundedInteger(
  value: unknown,
  min: number,
  max: number,
): value is number {
  return (
    typeof value === "number" &&
    Number.isInteger(value) &&
    value >= min &&
    value <= max
  );
}

function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN_CASE_INSENSITIVE.test(value);
}

function nullableUuid(value: unknown): value is string | null {
  return value === null || isUuid(value);
}

function nullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

export const sessionCookieName = SESSION_COOKIE;
