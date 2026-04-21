import { clearAuth, getAuth, setAuth } from "./auth";
import type { BrowserSnapshot, Browser } from "./types";

const APP_URL = (import.meta.env.VITE_APP_URL ?? "https://app.zima.app").replace(/\/+$/, "");
const BASE_URL = (
  import.meta.env.VITE_EXTENSION_API_URL ??
  `${APP_URL}/api/v1/extension`
).replace(/\/+$/, "");
const TOKEN_ROTATE_WINDOW_MS = 10 * 60 * 1000;

type ExtensionTokenResponse = {
  extension_token: string;
  expires_in: number;
  expires_at?: string;
};

let refreshInFlight: Promise<void> | null = null;

function resolveExpiresAt(payload: ExtensionTokenResponse): number {
  if (typeof payload.expires_at === "string") {
    const parsed = Date.parse(payload.expires_at);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return Date.now() + payload.expires_in * 1000;
}

async function refreshAuthToken(force = false): Promise<void> {
  if (refreshInFlight) {
    await refreshInFlight;
    return;
  }

  refreshInFlight = (async () => {
    const auth = await getAuth();
    if (!auth) throw new Error("Not authenticated");

    if (!force && auth.expiresAt - Date.now() > TOKEN_ROTATE_WINDOW_MS) {
      return;
    }

    const attemptedToken = auth.extensionToken;
    const res = await fetch(`${BASE_URL}/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${attemptedToken}`,
      },
      body: JSON.stringify({}),
    });

    if (res.status === 401) {
      const latestAuth = await getAuth();
      if (latestAuth && latestAuth.extensionToken !== attemptedToken) {
        return;
      }
      await clearAuth();
      throw new Error("Unauthenticated — extension token expired or revoked");
    }
    if (!res.ok) {
      throw new Error(`API error ${res.status}: ${await res.text()}`);
    }

    const payload = (await res.json()) as ExtensionTokenResponse;
    await setAuth({
      extensionToken: payload.extension_token,
      userId: auth.userId,
      expiresAt: resolveExpiresAt(payload),
    });
  })();

  try {
    await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

async function authHeaders(): Promise<Record<string, string>> {
  await refreshAuthToken(false);
  const auth = await getAuth();
  if (!auth) throw new Error("Not authenticated");
  return { Authorization: `Bearer ${auth.extensionToken}` };
}

async function post<T>(
  path: string,
  body: unknown,
  headers?: Record<string, string>
): Promise<T> {
  const attemptedToken =
    typeof headers?.Authorization === "string" && headers.Authorization.startsWith("Bearer ")
      ? headers.Authorization.slice(7)
      : null;

  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });

  if (res.status === 401) {
    if (attemptedToken) {
      const latestAuth = await getAuth();
      if (latestAuth && latestAuth.extensionToken !== attemptedToken) {
        const retryHeaders = {
          ...(headers ?? {}),
          Authorization: `Bearer ${latestAuth.extensionToken}`,
        };
        return post<T>(path, body, retryHeaders);
      }
      await clearAuth();
    }
    throw new Error("Unauthenticated — extension token expired or revoked");
  }

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }

  const text = await res.text();
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export async function register(
  setupToken: string,
  userId: string,
  browser: Browser,
  version: string
): Promise<ExtensionTokenResponse> {
  return post<ExtensionTokenResponse>(
    "/register",
    { setup_token: setupToken, user_id: userId, browser, version },
    {}
  );
}

export async function postSnapshot(snapshot: BrowserSnapshot): Promise<void> {
  const headers = await authHeaders();
  await post("/snapshot", { raw_snapshot: snapshot }, headers);
}

export async function postGuideEvent(
  provider: string,
  step: string
): Promise<void> {
  const headers = await authHeaders();
  await post("/guide-event", { provider, step }, headers);
}

export async function postHeartbeat(): Promise<void> {
  const headers = await authHeaders();
  await post("/heartbeat", {}, headers);
}
