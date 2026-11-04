import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST as login } from "../src/app/api/predictive/auth/login/route";
import { POST as logout } from "../src/app/api/predictive/auth/logout/route";
import { GET as session } from "../src/app/api/predictive/session/route";

const credential = "browser-operator-secret-".padEnd(48, "s");

function configure() {
  vi.stubEnv("NODE_ENV", "test");
  vi.stubEnv("ENVIRONMENT", "test");
  vi.stubEnv("PREDICTIVE_UI_ENABLED", "true");
  vi.stubEnv("PREDICTION_SERVICE_ENABLED", "true");
  vi.stubEnv("PREDICTION_OPERATOR_TOKEN", "operator-token-".padEnd(48, "x"));
  vi.stubEnv("PREDICTIVE_UI_OPERATOR_SECRET", credential);
  vi.stubEnv(
    "PREDICTIVE_UI_SESSION_SECRET",
    "session-mac-secret-".padEnd(48, "m"),
  );
  vi.stubEnv("PREDICTIVE_UI_ORIGIN", "http://localhost");
  vi.stubEnv(
    "PREDICTIVE_UI_ALLOWED_VEHICLE_IDS",
    "b11d5220-a3ae-4f0d-a6c8-7d26cc3a7351",
  );
  vi.stubEnv("PREDICTIVE_UI_API_ALLOWED_HOSTS", "api,localhost");
  vi.stubEnv("API_BASE_URL", "http://api:8000");
}

function loginRequest(
  options: {
    origin?: string;
    body?: unknown;
    cookie?: string;
    secure?: boolean;
  } = {},
) {
  return new NextRequest(
    `${options.secure ? "https" : "http"}://localhost/api/predictive/auth/login`,
    {
      method: "POST",
      headers: {
        ...(options.origin ? { origin: options.origin } : {}),
        "content-type": "application/json",
        ...(options.cookie
          ? { cookie: `vip_predictive_session=${options.cookie}` }
          : {}),
      },
      body: JSON.stringify(options.body ?? { credential }),
    },
  );
}

describe("protected operator session routes", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    configure();
  });

  it("rejects cross-origin login and incorrect operator credentials", async () => {
    const crossOrigin = await login(
      loginRequest({ origin: "https://attacker.test" }),
    );
    const wrongCredential = await login(
      loginRequest({
        origin: "http://localhost",
        body: { credential: "wrong" },
      }),
    );
    expect(crossOrigin.status).toBe(403);
    expect(wrongCredential.status).toBe(401);
    expect((await wrongCredential.json()).code).toBe("INVALID_CREDENTIAL");
  });

  it("sets a scoped HttpOnly SameSite cookie, rotates the session, and revokes it on logout", async () => {
    vi.stubEnv("PREDICTIVE_UI_ORIGIN", "https://localhost");
    const firstResponse = await login(
      loginRequest({ origin: "https://localhost", secure: true }),
    );
    expect(firstResponse.status).toBe(200);
    const firstCookie = firstResponse.headers.get("set-cookie") ?? "";
    expect(firstCookie).toContain("HttpOnly");
    expect(firstCookie.toLowerCase()).toContain("samesite=strict");
    expect(firstCookie).toContain("Path=/api/predictive");
    expect(firstCookie).toContain("Secure");
    expect(firstCookie).not.toContain("operator-token-");
    const firstToken = firstCookie.match(/vip_predictive_session=([^;]+)/)?.[1];
    expect(firstToken).toBeTruthy();
    const firstSession = session(
      new NextRequest("http://localhost/api/predictive/session", {
        headers: { cookie: `vip_predictive_session=${firstToken}` },
      }),
    );
    expect((await firstSession.json()).authenticated).toBe(true);

    const secondResponse = await login(
      loginRequest({
        origin: "https://localhost",
        cookie: firstToken,
        secure: true,
      }),
    );
    expect(secondResponse.status).toBe(200);
    const secondToken = (secondResponse.headers.get("set-cookie") ?? "").match(
      /vip_predictive_session=([^;]+)/,
    )?.[1];
    expect(secondToken).toBeTruthy();
    expect(secondToken).not.toBe(firstToken);
    expect(
      (
        await session(
          new NextRequest("http://localhost/api/predictive/session", {
            headers: { cookie: `vip_predictive_session=${firstToken}` },
          }),
        )
      ).status,
    ).toBe(200);
    expect(
      (
        await (
          await session(
            new NextRequest("http://localhost/api/predictive/session", {
              headers: { cookie: `vip_predictive_session=${firstToken}` },
            }),
          )
        ).json()
      ).authenticated,
    ).toBe(false);

    const active = await session(
      new NextRequest("http://localhost/api/predictive/session", {
        headers: { cookie: `vip_predictive_session=${secondToken}` },
      }),
    );
    const csrf = (await active.json()).csrfToken as string;
    const logoutResponse = await logout(
      new NextRequest("https://localhost/api/predictive/auth/logout", {
        method: "POST",
        headers: {
          origin: "https://localhost",
          cookie: `vip_predictive_session=${secondToken}`,
          "x-csrf-token": csrf,
        },
      }),
    );
    expect(logoutResponse.status).toBe(200);
    expect(logoutResponse.headers.get("set-cookie")).toContain("Max-Age=0");
    const afterLogout = await session(
      new NextRequest("http://localhost/api/predictive/session", {
        headers: { cookie: `vip_predictive_session=${secondToken}` },
      }),
    );
    expect(await afterLogout.json()).toMatchObject({ authenticated: false });
  });

  it("requires the session CSRF token for logout", async () => {
    const response = await login(loginRequest({ origin: "http://localhost" }));
    const token = (response.headers.get("set-cookie") ?? "").match(
      /vip_predictive_session=([^;]+)/,
    )?.[1];
    const denied = await logout(
      new NextRequest("http://localhost/api/predictive/auth/logout", {
        method: "POST",
        headers: {
          origin: "http://localhost",
          cookie: `vip_predictive_session=${token}`,
          "x-csrf-token": "wrong",
        },
      }),
    );
    expect(denied.status).toBe(403);
    expect((await denied.json()).code).toBe("CSRF_REJECTED");
  });
});
