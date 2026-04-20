"use client"

import Link from "next/link"
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Copy,
  ExternalLink,
  Info,
  Laptop,
  MonitorSmartphone,
  Play,
  Plus,
  Puzzle,
  Shield,
  ShieldCheck,
  Wifi,
} from "lucide-react"
import { toast } from "sonner"
import { api, ApiRequestError } from "@/lib/api/client"
import { SeverityBadge } from "@/components/ui/SeverityBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { hasBrowserInputs } from "@/lib/browserReview"
import { usePasswordManagerFlow } from "@/lib/usePasswordManagerFlow"
import type {
  AccountResponse,
  Asset,
  AssetOut,
  CompanionStatusResponse,
  FindingListResponse,
  Scan,
  ScanListResponse,
  Signal,
  SignalListResponse,
} from "@/types/api"

type BrowserInfo = {
  osName: string
  browserName: string
  deviceLabel: string
}

const DNS_PRIMARY = "9.9.9.9"
const DNS_SECONDARY = "149.112.112.112"

type ToolLink = {
  label: string
  href: string
}

type RecommendedBrowserTool = {
  name: string
  why: string
  badge?: string
  caution?: string
  links: ToolLink[]
}

function detectCurrentBrowserInfo(): BrowserInfo {
  if (typeof window === "undefined") {
    return {
      osName: "Computer",
      browserName: "Browser",
      deviceLabel: "Computer · Browser",
    }
  }

  const ua = window.navigator.userAgent
  const platform = window.navigator.platform

  const osName =
    /Mac/i.test(platform) || /Mac OS X/i.test(ua)
      ? "Mac"
      : /Win/i.test(platform) || /Windows/i.test(ua)
      ? "Windows"
      : /Linux/i.test(platform) || /Linux/i.test(ua)
      ? "Linux"
      : /iPhone|iPad|iPod/i.test(ua)
      ? "iPhone or iPad"
      : /Android/i.test(ua)
      ? "Android"
      : "Computer"

  const browserName =
    /Edg\//i.test(ua)
      ? "Edge"
      : /Firefox\//i.test(ua)
      ? "Firefox"
      : /Chrome\//i.test(ua) && !/Edg\//i.test(ua)
      ? "Chrome"
      : /Safari\//i.test(ua) && !/Chrome\//i.test(ua)
      ? "Safari"
      : "Browser"

  return {
    osName,
    browserName,
    deviceLabel: `${osName} · ${browserName}`,
  }
}

function formatBrowserAssetValue(asset: Asset) {
  if (asset.entity_type !== "url") return asset.value

  const parts = asset.value.split(":")
  if (parts.length >= 3) {
    const [identifier, , platform] = parts
    return `${platform} extension · ${identifier}`
  }
  return asset.value
}

function getLatestBrowserInputAt(assets: Asset[]) {
  if (assets.length === 0) return null

  return Math.max(
    ...assets.map((asset) => Date.parse(asset.updated_at || asset.created_at)),
  )
}

function getLatestCompletedScanAfter(scans: Scan[], since: number | null) {
  if (!Number.isFinite(since)) return null

  return scans
    .filter((scan) => scan.status === "completed" && scan.completed_at)
    .sort((a, b) => Date.parse(b.completed_at || "") - Date.parse(a.completed_at || ""))
    .find((scan) => {
      const completedAt = Date.parse(scan.completed_at || "")
      return Number.isFinite(completedAt) && completedAt >= (since ?? 0)
    }) ?? null
}

function isBrowserSignal(signal: Signal) {
  return signal.category === "browser_security" || signal.signal_type === "malicious_extension_found"
}

function browserSignalLabel(signal: Signal) {
  if (signal.signal_type === "malicious_extension_found") return "Malicious extension"
  if (signal.signal_type === "browser_extension_risk") return "Extension risk"
  return "Browser setting"
}

