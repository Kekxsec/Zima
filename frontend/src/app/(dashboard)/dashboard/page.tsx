"use client"

import { useQuery } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import {
  AlertTriangle,
  ShieldCheck,
  ScanLine,
  TrendingUp,
  RefreshCw,
  ArrowRight,
  Activity,
  Mailbox,
} from "lucide-react"
import Link from "next/link"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts"
import { format, parseISO } from "date-fns"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { SeverityBadge } from "@/components/ui/SeverityBadge"
import { cn } from "@/lib/utils"
import type {
  ScoreListResponse,
  FindingListResponse,
  ScanListResponse,
  ScoreHistoryResponse,
  DiscoveredAccountListResponse,
} from "@/types/api"

function scoreGrade(score: number) {
  if (score >= 80) return { label: "Good",    color: "text-green-600" }
  if (score >= 60) return { label: "Fair",    color: "text-sky-600" }
  if (score >= 40) return { label: "At Risk", color: "text-amber-600" }
  return             { label: "Critical",  color: "text-red-600" }
}

function scoreStroke(score: number): string {
  if (score >= 80) return "#22c55e"
  if (score >= 60) return "#0ea5e9"
  if (score >= 40) return "#f59e0b"
  return "#ef4444"
}

function ScoreRing({ score }: { score: number }) {
  const r = 46
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const color = scoreStroke(score)

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={112} height={112} className="-rotate-90">
        <circle cx={56} cy={56} r={r} fill="none" stroke="hsl(var(--border))" strokeWidth={9} />
        <circle
          cx={56} cy={56} r={r} fill="none"
          stroke={color} strokeWidth={9}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <span className="absolute text-[28px] font-bold tabular-nums leading-none" style={{ color }}>
        {score}
      </span>
    </div>
  )
}

