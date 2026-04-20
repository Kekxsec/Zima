"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Shield, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { useOnboardingStore } from "@/lib/store/onboarding"
import { api, ApiRequestError } from "@/lib/api/client"
import type {
  AssetDeclarePayload,
  AssetOut,
  Scan,
  ScanEvent,
  ScanEventListResponse,
} from "@/types/api"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
  { label: "Import & Enrich" },
]

const SCAN_STAGES = [
  {
    key: "queued",
    label: "Preparing scan",
    detail: "Creating the scan job and confirming which verified assets can be checked.",
  },
  {
    key: "modules",
    label: "Running source checks",
    detail: "Providers are checking breach, exposure, and account-discovery sources.",
  },
  {
    key: "correlation",
    label: "Correlating signals",
    detail: "Turning raw signals into grouped findings and prioritised issues.",
  },
  {
    key: "scoring",
    label: "Updating score",
    detail: "Calculating your latest identity score from the current scan results.",
  },
  {
    key: "notifications",
    label: "Finalising results",
    detail: "Writing the final scan state and preparing anything that needs to be surfaced next.",
  },
]

const STAGE_PROGRESS: Record<string, number> = {
  queued: 8,
  modules: 42,
  correlation: 68,
  scoring: 84,
  notifications: 94,
  completed: 100,
}

type ScanState = "triggering" | "running" | "completed" | "failed"
type StageKey = (typeof SCAN_STAGES)[number]["key"] | "completed"