function browserSettingsChecklist(browserName: string) {
  if (browserName === "Firefox") {
    return [
      "Turn on Enhanced Tracking Protection and set it to Strict if your sites still work properly.",
      "Turn on DNS over HTTPS and use Increased or Max protection if your network allows it.",
      "Turn on HTTPS-Only Mode so insecure sites are harder to open by accident.",
      "Keep Firefox and all extensions updating automatically.",
      "Remove old extensions and keep only the few you truly use.",
    ]
  }

  if (browserName === "Brave") {
    return [
      "Keep Shields on by default and block third-party cookies.",
      "Set Upgrade Connections to HTTPS to Strict.",
      "Pick a secure DNS provider in Security settings.",
      "Keep Brave and all extensions updating automatically.",
      "Remove extensions you installed for one-off tasks and no longer need.",
    ]
  }

  return [
    "Turn on the strongest tracking protection your browser supports without breaking the sites you rely on.",
    "Turn on secure DNS or DNS over HTTPS where available.",
    "Prefer HTTPS-only or strict HTTPS upgrade modes.",
    "Keep the browser and extensions updating automatically.",
    "Remove unused extensions and keep the extension list small.",
  ]
}

function saferBrowserChoices(currentBrowser: string) {
  return [
    {
      name: "Stay with your current browser",
      description:
        "This is fine if you keep it updated, trim your extensions, and turn on the strongest privacy settings it supports.",
      emphasized: true,
    },
    {
      name: "Firefox",
      description:
        currentBrowser === "Firefox"
          ? "You are already on a strong choice for privacy controls and extension flexibility."
          : "A good fit if you want clear privacy controls, strong extension support, and easy DNS-over-HTTPS settings.",
      href: "https://support.mozilla.org/en-US/kb/dns-over-https",
    },
    {
      name: "Brave",
      description:
        currentBrowser === "Brave"
          ? "You are already using stronger privacy defaults than most mainstream browsers ship with."
          : "A good fit if you want stronger privacy defaults out of the box with less manual setup.",
      href: "https://support.brave.com/hc/en-us/articles/360022806212-How-do-I-use-Shields-while-browsing",
    },
  ]
}

function browserDownloadLinks() {
  return [
    { label: "Download Firefox", href: "https://www.mozilla.org/firefox/new/" },
    { label: "Download Brave", href: "https://brave.com/download/" },
  ]
}

function passwordManagerInstallLinks(browserName: string) {
  const protonHref =
    browserName === "Firefox"
      ? "https://proton.me/pass/download/firefox"
      : browserName === "Edge"
      ? "https://proton.me/pass/download/edge"
      : browserName === "Brave"
      ? "https://proton.me/pass/download/brave"
      : "https://proton.me/pass/download/chrome"

  return [
    { label: "Bitwarden", href: "https://bitwarden.com/help/getting-started-browserext/" },
    { label: "1Password", href: "https://1password.com/downloads/browser-extension" },
    { label: "Proton Pass", href: protonHref },
  ]
}

function ublockInstallLink(browserName: string): ToolLink {
  if (browserName === "Firefox") {
    return {
      label: "Install uBlock Origin",
      href: "https://addons.mozilla.org/en-US/firefox/addon/ublock-origin/",
    }
  }

  if (browserName === "Edge") {
    return {
      label: "Install uBlock Origin",
      href: "https://microsoftedge.microsoft.com/addons/detail/odfafepnkmbhccpbejgmiehpchacaeak",
    }
  }

  return {
    label: "Install uBlock Origin",
    href: "https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm",
  }
}

function virusTotalInstallLink(browserName: string): ToolLink {
  if (browserName === "Firefox") {
    return {
      label: "Install VT4Browsers",
      href: "https://addons.mozilla.org/en-US/firefox/addon/vt4browsers/",
    }
  }

  if (browserName === "Edge") {
    return {
      label: "Install VT4Browsers",
      href: "https://microsoftedge.microsoft.com/addons/detail/vt4browsers/feklilkmifhginhfoogmgelcopaplodb",
    }
  }

  return {
    label: "Install VT4Browsers",
    href: "https://chrome.google.com/webstore/detail/efbjojhplkelaegfbieplglfidafgoka",
  }
}

