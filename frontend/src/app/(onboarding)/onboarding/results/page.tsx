"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Activity,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { SeverityBadge } from "@/components/ui/SeverityBadge"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { useOnboardingStore } from "@/lib/store/onboarding"
import { api } from "@/lib/api/client"
import type { ScoreListResponse, FindingListResponse, ScanListResponse } from "@/types/api"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
]

function scoreGrade(score: number) {
  if (score >= 80) return { label: "Good", color: "text-emerald-400", ring: "#34d399" }
  if (score >= 60) return { label: "Fair", color: "text-sky-400", ring: "#38bdf8" }
  if (score >= 40) return { label: "At Risk", color: "text-amber-400", ring: "#fbbf24" }
  return { label: "Critical", color: "text-red-400", ring: "#f87171" }
}

function ScoreRing({ score }: { score: number }) {
  const r = 46
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const { color, ring } = scoreGrade(score)

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={112} height={112} className="-rotate-90">
        <circle cx={56} cy={56} r={r} fill="none" stroke="rgb(51,65,85)" strokeWidth={9} />
        <circle
          cx={56} cy={56} r={r} fill="none"
          stroke={ring} strokeWidth={9}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <span className={`absolute text-[28px] font-bold tabular-nums leading-none ${color}`}>
        {score}
      </span>
    </div>
  )
}

export default function ResultsPage() {
  const router = useRouter()
  const setCompleted = useOnboardingStore((s) => s.setCompleted)

  const { data: scoreData, isLoading: scoreLoading } = useQuery({
    queryKey: ["onboarding-scores"],
    queryFn: () => api.get<ScoreListResponse>("/scores"),
    retry: 2,
  })

  const { data: findingData, isLoading: findingsLoading } = useQuery({
    queryKey: ["onboarding-findings"],
    queryFn: () => api.get<FindingListResponse>("/findings/?limit=5"),
    retry: 2,
  })

  const { data: scanData, isLoading: scanLoading } = useQuery({
    queryKey: ["onboarding-scans"],
    queryFn: () => api.get<ScanListResponse>("/scans/?limit=1"),
    retry: 2,
  })

  const isLoading = scoreLoading || findingsLoading || scanLoading

  const primaryScore = scoreData?.scores.find((s) => s.domain === "identity")
  const score = primaryScore?.score ?? 0
  const { label: gradeLabel, color: gradeColor } = scoreGrade(score)
  const latestScan = scanData?.scans[0]
  const findings = findingData?.findings ?? []
  const openSignals = findingData?.signals_open ?? 0

  function handleDone() {
    setCompleted(true)
    router.push("/dashboard")
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={3} />
      </div>

      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">Your identity scan results</h1>
          <p className="text-slate-400 text-sm">
            Here&apos;s a summary of what we found. You can explore the full details on your dashboard.
          </p>
        </div>

        {/* ── Two-column: Score + Stats ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Identity Score */}
          <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-6 flex flex-col items-center justify-center">
            {isLoading || !primaryScore ? (
              <>
                <div className="w-28 h-28 rounded-full border-4 border-slate-700 animate-pulse" />
                <p className="text-slate-500 text-sm mt-3">
                  {isLoading ? "Loading results…" : "Computing score…"}
                </p>
              </>
            ) : (
              <>
                <ScoreRing score={score} />
                <p className={`text-lg font-semibold mt-3 ${gradeColor}`}>{gradeLabel}</p>
                <p className="text-xs text-slate-500 mt-1">Identity score</p>
              </>
            )}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-3">
            <StatBox
              label="Signals"
              value={latestScan?.signals_created ?? openSignals}
              icon={<Activity className="w-4 h-4 text-amber-400" />}
              color="text-amber-400"
              loading={isLoading}
            />
            <StatBox
              label="Findings"
              value={latestScan?.findings_created ?? findings.length}
              icon={<AlertTriangle className="w-4 h-4 text-red-400" />}
              color="text-red-400"
              loading={isLoading}
            />
            <StatBox
              label="Open signals"
              value={openSignals}
              icon={<ShieldAlert className="w-4 h-4 text-orange-400" />}
              color="text-orange-400"
              loading={isLoading}
            />
            <StatBox
              label="Domains checked"
              value={latestScan?.domains_run.length ?? 0}
              icon={<ShieldCheck className="w-4 h-4 text-emerald-400" />}
              color="text-emerald-400"
              loading={isLoading}
            />
          </div>
        </div>

        {/* ── Top findings ── */}
        {findings.length > 0 && (
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 mb-6">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Top findings
            </h2>
            <div className="space-y-2">
              {findings.map((f) => (
                <div
                  key={f.finding_id}
                  className="flex items-start justify-between gap-3 py-2 border-t border-slate-700/40 first:border-0"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200 truncate">{f.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{f.explanation}</p>
                  </div>
                  <SeverityBadge severity={f.severity} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Password manager prompt (generic) ── */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 mb-8">
          <div className="flex items-start gap-3">
            <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 mt-0.5">
              <CheckCircle2 className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                Recommended: use a password manager
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                A password manager generates and stores unique, strong passwords for every site — the single most
                effective step you can take to limit breach impact. Popular options include Bitwarden (free &amp; open
                source), 1Password, and Dashlane. Enable two-factor authentication on all critical accounts.
              </p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="flex justify-center">
          <Button size="lg" className="gap-2 px-10" onClick={handleDone}>
            Go to dashboard <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function StatBox({
  label,
  value,
  icon,
  color,
  loading = false,
}: {
  label: string
  value: number
  icon: React.ReactNode
  color: string
  loading?: boolean
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4 flex flex-col items-center justify-center text-center">
      <div className="mb-1">{icon}</div>
      {loading ? (
        <div className="h-8 w-10 rounded bg-slate-700 animate-pulse mb-0.5" />
      ) : (
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
      )}
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
    </div>
  )
}
