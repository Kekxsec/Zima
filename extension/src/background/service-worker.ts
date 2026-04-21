import { postHeartbeat, postSnapshot, register } from "../shared/api";
import { getAuth, setAuth, isConnected } from "../shared/auth";
import type { AuthState, Browser, BrowserSnapshot, InstalledExtension } from "../shared/types";

// ─── Installation / setup-token exchange ─────────────────────────────────────

const APP_BASE_URL = import.meta.env.VITE_APP_URL ?? "https://app.zima.app";
const HEARTBEAT_ALARM_NAME = "zima-heartbeat";
const HEARTBEAT_INTERVAL_MINUTES = 5;
const SNAPSHOT_INTERVAL_MS = 60 * 60 * 1000;
const LAST_SNAPSHOT_AT_KEY = "zima_last_snapshot_at";
const PRIVACY_SNAPSHOT_KEY = "zima_privacy_snapshot";
const EXTENSION_COUNT_KEY = "zima_extension_count";
const GUIDE_COMPLETIONS_KEY = "zima_guide_completions";

chrome.runtime.onInstalled.addListener(async ({ reason }) => {
  await ensureHeartbeatAlarm();

  if (reason === "install") {
    chrome.tabs.create({ url: `${APP_BASE_URL}/connect-extension` });
  }
});

chrome.runtime.onStartup.addListener(() => {
  ensureHeartbeatAlarm().catch(() => {
    // Non-fatal
  });
  runHeartbeatCycle().catch(() => {
    // Non-fatal
  });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== HEARTBEAT_ALARM_NAME) return;
  runHeartbeatCycle().catch(() => {
    // Non-fatal
  });
});

ensureHeartbeatAlarm().catch(() => {
  // Non-fatal
});
runHeartbeatCycle().catch(() => {
  // Non-fatal
});

const ALLOWED_SENDER_ORIGINS = new Set([
  APP_BASE_URL,
  chrome.runtime.getURL("").replace(/\/$/, ""),
]);