function recommendedBrowserTools(browserName: string): RecommendedBrowserTool[] {
  return [
    {
      name: "Password manager extension",
      why:
        "Use one official password-manager extension so logins are filled only on the correct site and you can stop relying on the browser's built-in password manager.",
      badge: "Core",
      links: passwordManagerInstallLinks(browserName),
    },
    {
      name: "uBlock Origin",
      why:
        "This is the cleanest first install from your process docs. It blocks ads, trackers, and many malicious pages with very little setup.",
      badge: "Core",
      links: [ublockInstallLink(browserName)],
    },
    {
      name: "Malwarebytes Browser Guard",
      why:
        "This matches your process docs as well. It focuses on scam, phishing, and malicious-page blocking in a very simple way.",
      badge: "Core",
      links: [{ label: "Install Browser Guard", href: "https://www.malwarebytes.com/browserguard" }],
    },
    {
      name: "VirusTotal browser extension",
      why:
        "Useful when you want to right-click a suspicious link or file and check it before trusting it.",
      badge: "Optional",
      caution:
        "Review the extension settings carefully before enabling automatic submissions, because uploads may share material with VirusTotal.",
      links: [virusTotalInstallLink(browserName)],
    },
    {
      name: "NoScript",
      why:
        "This is a strong option for people who want aggressive script blocking, but it is an advanced tool and can break normal websites until you allow trusted sites.",
      badge: "Advanced",
      caution: "Best for Firefox users who are comfortable making trust decisions site by site.",
      links: [{ label: "Install NoScript for Firefox", href: "https://addons.mozilla.org/en-US/firefox/addon/noscript/" }],
    },
    {
      name: "HTTPS Everywhere",
      why:
        "Do not install this now. EFF says modern browsers already have native HTTPS-only or strict HTTPS modes.",
      badge: "Replaced",
      links: [{ label: "Read EFF guidance", href: "https://www.eff.org/https-everywhere/" }],
    },
  ]
}

function dnsSetupSteps(osName: string) {
  if (osName === "Windows") {
    return [
      "Open Network & Internet Settings.",
      "Open adapter settings, then IPv4 properties for your current network.",
      `Paste ${DNS_PRIMARY} and ${DNS_SECONDARY} as your DNS servers.`,
    ]
  }

  if (osName === "Mac") {
    return [
      "Open System Settings, then Network.",
      "Open your active connection and go to DNS.",
      `Add ${DNS_PRIMARY} and ${DNS_SECONDARY}, then apply the changes.`,
    ]
  }

  return [
    "Open your network settings for the connection you use every day.",
    "Find the DNS or Name Server section.",
    `Paste ${DNS_PRIMARY} and ${DNS_SECONDARY}, then reconnect if needed.`,
  ]
}

async function copyText(value: string, label: string) {
  try {
    await navigator.clipboard.writeText(value)
    toast.success(`${label} copied.`)
  } catch {
    toast.error(`Could not copy ${label.toLowerCase()}.`)
  }
}

