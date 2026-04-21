"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { api } from "@/lib/api/client"

type Phase = "idle" | "fetching" | "waiting_extension" | "sending" | "success" | "no_extension" | "error"

type ExtensionMessage =
  | { type: "ZIMA_EXTENSION_READY" }
  | { type: "ZIMA_CONNECT_RESULT"; ok: boolean; error?: string }
  | { type: "ZIMA_CHECK_EXTENSION" }

function isExtensionMessage(data: unknown): data is ExtensionMessage {
  if (typeof data !== "object" || !data) return false
  const msg = data as Record<string, unknown>
  if (msg.type === "ZIMA_EXTENSION_READY") return true
  if (msg.type === "ZIMA_CHECK_EXTENSION") return true
  if (msg.type === "ZIMA_CONNECT_RESULT" && typeof msg.ok === "boolean") return true
  return false
}

// Poll for the extension by sending ZIMA_CHECK_EXTENSION every 300ms.
// Returns true if ZIMA_EXTENSION_READY arrives within timeoutMs.
function waitForExtension(timeoutMs: number): Promise<boolean> {
  return new Promise((resolve) => {
    const deadline = Date.now() + timeoutMs
    let settled = false

    function done(found: boolean) {
      if (settled) return
      settled = true
      clearInterval(pollInterval)
      window.removeEventListener("message", handler)
      resolve(found)
    }

    function handler(event: MessageEvent) {
      if (!isExtensionMessage(event.data)) return
      if ((event.data as ExtensionMessage).type === "ZIMA_EXTENSION_READY") done(true)
    }

    window.addEventListener("message", handler)

    const pollInterval = setInterval(() => {
      if (Date.now() > deadline) { done(false); return }
      window.postMessage({ type: "ZIMA_CHECK_EXTENSION" }, window.location.origin)
    }, 300)

    // Send immediately too
    window.postMessage({ type: "ZIMA_CHECK_EXTENSION" }, window.location.origin)
  })
}

async function getSetupToken(): Promise<{ setup_token: string; user_id: string }> {
  return api.post<{ setup_token: string; user_id: string }>("/extension/setup-token")
}

const EXTENSION_TIMEOUT_MS = 3000

function waitForMessage<T extends ExtensionMessage>(
  predicate: (msg: ExtensionMessage) => msg is T,
  timeoutMs: number,
): Promise<T | null> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      window.removeEventListener("message", handler)
      resolve(null)
    }, timeoutMs)

    function handler(event: MessageEvent) {
      if (!isExtensionMessage(event.data)) return
      if (!predicate(event.data)) return
      clearTimeout(timer)
      window.removeEventListener("message", handler)
      resolve(event.data as T)
    }

    window.addEventListener("message", handler)
  })
}

function ConnectFlow({ onDone }: { onDone: (phase: Phase, error?: string) => void }) {
  useEffect(() => {
    let cancelled = false

    async function connect() {
      try {
        onDone("waiting_extension")
        const extensionFound = await waitForExtension(EXTENSION_TIMEOUT_MS)
        if (cancelled) return
        if (!extensionFound) { onDone("no_extension"); return }

        const { setup_token, user_id } = await getSetupToken()
        if (cancelled) return

        onDone("sending")

        // Send token to content script relay
        const resultPromise = waitForMessage(
          (m): m is { type: "ZIMA_CONNECT_RESULT"; ok: boolean; error?: string } =>
            m.type === "ZIMA_CONNECT_RESULT",
          EXTENSION_TIMEOUT_MS,
        )
        window.postMessage(
          { type: "ZIMA_CONNECT", setupToken: setup_token, userId: user_id },
          window.location.origin,
        )

        const result = await resultPromise
        if (cancelled) return

        if (!result) {
          onDone("error", "Extension did not respond. Try again.")
          return
        }

        onDone(result.ok ? "success" : "error", result.error)
      } catch (err: unknown) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "Unknown error"
          onDone("error", msg)
        }
      }
    }

    connect()
    return () => { cancelled = true }
  }, [onDone])

  return null
}

export default function ConnectExtensionPage() {
  const [phase, setPhase] = useState<Phase>("fetching")
  const [error, setError] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const retryCount = useRef(0)

  const handleDone = useCallback((nextPhase: Phase, err?: string) => {
    setError(err ?? null)
    setPhase(nextPhase)
  }, [])

  function retry() {
    if (retryCount.current >= 3) {
      setError("Too many retries. Please refresh the page.")
      setPhase("error")
      return
    }
    retryCount.current += 1
    setError(null)
    setPhase("fetching")
    setRetryKey((k) => k + 1)
  }

  const isLoading =
    phase === "fetching" || phase === "waiting_extension" || phase === "sending"

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      {isLoading && (
        <ConnectFlow key={retryKey} onDone={handleDone} />
      )}

      <div
        style={{
          background: "#0f172a",
          border: "1px solid #1e293b",
          borderRadius: 12,
          padding: "2rem",
          maxWidth: 420,
          width: "100%",
          color: "#f1f5f9",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 800,
            color: "#38bdf8",
            letterSpacing: "0.1em",
            marginBottom: "1.5rem",
          }}
        >
          ZIMA
        </div>

        {isLoading && (
          <>
            <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
              Connecting extension…
            </h1>
            <p style={{ fontSize: 13, color: "#94a3b8" }}>
              {phase === "fetching"
                ? "Getting a secure token…"
                : phase === "waiting_extension"
                  ? "Looking for the Zima extension…"
                  : "Authenticating…"}
            </p>
            <div
              style={{
                marginTop: "1.5rem",
                height: 3,
                background: "#1e293b",
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div style={{ height: "100%", width: "60%", background: "#38bdf8", borderRadius: 2 }} />
            </div>
          </>
        )}

        {phase === "success" && (
          <>
            <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "#22c55e" }}>
              Extension connected
            </h1>
            <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: "1.5rem" }}>
              Your browser is now linked to your Zima account. Use the extension from your toolbar
              to export your email.
            </p>
            <a
              href="/dashboard"
              style={{
                display: "block",
                textAlign: "center",
                padding: "10px 0",
                background: "#38bdf8",
                color: "#0f172a",
                borderRadius: 8,
                fontWeight: 700,
                fontSize: 13,
                textDecoration: "none",
              }}
            >
              Go to dashboard
            </a>
          </>
        )}

        {phase === "no_extension" && (
          <>
            <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
              Extension not detected
            </h1>
            <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: "1.5rem" }}>
              Install the Zima browser extension, then return to this page to connect it to your
              account.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <a
                href="https://chromewebstore.google.com"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "block",
                  textAlign: "center",
                  padding: "10px 0",
                  background: "#38bdf8",
                  color: "#0f172a",
                  borderRadius: 8,
                  fontWeight: 700,
                  fontSize: 13,
                  textDecoration: "none",
                }}
              >
                Install extension
              </a>
              <button
                onClick={retry}
                style={{
                  padding: "10px 0",
                  background: "#1e293b",
                  border: "1px solid #334155",
                  color: "#f1f5f9",
                  borderRadius: 8,
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Try again
              </button>
            </div>
          </>
        )}

        {phase === "error" && (
          <>
            <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "#ef4444" }}>
              Something went wrong
            </h1>
            <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: "1.5rem" }}>
              {error ?? "Could not connect the extension."}
            </p>
            <button
              onClick={retry}
              style={{
                width: "100%",
                padding: "10px 0",
                background: "#1e293b",
                border: "1px solid #334155",
                color: "#f1f5f9",
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          </>
        )}
      </div>
    </div>
  )
}