// Message from the Zima webapp (relayed by content script) or from popup
chrome.runtime.onMessage.addListener((msg: unknown, sender, sendResponse) => {
  if (!isRecord(msg)) return false;

  // Reject messages from unexpected origins
  const senderOrigin = sender.origin ?? sender.url?.replace(/(https?:\/\/[^/]+).*/, "$1");
  if (!senderOrigin || !ALLOWED_SENDER_ORIGINS.has(senderOrigin)) return false;

  if (msg["type"] === "CONNECT") {
    if (typeof msg["setupToken"] !== "string" || typeof msg["userId"] !== "string") {
      sendResponse({ ok: false, error: "Invalid CONNECT payload" });
      return false;
    }
    handleConnect(msg["setupToken"], msg["userId"]).then(sendResponse).catch((err: unknown) => {
      sendResponse({ ok: false, error: String(err) });
    });
    return true; // async response
  }

  if (msg["type"] === "TRIGGER_GUIDE") {
    if (typeof msg["provider"] !== "string" || typeof msg["url"] !== "string") {
      sendResponse({ ok: false, error: "Invalid TRIGGER_GUIDE payload" });
      return false;
    }
    triggerGuideOnTab(msg["provider"], msg["url"]);
    sendResponse({ ok: true });
    return false;
  }

  if (msg["type"] === "GUIDE_COMPLETE") {
    const provider = typeof msg["provider"] === "string" ? msg["provider"] : null;
    if (provider) {
      chrome.storage.local.get(GUIDE_COMPLETIONS_KEY, (r) => {
        const prev = (r[GUIDE_COMPLETIONS_KEY] as Record<string, boolean>) ?? {};
        void chrome.storage.local.set({ [GUIDE_COMPLETIONS_KEY]: { ...prev, [provider]: true } });
      });
    }
    focusZimaTab();
    sendResponse({ ok: true });
    return false;
  }

  return false;
});

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function handleConnect(
  setupToken: string,
  userId: string,
): Promise<{ ok: boolean; error?: string }> {
  try {
    const browser = detectBrowser();
    const version = chrome.runtime.getManifest().version;
    const registration = await register(setupToken, userId, browser, version);

    const expiresAt = resolveExpiryMs(registration.expires_at, registration.expires_in);
    const auth: AuthState = { extensionToken: registration.extension_token, userId, expiresAt };
    await setAuth(auth);
    await ensureHeartbeatAlarm();

    // Fire and forget — don't block the CONNECT response on snapshot collection
    sendSnapshot(browser, version).catch(() => {
      // Non-fatal
    });
    runHeartbeatCycle().catch(() => {
      // Non-fatal
    });

    return { ok: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function ensureHeartbeatAlarm(): Promise<void> {
  const existing = await chrome.alarms.get(HEARTBEAT_ALARM_NAME);
  if (existing) return;
  await chrome.alarms.create(HEARTBEAT_ALARM_NAME, {
    periodInMinutes: HEARTBEAT_INTERVAL_MINUTES,
  });
}

async function runHeartbeatCycle(): Promise<void> {
  const auth = await getAuth();
  if (!isConnected(auth)) return;

  await postHeartbeat();
  await maybeSendPeriodicSnapshot();
}

async function maybeSendPeriodicSnapshot(): Promise<void> {
  const now = Date.now();
  const result = await chrome.storage.session.get(LAST_SNAPSHOT_AT_KEY);
  const lastSnapshotAtRaw = result[LAST_SNAPSHOT_AT_KEY];
  const lastSnapshotAt = typeof lastSnapshotAtRaw === "number" ? lastSnapshotAtRaw : 0;
  if (now - lastSnapshotAt < SNAPSHOT_INTERVAL_MS) return;

  const browser = detectBrowser();
  const version = chrome.runtime.getManifest().version;
  await sendSnapshot(browser, version);
}

// ─── Browser snapshot ─────────────────────────────────────────────────────────

function resolveExpiryMs(expiresAtIso: string | undefined, expiresInSeconds: number): number {
  if (typeof expiresAtIso === "string") {
    const parsed = Date.parse(expiresAtIso);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return Date.now() + expiresInSeconds * 1000;
}

async function sendSnapshot(browser: Browser, version: string): Promise<void> {
  const auth = await getAuth();
  if (!isConnected(auth)) return;

  const extensions = await collectExtensions();
  const privacySettings = await collectPrivacySettings();

  const snapshot: BrowserSnapshot = { browser, version, extensions, privacySettings };
  await postSnapshot(snapshot);
  await chrome.storage.session.set({ [LAST_SNAPSHOT_AT_KEY]: Date.now() });
  await chrome.storage.local.set({
    [PRIVACY_SNAPSHOT_KEY]: privacySettings,
    [EXTENSION_COUNT_KEY]: extensions.length,
  });
}

async function collectExtensions(): Promise<InstalledExtension[]> {
  const all = await chrome.management.getAll();
  return all
    .filter((ext) => ext.id !== chrome.runtime.id)
    .map((ext) => ({
      id: ext.id,
      name: ext.name,
      version: ext.version,
      enabled: ext.enabled,
    }));
}

type PrivacySettingDetails = {
  value?: unknown;
  levelOfControl?: unknown;
};

type PrivacySettingSnapshot = {
  value: unknown;
  levelOfControl: string | null;
  error?: string;
};

function isChromeSetting(setting: unknown): setting is { get: (details: object) => Promise<PrivacySettingDetails> } {
  return typeof setting === "object" && setting !== null && typeof (setting as { get?: unknown }).get === "function";
}

async function readPrivacySetting(
  settings: Record<string, unknown>,
  key: string,
  setting: unknown,
): Promise<void> {
  if (!isChromeSetting(setting)) {
    settings[key] = {
      value: null,
      levelOfControl: null,
      error: "Unavailable in this Chrome build",
    } satisfies PrivacySettingSnapshot;
    return;
  }

  try {
    const details = await setting.get({});
    settings[key] = {
      value: details.value ?? null,
      levelOfControl:
        typeof details.levelOfControl === "string" ? details.levelOfControl : null,
    } satisfies PrivacySettingSnapshot;
  } catch (err) {
    settings[key] = {
      value: null,
      levelOfControl: null,
      error: String(err),
    } satisfies PrivacySettingSnapshot;
  }
}

async function collectPrivacySettings(): Promise<Record<string, unknown>> {
  const settings: Record<string, unknown> = {};
  const privacy = chrome.privacy as unknown as {
    network?: Record<string, unknown>;
    services?: Record<string, unknown>;
    websites?: Record<string, unknown>;
  };

  const targets: { key: string; setting: unknown }[] = [
    // network
    { key: "networkPredictionEnabled", setting: privacy.network?.["networkPredictionEnabled"] },
    { key: "webRTCIPHandlingPolicy", setting: privacy.network?.["webRTCIPHandlingPolicy"] },

    // services
    { key: "alternateErrorPagesEnabled", setting: privacy.services?.["alternateErrorPagesEnabled"] },
    { key: "autofillAddressEnabled", setting: privacy.services?.["autofillAddressEnabled"] },
    { key: "autofillCreditCardEnabled", setting: privacy.services?.["autofillCreditCardEnabled"] },
    { key: "passwordSavingEnabled", setting: privacy.services?.["passwordSavingEnabled"] },
    { key: "safeBrowsingEnabled", setting: privacy.services?.["safeBrowsingEnabled"] },
    {
      key: "safeBrowsingExtendedReportingEnabled",
      setting: privacy.services?.["safeBrowsingExtendedReportingEnabled"],
    },
    { key: "searchSuggestEnabled", setting: privacy.services?.["searchSuggestEnabled"] },
    { key: "spellingServiceEnabled", setting: privacy.services?.["spellingServiceEnabled"] },
    { key: "translationServiceEnabled", setting: privacy.services?.["translationServiceEnabled"] },

    // websites
    { key: "doNotTrackEnabled", setting: privacy.websites?.["doNotTrackEnabled"] },
    { key: "hyperlinkAuditingEnabled", setting: privacy.websites?.["hyperlinkAuditingEnabled"] },
    { key: "referrersEnabled", setting: privacy.websites?.["referrersEnabled"] },
    { key: "thirdPartyCookiesAllowed", setting: privacy.websites?.["thirdPartyCookiesAllowed"] },
    { key: "adMeasurementEnabled", setting: privacy.websites?.["adMeasurementEnabled"] },
    { key: "fledgeEnabled", setting: privacy.websites?.["fledgeEnabled"] },
    { key: "relatedWebsiteSetsEnabled", setting: privacy.websites?.["relatedWebsiteSetsEnabled"] },
    { key: "topicsEnabled", setting: privacy.websites?.["topicsEnabled"] },
  ];

  for (const { key, setting } of targets) {
    await readPrivacySetting(settings, key, setting);
  }

  return settings;
}

// ─── Guide triggering ─────────────────────────────────────────────────────────

async function triggerGuideOnTab(provider: string, targetUrl: string): Promise<void> {
  const tabs = await chrome.tabs.query({ url: `${targetUrl}*` });
  if (tabs.length > 0 && tabs[0]?.id != null) {
    await chrome.tabs.sendMessage(tabs[0].id, { type: "SHOW_GUIDE", provider });
    await chrome.tabs.update(tabs[0].id, { active: true });
  } else {
    const tab = await chrome.tabs.create({ url: targetUrl });
    chrome.tabs.onUpdated.addListener(function onUpdated(tabId, info) {
      if (tabId === tab.id && info.status === "complete") {
        chrome.tabs.onUpdated.removeListener(onUpdated);
        if (tab.id != null) {
          chrome.tabs.sendMessage(tab.id, { type: "SHOW_GUIDE", provider }).catch(() => {
            // Tab may have closed before content script was ready
          });
        }
      }
    });
  }
}

async function focusZimaTab(): Promise<void> {
  const tabs = await chrome.tabs.query({ url: `${APP_BASE_URL}/*` });
  if (tabs.length > 0 && tabs[0]?.id != null) {
    await chrome.tabs.update(tabs[0].id, { active: true });
    if (tabs[0].windowId != null) {
      await chrome.windows.update(tabs[0].windowId, { focused: true });
    }
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function detectBrowser(): Browser {
  const ua = navigator.userAgent;
  if (ua.includes("Brave")) return "brave";
  if (ua.includes("Edg/")) return "edge";
  if (ua.includes("Firefox")) return "firefox";
  return "chrome";
}