export default function BrowserPage() {
  const qc = useQueryClient()
  const [localBrowserInfo] = useState(detectCurrentBrowserInfo)
  const [extensionInput, setExtensionInput] = useState("")

  const { data: accountData, isLoading: accountLoading } = useQuery({
    queryKey: ["browser-account"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })
const { data: findingsData } = useQuery({
    queryKey: ["browser-open-findings"],
    queryFn: () => api.get<FindingListResponse>("/findings?limit=1&filter_status=open"),
  })
  const { data: signalsData, isLoading: signalsLoading } = useQuery({
    queryKey: ["browser-signals"],
    queryFn: () => api.get<SignalListResponse>("/signals?limit=100&filter_status=open"),
  })
  const { data: scansData } = useQuery({
    queryKey: ["browser-scans"],
    queryFn: () => api.get<ScanListResponse>("/scans?limit=10"),
  })
  const { data: companionStatus } = useQuery({
    queryKey: ["companion-status"],
    queryFn: () => api.get<CompanionStatusResponse>("/companion/status"),
    refetchInterval: 30_000,
  })

  const openFindings = findingsData?.total ?? 0
  const { exportCompleted } = usePasswordManagerFlow(accountData?.user.user_id)
  const browserAssets = (accountData?.assets ?? []).filter(
    (asset) => asset.entity_type === "device" || asset.entity_type === "url",
  )
  const browserSignals = (signalsData?.signals ?? []).filter(isBrowserSignal)
  const hasBrowserInputsSaved = hasBrowserInputs(accountData?.assets ?? [])
  const hasSavedCurrentDevice = browserAssets.some(
    (asset) => asset.entity_type === "device" && asset.value === localBrowserInfo.deviceLabel,
  )
  const canStartBrowserStage = exportCompleted && openFindings === 0
  const latestBrowserInputAt = getLatestBrowserInputAt(browserAssets)
  const latestCompletedBrowserScan = getLatestCompletedScanAfter(scansData?.scans ?? [], latestBrowserInputAt)
  const hasCompletedBrowserScan = Boolean(latestCompletedBrowserScan)
  const savedExtensionAssets = browserAssets.filter((asset) => asset.entity_type === "url")
  const localInspectionLikelyUnavailable =
    hasCompletedBrowserScan &&
    browserSignals.length === 0 &&
    browserAssets.some((asset) => asset.entity_type === "device") &&
    savedExtensionAssets.length === 0

  const refreshBrowserData = () => {
    qc.invalidateQueries({ queryKey: ["browser-account"] })
    qc.invalidateQueries({ queryKey: ["scores-account"] })
    qc.invalidateQueries({ queryKey: ["dashboard-account"] })
    qc.invalidateQueries({ queryKey: ["accounts-profile"] })
  }

  const { mutate: saveDevice, isPending: savingDevice } = useMutation({
    mutationFn: () =>
      api.post<AssetOut>("/assets", {
        entity_type: "device",
        value: localBrowserInfo.deviceLabel,
      }),
    onSuccess: () => {
      toast.success("This browser and device are saved for review.")
      refreshBrowserData()
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Could not save this device.")
    },
  })

  const { mutate: saveExtension, isPending: savingExtension } = useMutation({
    mutationFn: () =>
      api.post<AssetOut>("/assets", {
        entity_type: "url",
        value: extensionInput,
      }),
    onSuccess: () => {
      toast.success("Extension saved for browser review.")
      setExtensionInput("")
      refreshBrowserData()
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Could not save that extension.")
    },
  })

  const { mutate: runBrowserScan, isPending: startingScan } = useMutation({
    mutationFn: () => api.post<Scan>("/scans", { tier: "standard" }),
    onSuccess: (scan) => {
      toast.success("Browser review scan started.")
      qc.invalidateQueries({ queryKey: ["scans"] })
      qc.invalidateQueries({ queryKey: ["browser-signals"] })
      window.location.href = `/dashboard?scan_id=${scan.id}`
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Could not start the browser review scan.")
    },
  })

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Secure your browser</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          After your account cleanup, the next stage is the browser you use every day. We need to know which
          browser you use, which extensions are installed, and which settings should be tightened.
        </p>
      </div>

      <Card>
        <CardContent className="flex items-start justify-between gap-4 p-5 flex-wrap">
          <div className="flex items-start gap-3">
            <MonitorSmartphone className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">
                {companionStatus?.connected ? "Companion connected" : "Zima Companion"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
                {companionStatus?.connected
                  ? `${companionStatus.platform ?? "Unknown platform"} · v${companionStatus.version ?? "?"} · ${companionStatus.extension_count} extension${companionStatus.extension_count === 1 ? "" : "s"} found`
                  : "Install the companion to give Zima direct visibility into your browser extensions and settings."}
              </p>
            </div>
          </div>
          <Button variant="outline" className="gap-2 shrink-0" asChild>
            <Link href="/companion">
              {companionStatus?.connected ? "Manage companion" : "Set up companion"}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      {!canStartBrowserStage && (
        <Card className="border-primary/25 bg-primary/10">
          <CardContent className="flex items-start justify-between gap-4 p-5 flex-wrap">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">
                Finish the account stages before you focus here
              </p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                Browser hardening comes after your accounts are organised and the urgent online-account issues are
                under control.
              </p>
            </div>
            <Button className="gap-2" asChild>
              <Link href={exportCompleted ? "/findings" : "/accounts"}>
                {exportCompleted ? "Go to priorities" : "Go to accounts"}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Tell Zima about this browser</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {accountLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <>
              <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
                <div className="flex items-center gap-2">
                  <Laptop className="h-4 w-4 text-violet-400" />
                  <p className="text-sm font-semibold text-foreground">{localBrowserInfo.deviceLabel}</p>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Save the browser you use every day first. That gives Zima a target for the browser review.
                </p>
                <Button
                  variant="outline"
                  className="mt-3 gap-2"
                  disabled={savingDevice || hasSavedCurrentDevice}
                  onClick={() => saveDevice()}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  {hasSavedCurrentDevice ? "Browser saved" : "Save this browser"}
                </Button>
              </div>

              <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
                <div className="flex items-center gap-2">
                  <Puzzle className="h-4 w-4 text-violet-300" />
                  <p className="text-sm font-semibold text-foreground">Optional: add browser tools you already use</p>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Paste the official install page for any extension you already trust and use. Zima can assess
                  that extension even if it cannot inspect your local browser files yet.
                </p>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <Input
                    value={extensionInput}
                    onChange={(event) => setExtensionInput(event.target.value)}
                    placeholder="Paste the extension install page"
                  />
                  <Button
                    className="gap-2"
                    disabled={savingExtension || extensionInput.trim().length === 0}
                    onClick={() => saveExtension()}
                  >
                    <Plus className="h-4 w-4" />
                    Add
                  </Button>
                </div>
              </div>

              {browserAssets.length > 0 && (
                <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
                  <p className="text-sm font-semibold text-foreground">Saved for review</p>
                  <div className="mt-3 space-y-2">
                    {browserAssets.map((asset) => (
                      <div key={asset.asset_id} className="flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-background px-3 py-3">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground">{formatBrowserAssetValue(asset)}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {asset.entity_type === "url" ? "Extension saved for review" : "Browser saved for review"}
                          </p>
                        </div>
                        <Badge variant="secondary" className="rounded-full">
                          {asset.entity_type === "url" ? "Extension" : "Browser"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
                <div className="flex items-start gap-3">
                  <Info className="mt-0.5 h-4 w-4 text-violet-400 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-foreground">What this scan can check today</p>
                    <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                      Zima can always review extension links you save here. To inspect your real installed
                      extensions and browser settings, Zima also needs access to the browser files on this
                      machine.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  className="gap-2"
                  disabled={startingScan || !hasBrowserInputsSaved || !canStartBrowserStage}
                  onClick={() => runBrowserScan()}
                >
                  <Play className="h-4 w-4" />
                  Run browser review scan
                </Button>
                {!hasBrowserInputsSaved && (
                  <p className="text-sm text-muted-foreground">
                    Save your browser first, then run the scan.
                  </p>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {hasCompletedBrowserScan && browserSignals.length === 0 && (
        <Card className="border-amber-500/25 bg-amber-500/10">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Why the last browser scan looked empty</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-200 shrink-0" />
              <p className="leading-relaxed">
                Zima did not find any browser issues from the data it could see in your last scan.
              </p>
            </div>
            {localInspectionLikelyUnavailable ? (
              <p className="leading-relaxed">
                You only saved the browser itself. That tells Zima what you use, but it does not expose your
                real installed extensions or settings. In Docker or a hosted setup, local browser inspection will
                stay empty until Zima has machine access through folder mounts or a local helper tool.
              </p>
            ) : (
              <p className="leading-relaxed">
                If you expected installed extensions or browser settings to appear here, Zima likely could not
                see the local browser files on this machine. The extension links you save manually can still be
                reviewed without that deeper access.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">What we found in your browser review</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {signalsLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, index) => (
                <Skeleton key={index} className="h-24 w-full" />
              ))}
            </div>
          ) : browserSignals.length > 0 ? (
            browserSignals.map((signal) => (
              <div key={signal.signal_id} className="rounded-xl border border-border bg-card/80 px-4 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-foreground">{signal.summary}</p>
                      <Badge variant="secondary" className="rounded-full">
                        {browserSignalLabel(signal)}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {signal.details ?? "Review this item in the context of the browser you use every day."}
                    </p>
                    {signal.recommended_action && (
                      <p className="mt-2 text-sm text-foreground">Next step: {signal.recommended_action}</p>
                    )}
                  </div>
                  <SeverityBadge severity={signal.severity} className="w-[72px] justify-center shrink-0" />
                </div>
              </div>
            ))
          ) : (
            <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
              <p className="text-sm font-semibold text-foreground">No browser findings are showing yet</p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                If you just saved browser details, run a fresh scan above. If the next scan is still empty, use
                the hardening plan below and treat this stage as a manual setup checklist for now.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Simple browser hardening plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3 rounded-xl border border-border bg-card/80 px-4 py-4">
            <p className="text-sm font-semibold text-foreground">1. Choose the browser you want to keep using</p>
            {saferBrowserChoices(localBrowserInfo.browserName).map((choice) => (
              <div key={choice.name} className="rounded-lg border border-border/70 bg-background px-3 py-3">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <p className="text-sm font-medium text-foreground">{choice.name}</p>
                  {choice.emphasized && <Badge variant="secondary" className="rounded-full">Current choice</Badge>}
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{choice.description}</p>
                {choice.href && (
                  <Button variant="ghost" size="sm" className="mt-1 gap-2 px-0" asChild>
                    <Link href={choice.href} target="_blank" rel="noreferrer">
                      Read official guide
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </Button>
                )}
              </div>
            ))}
            <div className="flex flex-wrap gap-2">
              {browserDownloadLinks().map((link) => (
                <Button key={link.href} variant="outline" size="sm" className="gap-2" asChild>
                  <Link href={link.href} target="_blank" rel="noreferrer">
                    {link.label}
                    <ExternalLink className="h-4 w-4" />
                  </Link>
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-3 rounded-xl border border-border bg-card/80 px-4 py-4">
            <p className="text-sm font-semibold text-foreground">2. Turn on the important safety settings</p>
            {browserSettingsChecklist(localBrowserInfo.browserName).map((item) => (
              <div key={item} className="rounded-lg border border-border/70 bg-background px-3 py-3 text-sm text-muted-foreground">
                {item}
              </div>
            ))}
          </div>

          <div className="space-y-3 rounded-xl border border-border bg-card/80 px-4 py-4">
            <div className="flex items-center gap-2">
              <Wifi className="h-4 w-4 text-violet-400" />
              <p className="text-sm font-semibold text-foreground">3. Use secure DNS</p>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Recommended: Quad9. Copy these values into your network settings.
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg border border-border/70 bg-background px-3 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Primary</p>
                <div className="mt-1 flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">{DNS_PRIMARY}</p>
                  <Button variant="ghost" size="sm" className="gap-2" onClick={() => copyText(DNS_PRIMARY, "Primary DNS")}>
                    <Copy className="h-4 w-4" />
                    Copy
                  </Button>
                </div>
              </div>
              <div className="rounded-lg border border-border/70 bg-background px-3 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Secondary</p>
                <div className="mt-1 flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">{DNS_SECONDARY}</p>
                  <Button variant="ghost" size="sm" className="gap-2" onClick={() => copyText(DNS_SECONDARY, "Secondary DNS")}>
                    <Copy className="h-4 w-4" />
                    Copy
                  </Button>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              {dnsSetupSteps(localBrowserInfo.osName).map((step) => (
                <div key={step} className="rounded-lg border border-border/70 bg-background px-3 py-3 text-sm text-muted-foreground">
                  {step}
                </div>
              ))}
            </div>
            <Button variant="ghost" size="sm" className="gap-2 px-0" asChild>
              <Link href="https://www.quad9.net/" target="_blank" rel="noreferrer">
                Open Quad9 guide
                <ExternalLink className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          <div className="space-y-3 rounded-xl border border-border bg-card/80 px-4 py-4">
            <p className="text-sm font-semibold text-foreground">4. Install the small set of tools that matter</p>
            {recommendedBrowserTools(localBrowserInfo.browserName).map((tool) => (
              <div key={tool.name} className="rounded-lg border border-border/70 bg-background px-3 py-3">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-300" />
                    <p className="text-sm font-medium text-foreground">{tool.name}</p>
                  </div>
                  {tool.badge && <Badge variant="secondary" className="rounded-full">{tool.badge}</Badge>}
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{tool.why}</p>
                {tool.caution && (
                  <p className="mt-2 text-xs leading-relaxed text-amber-200/90">{tool.caution}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  {tool.links.map((link) => (
                    <Button key={link.href} variant="outline" size="sm" className="gap-2" asChild>
                      <Link href={link.href} target="_blank" rel="noreferrer">
                        {link.label}
                        <ExternalLink className="h-4 w-4" />
                      </Link>
                    </Button>
                  ))}
                </div>
              </div>
            ))}
            <div className="flex items-start gap-3 rounded-lg border border-border/70 bg-background px-3 py-3">
              <Shield className="mt-0.5 h-4 w-4 text-amber-300 shrink-0" />
              <p className="text-sm leading-relaxed text-muted-foreground">
                Keep the list short: one password manager extension, one strong blocker, then add advanced tools
                only if you understand the trade-offs.
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-primary/25 bg-primary/10 px-4 py-4">
            <p className="text-sm font-semibold text-foreground">Automated remediation requires the Companion</p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              A website cannot change browser policies, installed extensions, or system DNS directly. Install the
              Zima Companion above to enable deeper visibility. Automated remediation will be available in a future
              release.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
