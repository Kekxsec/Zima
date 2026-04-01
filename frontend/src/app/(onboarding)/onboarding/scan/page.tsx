"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { Shield, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { useOnboardingStore } from "@/lib/store/onboarding"
import { api, ApiRequestError } from "@/lib/api/client"
import type { AssetDeclarePayload, AssetOut, Scan } from "@/types/api"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
]

const SCAN_STEPS = [
  {
    key: "prepare",
    label: "Preparing scan",
    detail: "Verifying assets and initialising scan profile…",
  },
  {
    key: "breach",
    label: "Checking breach databases",
    detail: "Querying HIBP, DeHashed, and LeakCheck for your email addresses…",
  },
  {
    key: "stealer",
    label: "Scanning stealer logs",
    detail: "Searching infostealer logs for captured credentials and cookies…",
  },
  {
    key: "credential",
    label: "Checking credential exposure",
    detail: "Looking for leaked usernames and passwords on paste sites…",
  },
  {
    key: "username",
    label: "Scanning username presence",
    detail: "Checking your handles across 100+ platforms for public exposure…",
  },
  {
    key: "phone",
    label: "Checking phone number",
    detail: "Validating carrier, country, and public CNAM records…",
  },
  {
    key: "reputation",
    label: "Analysing email reputation",
    detail: "Checking sender reputation, blocklists, and risk signals…",
  },
  {
    key: "accounts",
    label: "Discovering linked accounts",
    detail: "Finding services registered to your email addresses…",
  },
  {
    key: "scoring",
    label: "Calculating identity score",
    detail: "Aggregating findings and computing your risk score…",
  },
]

// The scoring step is the final one — it only completes when the scan is done
const SCORING_IDX = SCAN_STEPS.length - 1
// Auto-advance stops one step before scoring, so scoring only ticks on actual completion
const AUTO_ADVANCE_MAX = SCORING_IDX - 1
// Spread the auto-advance steps across ~72 s (matches typical scan duration)
const STEP_INTERVAL_MS = 9000

type ScanState = "triggering" | "running" | "completed" | "failed"

export default function ScanPage() {
  const router = useRouter()
  const setScanId = useOnboardingStore((s) => s.setScanId)
  const setCompleted = useOnboardingStore((s) => s.setCompleted)
  const identity = useOnboardingStore((s) => s.identity)

  const [scanState, setScanState] = useState<ScanState>("triggering")
  const [error, setError] = useState<string | null>(null)
  const [visibleStep, setVisibleStep] = useState(0)
  const [scan, setScan] = useState<Scan | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const stepTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const hasFiredRef = useRef(false)

  // Auto-advance through steps 0 → AUTO_ADVANCE_MAX at STEP_INTERVAL_MS each.
  // Stops before the scoring step so it doesn't falsely imply completion.
  useEffect(() => {
    stepTimerRef.current = setInterval(() => {
      setVisibleStep((prev) => {
        if (prev < AUTO_ADVANCE_MAX) return prev + 1
        clearInterval(stepTimerRef.current!)
        return prev
      })
    }, STEP_INTERVAL_MS)
    return () => clearInterval(stepTimerRef.current!)
  }, [])

  // When the scan actually completes, advance to the scoring step
  useEffect(() => {
    if (scanState === "completed") {
      setVisibleStep(SCORING_IDX)
    }
  }, [scanState])

  // Trigger scan then poll
  useEffect(() => {
    if (hasFiredRef.current) return
    hasFiredRef.current = true

    let cancelled = false

    async function triggerAndPoll() {
      try {
        // Submit declared assets (phone, usernames) before triggering the scan
        if (identity) {
          const declarations: AssetDeclarePayload[] = []
          if (identity.phone?.trim()) {
            declarations.push({ entity_type: "phone_number", value: identity.phone.trim() })
          }
          for (const u of identity.usernames) {
            if (u.trim()) declarations.push({ entity_type: "username", value: u.trim() })
          }
          await Promise.allSettled(
            declarations.map((d) => api.post<AssetOut>("/assets/", d)),
          )
        }

        // Trigger scan
        const triggered = await api.post<Scan>("/scans/", { tier: "standard" })
        if (cancelled) return

        setScanId(triggered.id)
        setScanState("running")

        if (triggered.status === "completed") {
          setScan(triggered)
          setScanState("completed")
          setCompleted(true)
          return
        }

        // Poll every 4 s — use the individual endpoint so stale detection fires
        pollRef.current = setInterval(async () => {
          try {
            const latest = await api.get<Scan>(`/scans/${triggered.id}`)
            if (cancelled) return
            setScan(latest)

            if (latest.status === "completed") {
              clearInterval(pollRef.current!)
              setScanState("completed")
              setCompleted(true)
            } else if (latest.status === "failed") {
              clearInterval(pollRef.current!)
              setScanState("failed")
              setError(latest.error_detail ?? "Scan failed — please try again.")
            }
          } catch (pollErr) {
            if (cancelled) return
            if (pollErr instanceof ApiRequestError && (pollErr.status === 401 || pollErr.status === 403)) {
              clearInterval(pollRef.current!)
              setScanState("failed")
              setError("Your session expired. Please sign in again.")
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
      clearInterval(pollRef.current!)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Navigate after scoring step becomes visible and scan is done
  useEffect(() => {
    if (scanState === "completed" && visibleStep >= SCORING_IDX) {
      const t = setTimeout(() => router.push("/onboarding/results"), 1200)
      return () => clearTimeout(t)
    }
  }, [scanState, visibleStep, router])

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={2} />
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
            {scanState === "triggering" && "Starting your scan…"}
            {scanState === "running" && "Scanning your identity…"}
            {scanState === "completed" && "Scan complete"}
            {scanState === "failed" && "Scan failed"}
          </h1>
          <p className="text-slate-400 text-sm">
            {scanState === "failed"
              ? error ?? "An unexpected error occurred."
              : scanState === "completed"
              ? "All checks complete. Preparing your results…"
              : "This usually takes 60–90 seconds. Sit tight while we check multiple sources."}
          </p>
        </div>

        {/* Scan step list */}
        {scanState !== "failed" && (
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 space-y-1">
            {SCAN_STEPS.map((step, i) => {
              const isDone =
                scanState === "completed"
                  ? true
                  : i < visibleStep
              const isActive = !isDone && i === visibleStep

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
                      <p className="text-xs text-slate-500 mt-0.5">{step.detail}</p>
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
