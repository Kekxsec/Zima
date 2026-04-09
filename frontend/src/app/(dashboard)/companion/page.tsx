"use client"

import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  Loader2,
  MonitorSmartphone,
  Terminal,
} from "lucide-react"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { CompanionStatusResponse, SetupTokenResponse } from "@/types/api"
import { cn } from "@/lib/utils"

// ─── Constants ────────────────────────────────────────────────────────────────

const COMPANION_VERSION = "0.1.0"
// Releases live in the main Zima repo, tagged companion-v<semver>
const RELEASES_BASE = `https://github.com/Kekxsec/Zima/releases/download/companion-v${COMPANION_VERSION}`
// Backend root URL used in the setup command (strip the /api/v1 path suffix)
const BACKEND_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/api\/v1$/, "")

const PLATFORMS = [
  { label: "macOS (Apple Silicon)", file: "zima-companion-arm64",          note: "M1 / M2 / M3 / M4" },
  { label: "macOS (Intel)",         file: "zima-companion-x86_64-macos",   note: "Intel x86-64" },
  { label: "Linux",                 file: "zima-companion-linux-x86_64",   note: "x86-64" },
  { label: "Windows",               file: "zima-companion-windows-x86_64.exe", note: "x86-64" },
] as const

const INSTALL_STEPS: Record<string, string[]> = {
  "macOS (Apple Silicon)": [
    `curl -Lo zima-companion "${RELEASES_BASE}/zima-companion-arm64"`,
    "chmod +x zima-companion",
    "sudo mv zima-companion /usr/local/bin/",
  ],
  "macOS (Intel)": [
    `curl -Lo zima-companion "${RELEASES_BASE}/zima-companion-x86_64-macos"`,
    "chmod +x zima-companion",
    "sudo mv zima-companion /usr/local/bin/",
  ],
  Linux: [
    `curl -Lo zima-companion "${RELEASES_BASE}/zima-companion-linux-x86_64"`,
    "chmod +x zima-companion",
    "sudo mv zima-companion /usr/local/bin/",
  ],
  Windows: [
    `# Download zima-companion-windows-x86_64.exe from the link above`,
    `# Rename it to zima-companion.exe and move it to a folder in your PATH`,
    `# Or run it directly from the download folder`,
  ],
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function copyText(text: string, label: string) {
  navigator.clipboard.writeText(text).then(() => toast.success(`${label} copied.`))
}

// ─── Download card ────────────────────────────────────────────────────────────

function DownloadCard() {
  const [selected, setSelected] = useState<string>(PLATFORMS[0].label)
  const platform = PLATFORMS.find((p) => p.label === selected)!
  const downloadUrl = `${RELEASES_BASE}/${platform.file}`
  const installSteps = INSTALL_STEPS[selected] ?? []

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Step 1. Download the companion</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground leading-relaxed">
          The companion is a small signed binary — no runtime or installation wizard required. Choose your
          platform, download, and drop it in your PATH.
        </p>

        {/* Platform selector */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {PLATFORMS.map((p) => (
            <button
              key={p.label}
              onClick={() => setSelected(p.label)}
              className={cn(
                "rounded-lg border p-3 text-left text-xs transition-all",
                selected === p.label
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/40 hover:bg-muted/40",
              )}
            >
              <p className="font-semibold">{p.label.split(" ")[0]}</p>
              <p className="mt-0.5 text-muted-foreground">{p.note}</p>
            </button>
          ))}
        </div>

        {/* Download button */}
        <div className="flex items-center gap-3 flex-wrap">
          <Button asChild className="gap-2">
            <a href={downloadUrl} download>
              <Download className="h-4 w-4" />
              Download for {selected}
            </a>
          </Button>
          <a
            href="https://github.com/Kekxsec/zima-companion/releases"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            All releases <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        {/* Install steps */}
        <div className="space-y-1.5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Install
          </p>
          <div className="rounded-lg border border-border/70 bg-background px-4 py-3">
            {installSteps.map((step) => (
              <div key={step} className="flex items-start justify-between gap-3 py-1">
                <code className="text-xs text-foreground break-all">{step}</code>
                {!step.startsWith("#") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 shrink-0 gap-1 px-2 text-[10px]"
                    onClick={() => copyText(step, "Command")}
                  >
                    <Copy className="h-3 w-3" />
                    Copy
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Connect card ─────────────────────────────────────────────────────────────

function ConnectCard() {
  const [tokenData, setTokenData] = useState<{ token: string; userId: string } | null>(null)

  const { mutate: generateSetupToken, isPending: generatingToken } = useMutation({
    mutationFn: () => api.post<SetupTokenResponse>("/companion/setup-token", {}),
    onSuccess: (res) => setTokenData({ token: res.setup_token, userId: res.user_id }),
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Could not generate a setup token.")
    },
  })

  const connectCommand = tokenData
    ? `zima-companion setup --token ${tokenData.token} --backend ${BACKEND_URL} --user_id ${tokenData.userId}`
    : ""

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Step 2. Connect to your account</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground leading-relaxed">
          Generate a one-time setup token, then run the command below on the machine where you installed the
          companion. The token expires in 15 minutes.
        </p>

        <Button
          variant="outline"
          className="gap-2"
          disabled={generatingToken}
          onClick={() => generateSetupToken()}
        >
          {generatingToken ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Terminal className="h-4 w-4" />
          )}
          {tokenData ? "Regenerate token" : "Generate setup token"}
        </Button>

        {tokenData && (
          <div className="rounded-lg border border-border/70 bg-background px-4 py-3 space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Run this command on the target machine
              </p>
              <div className="flex items-center justify-between gap-3">
                <code className="text-xs text-foreground break-all">{connectCommand}</code>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-2 shrink-0"
                  onClick={() => copyText(connectCommand, "Command")}
                >
                  <Copy className="h-4 w-4" />
                  Copy
                </Button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Token expires in 15 minutes. If it expires, click Regenerate to get a new one.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Status card ──────────────────────────────────────────────────────────────

function StatusCard() {
  const { data: companionStatus, isLoading } = useQuery({
    queryKey: ["companion-status"],
    queryFn: () => api.get<CompanionStatusResponse>("/companion/status"),
    refetchInterval: (query) => (query.state.data?.connected ? false : 8000),
  })

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <MonitorSmartphone className="h-4 w-4 text-sky-300" />
          Companion status
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : companionStatus?.connected ? (
          <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <p className="text-sm font-semibold text-foreground">Companion connected</p>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-3 text-sm text-muted-foreground">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider">Platform</p>
                <p className="mt-1">{companionStatus.platform ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider">Version</p>
                <p className="mt-1">{companionStatus.version ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider">Extensions found</p>
                <p className="mt-1">{companionStatus.extension_count}</p>
              </div>
            </div>
            {companionStatus.last_seen_at && (
              <p className="mt-3 text-xs text-muted-foreground">
                Last seen {new Date(companionStatus.last_seen_at).toLocaleString()}
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-xl border border-border bg-card/80 px-4 py-4">
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Waiting for companion to connect… This will update automatically.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CompanionPage() {
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Zima Companion</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          The companion is a lightweight binary that runs on your machine and gives Zima direct visibility
          into your installed browser extensions and settings. It reports read-only state — it does not change
          anything on your machine.
        </p>
      </div>

      <StatusCard />
      <DownloadCard />
      <ConnectCard />
    </div>
  )
}
