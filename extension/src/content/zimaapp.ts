// Content script on app.zima.app — relays messages between the page and the service worker.

function announce() {
  window.postMessage({ type: "ZIMA_EXTENSION_READY" }, window.location.origin);
}

window.addEventListener("message", (event: MessageEvent<unknown>) => {
  if (event.source !== window) return;
  if (event.origin !== window.location.origin) return;

  const data = event.data;
  if (typeof data !== "object" || data === null) return;
  const msg = data as Record<string, unknown>;

  // Page polling for extension presence after it loads
  if (msg["type"] === "ZIMA_CHECK_EXTENSION") {
    announce();
    return;
  }

  if (msg["type"] !== "ZIMA_CONNECT") return;
  if (typeof msg["setupToken"] !== "string" || typeof msg["userId"] !== "string") return;

  chrome.runtime.sendMessage(
    { type: "CONNECT", setupToken: msg["setupToken"], userId: msg["userId"] },
    (resp: { ok: boolean; error?: string } | undefined) => {
      window.postMessage(
        { type: "ZIMA_CONNECT_RESULT", ok: resp?.ok ?? false, error: resp?.error },
        window.location.origin,
      );
    },
  );
});

// Announce immediately on inject (catches pages that pre-register listeners)
announce();