function MetricCard({
  label,
  value,
  sublabel,
  icon: Icon,
  iconColor,
  iconBg,
  loading,
}: {
  label: string
  value: React.ReactNode
  sublabel?: string
  icon: React.ElementType
  iconColor: string
  iconBg: string
  loading?: boolean
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {label}
            </p>
            {loading ? (
              <Skeleton className="mt-1 h-7 w-14" />
            ) : (
              <p className="text-2xl font-bold tabular-nums text-foreground">{value}</p>
            )}
            {sublabel && (
              <p className="text-xs text-muted-foreground truncate">{sublabel}</p>
            )}
          </div>
          <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", iconBg)}>
            <Icon className={cn("h-5 w-5", iconColor)} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const router = useRouter()

  const { data: scoresData, isLoading: scoresLoading } = useQuery({
    queryKey: ["scores"],
    queryFn: () => api.get<ScoreListResponse>("/scores"),
  })

  const { data: findingsData, isLoading: findingsLoading } = useQuery({
    queryKey: ["findings", { limit: 5, status: "open" }],
    queryFn: () => api.get<FindingListResponse>("/findings?limit=5&status=open"),
    retry: (count, err) => !(err instanceof ApiRequestError && err.status === 401) && count < 2,
  })

  const { data: scansData } = useQuery({
    queryKey: ["scans", { limit: 1 }],
    queryFn: () => api.get<ScanListResponse>("/scans?limit=1"),
  })

  const { data: accountsData } = useQuery({
    queryKey: ["discovered-accounts-count"],
    queryFn: () => api.get<DiscoveredAccountListResponse>("/email-accounts/accounts?limit=1"),
  })

  const primaryScore = scoresData?.scores?.[0]
  const identityDomain = primaryScore?.domain ?? "identity"

  const { data: historyData } = useQuery({
    queryKey: ["score-history", identityDomain],
    queryFn: () => api.get<ScoreHistoryResponse>(`/scores/${identityDomain}/history`),
    enabled: !!primaryScore,
  })

  const chartData = historyData?.history
    .slice(-30)
    .sort((a, b) => a.calculated_at.localeCompare(b.calculated_at))
    .map((h) => ({
      date: format(parseISO(h.calculated_at), "MMM d"),
      score: h.score,
    }))

  const lastScan = scansData?.scans?.[0]
  const totalAccounts = accountsData?.total ?? 0
  const openFindings = findingsData?.findings ?? []
  const totalOpen = findingsData?.total ?? 0
  const signalCount = primaryScore?.signal_count ?? 0
  const grade = primaryScore ? scoreGrade(primaryScore.score) : null

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Identity security posture at a glance
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Score ring card */}
        <Card className="col-span-2 lg:col-span-1">
          <CardContent className="flex flex-col items-center justify-center py-5 px-4 gap-1">
            {scoresLoading ? (
              <Skeleton className="h-[112px] w-[112px] rounded-full" />
            ) : primaryScore ? (
              <>
                <ScoreRing score={primaryScore.score} />
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mt-1.5">
                  Identity Score
                </p>
                {grade && (
                  <span className={cn("text-xs font-semibold", grade.color)}>{grade.label}</span>
                )}
              </>
            ) : (
              <>
                <div className="flex h-[112px] w-[112px] items-center justify-center rounded-full border-[9px] border-border">
                  <span className="text-2xl font-bold text-muted-foreground">—</span>
                </div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mt-1.5">
                  Identity Score
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <MetricCard
          label="Open Findings"
          value={totalOpen}
          sublabel={totalOpen === 0 ? "No active threats" : `${totalOpen} need review`}
          icon={AlertTriangle}
          iconColor={totalOpen > 0 ? "text-red-500" : "text-green-500"}
          iconBg={totalOpen > 0 ? "bg-red-50" : "bg-green-50"}
          loading={findingsLoading}
        />

        <MetricCard
          label="Signals Detected"
          value={signalCount}
          sublabel="Across all providers"
          icon={Activity}
          iconColor="text-amber-500"
          iconBg="bg-amber-50"
          loading={scoresLoading}
        />

        <Link href="/accounts" className="block">
          <MetricCard
            label="Accounts Found"
            value={totalAccounts}
            sublabel={totalAccounts === 0 ? "Upload mbox to discover" : "Tap to review"}
            icon={Mailbox}
            iconColor="text-violet-500"
            iconBg="bg-violet-50"
          />
        </Link>

        {/* Last scan card */}
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Last Scan
                </p>
                {lastScan ? (
                  <>
                    <p className="text-sm font-bold capitalize text-foreground">{lastScan.status}</p>
                    <p className="text-xs text-muted-foreground">
                      {lastScan.completed_at
                        ? format(parseISO(lastScan.completed_at), "MMM d, HH:mm")
                        : lastScan.started_at
                        ? format(parseISO(lastScan.started_at), "MMM d, HH:mm")
                        : "—"}
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">Never run</p>
                )}
              </div>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sky-50">
                <ScanLine className="h-5 w-5 text-sky-500" />
              </div>
            </div>
            <div className="mt-3">
              <Button size="sm" variant="outline" className="w-full gap-1.5 text-xs" asChild>
                <Link href="/scans">
                  <RefreshCw className="h-3 w-3" /> New scan
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Score trend */}
      {chartData && chartData.length >= 2 ? (
        <Card>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              30-Day Score Trend
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5">
            <div className="h-36">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="hsl(var(--primary))" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis domain={[0, 100]} hide />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: 12,
                    }}
                    formatter={(val) => [val, "Score"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    fill="url(#scoreGrad)"
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      ) : !scoresLoading && primaryScore ? (
        <Card className="border-dashed">
          <CardContent className="flex items-center justify-center py-6 text-sm text-muted-foreground">
            Run more scans to see your score trend.
          </CardContent>
        </Card>
      ) : null}

      {/* Recent findings */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between px-5 pt-5 pb-0">
          <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Recent Findings
          </CardTitle>
          <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs" asChild>
            <Link href="/findings">
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent className="px-5 pb-5 pt-3">
          {findingsLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-11 w-full" />
              ))}
            </div>
          ) : openFindings.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-50">
                <ShieldCheck className="h-5 w-5 text-green-500" />
              </div>
              <p className="text-sm font-medium">No open findings</p>
              <p className="text-xs text-muted-foreground">Your identity looks clean.</p>
            </div>
          ) : (
            <div className="divide-y divide-border -mx-1">
              {openFindings.map((f) => (
                <div
                  key={f.finding_id}
                  className="flex items-center gap-3 py-2.5 px-1 cursor-pointer hover:bg-muted/40 rounded-lg transition-colors"
                  onClick={() => router.push("/findings")}
                >
                  <SeverityBadge severity={f.severity} className="w-[72px] justify-center" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium leading-snug truncate">{f.title}</p>
                    <p className="text-xs text-muted-foreground truncate">{f.rule_name}</p>
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0 tabular-nums">
                    {Math.round(f.confidence * 100)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Empty state CTA */}
      {!scoresLoading && !primaryScore && (
        <Card className="border-dashed border-primary/30">
          <CardContent className="flex flex-col items-center py-10 text-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
              <TrendingUp className="h-7 w-7 text-primary" />
            </div>
            <div>
              <p className="font-semibold">Run your first scan</p>
              <p className="text-sm text-muted-foreground mt-1 max-w-xs mx-auto">
                Zima will analyse your digital footprint and generate an identity risk score.
              </p>
            </div>
            <Button asChild size="sm">
              <Link href="/scans">Start scan</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
