"use client"

import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  ArrowRight,
  Activity,
  Mailbox,
  Search,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { SeverityBadge } from "@/components/ui/SeverityBadge"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { api } from "@/lib/api/client"
import type { ScoreListResponse, FindingListResponse, ScanListResponse } from "@/types/api"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
  { label: "Import & Enrich" },
]

function scoreGrade(score: number) {
  if (score >= 80) return { label: "Good", color: "text-emerald-400", ring: "#34d399" }
  if (score >= 60) return { label: "Fair", color: "text-violet-400", ring: "#a78bfa" }
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

function dedupeBreaches(findings: FindingListResponse["findings"]) {
  const seen = new Set<string>()
  return findings
    .flatMap((finding) => finding.impacted_breaches)
    .filter((breach) => {
      const key = `${breach.email}:${breach.breach_name}:${breach.provider}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

export default function ResultsPage() {
  const router = useRouter()

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
  const surfacedBreaches = dedupeBreaches(findings).slice(0, 5)
  const openSignals = findingData?.signals_open ?? 0

  function handleDone() {
    router.push("/onboarding/import")
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={3} />
      </div>

      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">Your advisor has your first results</h1>
          <p className="text-slate-400 text-sm">
            Your first scan is finished. These are the issues Zima can already tie to verified assets.
            The next onboarding step brings in mailbox or vault evidence so the account map is based on your
            real footprint instead of guesswork.
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

        {surfacedBreaches.length > 0 && (
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 mb-6">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              Services already tied to exposed credentials
            </h2>
            <div className="space-y-2">
              {surfacedBreaches.map((breach) => (
                <div
                  key={`${breach.email}-${breach.breach_name}-${breach.provider}`}
                  className="flex items-start justify-between gap-3 py-2 border-t border-slate-700/40 first:border-0"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200 truncate">{breach.breach_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                      {breach.email} · {breach.provider}
                      {breach.breach_date ? ` · ${breach.breach_date}` : ""}
                    </p>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-1">{breach.summary}</p>
                  </div>
                  <SeverityBadge severity="high" />
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 mb-6">
          <h2 className="text-sm font-semibold text-white mb-3">Your guided plan</h2>
          <div className="space-y-3">
            <JourneyStep
              icon={<Mailbox className="w-4 h-4 text-violet-400" />}
              title="1. Bring in account evidence"
              description="Upload an .mbox export or supported vault export so Zima can identify registrations, password resets, and the services you actually use."
            />
            <JourneyStep
              icon={<Search className="w-4 h-4 text-violet-400" />}
              title="2. Review discovered accounts"
              description="We’ll turn those inbox clues into a cleaner account inventory so you can spot forgotten services and old login surfaces."
            />
            <JourneyStep
              icon={<ShieldAlert className="w-4 h-4 text-amber-400" />}
              title="3. Triage findings with context"
              description="Once your accounts are mapped, Zima can connect the breach evidence to the services you actually use and help you prioritise rotation and MFA."
            />
          </div>
        </div>

        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 mb-8">
          <div className="flex items-start gap-3">
            <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 mt-0.5">
              <Mailbox className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                What an mbox file actually is
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                An mbox file is a mailbox export. It contains the email messages that reveal where you signed up,
                which services sent password resets, and which accounts are still active. Zima uses it to find more
                accounts than breach data alone can show, so the rest of the security plan is based on your real
                footprint rather than guesswork.
              </p>
            </div>
          </div>
        </div>

        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 mb-8">
          <div className="flex items-start gap-3">
            <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 mt-0.5">
              <Search className="w-4 h-4 text-amber-300" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                Why you are not seeing the full account picture yet
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                The first scan can only work from verified assets and public evidence. We delay the full
                account-level view until the next step because that is where mailbox or vault evidence tells us
                which services are actually yours. Without that extra context, the dashboard would look complete
                when it is still missing part of the map.
              </p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="flex justify-center">
          <Button size="lg" className="gap-2 px-10" onClick={handleDone}>
            Continue with guided import <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function JourneyStep({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="shrink-0 flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900/60 border border-slate-700/60">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-slate-200">{title}</p>
        <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{description}</p>
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
