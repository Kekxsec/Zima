import type { AuthState } from "./types";

const AUTH_KEY = "zima_auth";

export async function getAuth(): Promise<AuthState | null> {
  const result = await chrome.storage.session.get(AUTH_KEY);
  const raw = result[AUTH_KEY];
  if (!raw || typeof raw !== "object") return null;
  const state = raw as AuthState;
  if (Date.now() > state.expiresAt) {
    await clearAuth();
    return null;
  }
  return state;
}

export async function setAuth(state: AuthState): Promise<void> {
  await chrome.storage.session.set({ [AUTH_KEY]: state });
}

export async function clearAuth(): Promise<void> {
  await chrome.storage.session.remove(AUTH_KEY);
}

export function isConnected(auth: AuthState | null): auth is AuthState {
  return auth !== null && Date.now() < auth.expiresAt;
}
