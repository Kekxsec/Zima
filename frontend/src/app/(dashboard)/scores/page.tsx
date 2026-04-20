"use client"

import Link from "next/link"
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { format, parseISO } from "date-fns"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts"
import { BarChart2, Minus, TrendingDown, TrendingUp } from "lucide-react"
import { api } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { hasCompletedBrowserReview } from "@/lib/browserReview"
import { cn } from "@/lib/utils"
import type { AccountResponse, FindingListResponse, ScoreHistoryResponse, ScoreListResponse, ScanListResponse } from "@/types/api"

function scoreColor(score: number) {
  if (score >= 80) return "#22c55e"
  if (score >= 60) return "#0ea5e9"
  if (score >= 40) return "#f59e0b"
  return "#ef4444"
}

function scoreGrade(score: number) {
  if (score >= 80) return { label: "Good", text: "text-emerald-200", bg: "bg-emerald-500/10", border: "border-emerald-500/25" }
  if (score >= 60) return { label: "Fair", text: "text-violet-200", bg: "bg-violet-500/10", border: "border-violet-500/25" }
  if (score >= 40) return { label: "At Risk", text: "text-amber-200", bg: "bg-amber-500/10", border: "border-amber-500/25" }
  return { label: "Critical", text: "text-red-200", bg: "bg-red-500/10", border: "border-red-500/25" }
}

function ScoreHistoryChart({ domain }: { domain: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["score-history", domain],
    queryFn: () => api.get<ScoreHistoryResponse>(`/scores/${domain}/history`),
  })

  if (isLoading) return <Skeleton className="h-52 w-full" />

  const history = data?.history ?? []
  if (history.length < 2) {
    return (
      <div className="flex items-center justify-center py-10 text-sm text-muted-foreground">
        We need more than one scan before we can show a trend here.
      </div>
    )
  }

  const chartData = [...history]
    .sort((a, b) => a.calculated_at.localeCompare(b.calculated_at))
    .map((entry) => ({
      date: format(parseISO(entry.calculated_at), "MMM d"),
      score: entry.score,
    }))

  const latest = chartData[chartData.length - 1]?.score ?? 0
  const previous = chartData[chartData.length - 2]?.score ?? latest
  const delta = latest - previous
  const TrendIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus
  const trendColor = delta > 0 ? "text-green-500" : delta < 0 ? "text-red-500" : "text-muted-foreground"

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <TrendIcon className={cn("h-4 w-4", trendColor)} />
        <span className={cn("text-sm font-medium", trendColor)}>
          {delta === 0 ? "No change since the last scan" : `${delta > 0 ? "+" : ""}${delta} since the last scan`}
        </span>
      </div>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              tickLine={false}
              axisLine={false}
            />
            <ReferenceLine y={80} stroke="#22c55e" strokeDasharray="4 4" strokeOpacity={0.4} />
            <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="4 4" strokeOpacity={0.4} />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: 12,
              }}
              formatter={(value) => [value, "Score"]}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke={scoreColor(latest)}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default function ScoresPage() {
  const { data: accountData } = useQuery({
    queryKey: ["scores-account"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })
  const { data: findingsData } = useQuery({
    queryKey: ["scores-open-findings"],
    queryFn: () => api.get<FindingListResponse>("/findings?limit=1&filter_status=open"),
  })
  const { data: scansData } = useQuery({
    queryKey: ["scores-scans"],
    queryFn: () => api.get<ScanListResponse>("/scans?limit=10"),
  })
  const { data, isLoading } = useQuery({
    queryKey: ["scores"],
    queryFn: () => api.get<ScoreListResponse>("/scores"),
  })

  const scores = data?.scores ?? []
  const [activeTab, setActiveTab] = useState<string | undefined>(undefined)
  const currentDomain = activeTab ?? scores[0]?.domain
  const primaryScore = scores.find((score) => score.domain === "identity") ?? scores[0]
  const hasBrowserSetup = hasCompletedBrowserReview(accountData?.assets ?? [], scansData?.scans ?? [])
  const openFindings = findingsData?.total ?? 0

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Check your progress</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          This page is only a later health check. Use it after accounts, priorities, and browser review are in
          better shape. Higher is better, but treat it as a rough trend, not a verdict.
        </p>
      </div>

      {openFindings > 0 && (
        <Card className="border-primary/25 bg-primary/10">
          <CardContent className="flex items-start justify-between gap-4 p-5 flex-wrap">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">Finish the priority issues first</p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                Progress is more meaningful after you work through the current breached services and urgent risks.
              </p>
            </div>
            <Button className="gap-2" asChild>
              <Link href="/findings">Go to priorities</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {openFindings === 0 && !hasBrowserSetup && (
        <Card className="border-primary/25 bg-primary/10">
          <CardContent className="flex items-start justify-between gap-4 p-5 flex-wrap">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">Run the browser review before using this page</p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                The next real stage is securing the browser you use every day. Add your browser details, review
                extensions, and run a browser scan first.
              </p>
            </div>
            <Button className="gap-2" asChild>
              <Link href="/browser">Open browser review</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Skeleton className="h-36 w-full" />
      ) : primaryScore ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Your latest security check</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-end gap-3">
              <p className="text-5xl font-bold" style={{ color: scoreColor(primaryScore.score) }}>
                {primaryScore.score}
              </p>
              <span
                className={cn(
                  "mb-1 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                  scoreGrade(primaryScore.score).bg,
                  scoreGrade(primaryScore.score).text,
                  scoreGrade(primaryScore.score).border,
                )}
              >
                {scoreGrade(primaryScore.score).label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              This is your current identity progress score. It should improve after you fix breached services,
              organise accounts in your password manager, and reduce old account exposure.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, index) => (
            <Skeleton key={index} className="h-28 w-full" />
          ))}
        </div>
      ) : scores.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <BarChart2 className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="font-semibold">No progress score yet</p>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Run another scan after you make changes and this page will become more useful.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {scores.map((score) => {
              const grade = scoreGrade(score.score)
              return (
                <Card
                  key={score.domain}
                  className={cn(
                    "cursor-pointer border-l-4 transition-all hover:shadow-md",
                    currentDomain === score.domain ? "ring-2 ring-primary/20" : "",
                  )}
                  style={{ borderLeftColor: scoreColor(score.score) }}
                  onClick={() => setActiveTab(score.domain)}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 space-y-1">
                        <p className="truncate text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                          {score.domain}
                        </p>
                        <p
                          className="text-4xl font-bold leading-none tabular-nums"
                          style={{ color: scoreColor(score.score) }}
                        >
                          {score.score}
                        </p>
                        <span
                          className={cn(
                            "mt-1 inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                            grade.bg,
                            grade.text,
                            grade.border,
                          )}
                        >
                          {grade.label}
                        </span>
                      </div>
                      <div className="mt-0.5 shrink-0 space-y-0.5 text-right">
                        <p className="text-xs text-muted-foreground">{score.signal_count} signals</p>
                        <p className="text-xs text-muted-foreground">
                          {format(parseISO(score.calculated_at), "MMM d")}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Progress over time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs value={currentDomain} onValueChange={setActiveTab}>
                {scores.length > 1 && (
                  <TabsList className="mb-4">
                    {scores.map((score) => (
                      <TabsTrigger key={score.domain} value={score.domain} className="capitalize text-xs">
                        {score.domain}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                )}
                {scores.map((score) => (
                  <TabsContent key={score.domain} value={score.domain}>
                    <ScoreHistoryChart domain={score.domain} />
                  </TabsContent>
                ))}
              </Tabs>
            </CardContent>
          </Card>
        </>
      )}

    </div>
  )
}