function formatDomainStage(rawStage: string) {
  const domain = rawStage.replace(/^domain:/, "")
  return domain
    .split("_")
    .join(" ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function getStageMeta(events: ScanEvent[], scanState: ScanState) {
  let stage: StageKey = scanState === "completed" ? "completed" : "queued"
  let detail = SCAN_STAGES[0].detail

  for (const event of events) {
    if (event.event_type === "scan_completed") {
      stage = "completed"
      detail = "All checks have finished and the results are being prepared."
      continue
    }

    if (event.event_type !== "stage_started") continue

    const rawStage = typeof event.data.stage === "string" ? event.data.stage : ""
    if (rawStage === "modules") {
      stage = "modules"
      detail = SCAN_STAGES[1].detail
      continue
    }
    if (rawStage.startsWith("domain:")) {
      stage = "modules"
      detail = `Running ${formatDomainStage(rawStage)} checks.`
      continue
    }
    if (rawStage === "correlation") {
      stage = "correlation"
      detail = SCAN_STAGES[2].detail
      continue
    }
    if (rawStage === "scoring") {
      stage = "scoring"
      detail = SCAN_STAGES[3].detail
      continue
    }
    if (rawStage === "notifications") {
      stage = "notifications"
      detail = SCAN_STAGES[4].detail
      continue
    }
    if (rawStage === "post_import_identity_review") {
      stage = "notifications"
      detail =
        "Running final data quality checks on identified accounts to improve service matching."
    }
  }

  return {
    stage,
    detail,
    progressPercent:
      scanState === "completed" ? 100 : STAGE_PROGRESS[stage],
  }
}

export default function ScanPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const setScanId = useOnboardingStore((s) => s.setScanId)
  const setCompleted = useOnboardingStore((s) => s.setCompleted)
  const identity = useOnboardingStore((s) => s.identity)
  const scanIdFromStore = useOnboardingStore((s) => s.scanId)
  const nextPath =
    searchParams.get("next") === "import-complete"
      ? "/onboarding/import/complete"
      : "/onboarding/results"
  const isImportFollowUp = nextPath === "/onboarding/import/complete"

  const [scanState, setScanState] = useState<ScanState>("triggering")
  const [error, setError] = useState<string | null>(null)
  const [scan, setScan] = useState<Scan | null>(null)
  const [scanEvents, setScanEvents] = useState<ScanEvent[]>([])

  const startedScanPromiseRef = useRef<Promise<Scan> | null>(null)
  const stageMeta = getStageMeta(scanEvents, scanState)
  const activeVisibleStep =
    scanState === "completed"
      ? SCAN_STAGES.length - 1
      : Math.max(
          0,
          SCAN_STAGES.findIndex((stage) => stage.key === stageMeta.stage),
        )

  // Trigger scan then poll.
  useEffect(() => {
    let cancelled = false
    let pollInterval: ReturnType<typeof setInterval> | null = null

    async function requestScan(): Promise<Scan> {
      const declarationTask = identity
        ? Promise.allSettled(
            Array.from(
              new Set(
                identity.usernames
                  .map((u) => u.trim().toLowerCase())
                  .filter(Boolean),
              ),
            ).map((value) =>
              api.post<AssetOut>("/assets", {
                entity_type: "username",
                value,
              } satisfies AssetDeclarePayload),
            ),
          )
        : null

      const triggered = await api.post<Scan>("/scans", { tier: "standard" })
      if (declarationTask) {
        const results = await declarationTask
        const failed = results.filter((r) => r.status === "rejected")
        if (failed.length > 0) {
          console.warn(`[scan] ${failed.length} username declaration(s) failed`)
        }
      }

      setScanId(triggered.id)
      return triggered
    }

    async function loadOrCreateScan(): Promise<Scan> {
      if (scanIdFromStore) {
        return api.get<Scan>(`/scans/${scanIdFromStore}`)
      }

      if (!startedScanPromiseRef.current) {
        startedScanPromiseRef.current = requestScan().catch((err) => {
          startedScanPromiseRef.current = null
          throw err
        })
      }

      return startedScanPromiseRef.current
    }

    async function applyScanState(latest: Scan) {
      setScan(latest)
      setScanId(latest.id)

      if (latest.status === "completed") {
        setScanState("completed")
        setCompleted(true)
        return true
      }

      if (latest.status === "failed") {
        setScanState("failed")
        setError(latest.error_detail ?? "Scan failed — please try again.")
        return true
      }

      setScanState("running")
      return false
    }

    async function loadScanEvents(scanId: string) {
      const eventData = await api.get<ScanEventListResponse>(`/scans/${scanId}/events`)
      if (!cancelled) {
        setScanEvents(eventData.events)
      }
    }

    async function triggerAndPoll() {
      try {
        const triggered = await loadOrCreateScan()
        if (cancelled) return
        await loadScanEvents(triggered.id)
        const finishedImmediately = await applyScanState(triggered)
        if (finishedImmediately || cancelled) {
          return
        }

        // Poll every 4 s — status plus event log. This keeps the UI aligned
        // with backend stages rather than a timer.
        pollInterval = setInterval(async () => {
          try {
            const [latest, eventData] = await Promise.all([
              api.get<Scan>(`/scans/${triggered.id}`),
              api.get<ScanEventListResponse>(`/scans/${triggered.id}/events`),
            ])
            if (cancelled) return
            setScanEvents(eventData.events)
            const finished = await applyScanState(latest)
            if (finished) {
              clearInterval(pollInterval!)
            }
          } catch (pollErr) {
            if (cancelled) return
            clearInterval(pollInterval!)
            setScanState("failed")
            if (pollErr instanceof ApiRequestError && (pollErr.status === 401 || pollErr.status === 403)) {
              setError("Your session expired. Please sign in again.")
            } else {
              setError(pollErr instanceof ApiRequestError ? pollErr.detail : "Scan check failed. Please refresh.")
            }
          }
        }, 4000)
      } catch (err) {
        if (cancelled) return
        setScanState("failed")
        setError(err instanceof ApiRequestError ? err.detail : "Could not start scan.")
      }
    }

    triggerAndPoll()

    return () => {
      cancelled = true
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [identity, scanIdFromStore, setCompleted, setScanId])

  useEffect(() => {
    if (scanState === "completed") {
      const t = setTimeout(() => router.push(nextPath), 1200)
      return () => clearTimeout(t)
    }
  }, [scanState, router, nextPath])

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={nextPath === "/onboarding/import/complete" ? 4 : 2} />
      </div>

      <div className="w-full max-w-lg">
        <div className="text-center mb-10">
          <div
            className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-5 ${
              scanState === "failed"
                ? "bg-red-500/10 border border-red-500/20"
                : scanState === "completed"
                ? "bg-emerald-500/10 border border-emerald-500/20"
                : "bg-primary/10 border border-primary/20"
            }`}
          >
            {scanState === "failed" ? (
              <AlertCircle className="w-8 h-8 text-red-400" />
            ) : scanState === "completed" ? (
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            ) : (
              <Shield className="w-8 h-8 text-primary animate-pulse" />
            )}
          </div>

          <h1 className="text-2xl font-bold text-white mb-2">
            {scanState === "triggering" &&
              (isImportFollowUp ? "Starting follow-up scan…" : "Starting your scan…")}
            {scanState === "running" &&
              (isImportFollowUp
                ? "Applying imported account evidence…"
                : "Scanning your identity…")}
            {scanState === "completed" && "Scan complete"}
            {scanState === "failed" && "Scan failed"}
          </h1>
          <p className="text-slate-400 text-sm">
            {scanState === "failed"
              ? error ?? "An unexpected error occurred."
              : scanState === "completed"
              ? "All checks complete. Preparing your results…"
              : isImportFollowUp
              ? "This follow-up scan runs provider checks, final data quality checks on identified accounts, correlation, and scoring so your imported evidence is reflected in findings."
              : "This status reflects live backend stages rather than a time estimate. Stay on this page and we’ll move you forward as soon as the scan finishes."}
          </p>
        </div>

        {scanState !== "failed" && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span>{scanState === "completed" ? "Complete" : "Backend stage progress"}</span>
              <span>{stageMeta.progressPercent}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-800/70 border border-slate-700/60 overflow-hidden">
              <div
                className={`h-full transition-all duration-700 ${
                  scanState === "completed"
                    ? "bg-emerald-400"
                    : "bg-primary"
                }`}
                style={{ width: `${stageMeta.progressPercent}%` }}
              />
            </div>
            {scanState !== "completed" && (
              <p className="mt-2 text-xs text-slate-500">{stageMeta.detail}</p>
            )}
          </div>
        )}

        {scanState !== "failed" && (
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 space-y-1">
            {SCAN_STAGES.map((step, i) => {
              const isDone =
                scanState === "completed"
                  ? true
                  : i < activeVisibleStep
              const isActive = !isDone && i === activeVisibleStep

              return (
                <div
                  key={step.key}
                  className={`flex items-start gap-3 rounded-lg px-2 py-2 transition-colors ${
                    isActive ? "bg-slate-700/40" : ""
                  }`}
                >
                  <div className="mt-0.5 shrink-0 w-4 h-4 flex items-center justify-center">
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : isActive ? (
                      <Loader2 className="w-4 h-4 text-primary animate-spin" />
                    ) : (
                      <div className="w-3 h-3 rounded-full border border-slate-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm font-medium leading-tight ${
                        isDone
                          ? "text-slate-400"
                          : isActive
                          ? "text-white"
                          : "text-slate-600"
                      }`}
                    >
                      {step.label}
                    </p>
                    {isActive && (
                      <p className="text-xs text-slate-500 mt-0.5">
                        {step.key === stageMeta.stage ? stageMeta.detail : step.detail}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Stats row once scan data is available */}
        {scan && scan.status === "completed" && (
          <div className="grid grid-cols-2 gap-3 mt-4">
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-white">{scan.signals_created}</p>
              <p className="text-xs text-slate-400 mt-0.5">Signals found</p>
            </div>
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-white">{scan.findings_created}</p>
              <p className="text-xs text-slate-400 mt-0.5">Findings raised</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
