"use client"

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
import { BarChart2, TrendingUp, TrendingDown, Minus } from "lucide-react"
import { api } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import type { ScoreListResponse, ScoreHistoryResponse } from "@/types/api"

function scoreColor(score: number) {
  if (score >= 80) return "#22c55e"
  if (score >= 60) return "#0ea5e9"
  if (score >= 40) return "#f59e0b"
  return "#ef4444"
}

function scoreGrade(score: number) {
  if (score >= 80) return { label: "Good",     text: "text-green-600", bg: "bg-green-50",  border: "border-green-200" }
  if (score >= 60) return { label: "Fair",     text: "text-sky-600",   bg: "bg-sky-50",    border: "border-sky-200" }
  if (score >= 40) return { label: "At Risk",  text: "text-amber-600", bg: "bg-amber-50",  border: "border-amber-200" }
  return             { label: "Critical",   text: "text-red-600",   bg: "bg-red-50",    border: "border-red-200" }
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
        Not enough data yet — scores accumulate after multiple scans.
      </div>
    )
  }

  const chartData = [...history]
    .sort((a, b) => a.calculated_at.localeCompare(b.calculated_at))
    .map((h) => ({
      date: format(parseISO(h.calculated_at), "MMM d"),
      score: h.score,
      signals: h.signal_count,
    }))

  const latest = chartData[chartData.length - 1]?.score ?? 0
  const prev = chartData[chartData.length - 2]?.score ?? latest
  const delta = latest - prev
  const TrendIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus
  const trendColor = delta > 0 ? "text-green-500" : delta < 0 ? "text-red-500" : "text-muted-foreground"

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <TrendIcon className={cn("h-4 w-4", trendColor)} />
        <span className={cn("text-sm font-medium", trendColor)}>
          {delta === 0 ? "No change" : `${delta > 0 ? "+" : ""}${delta} from last score`}
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
              formatter={(val) => [val, "Score"]}
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
  const { data, isLoading } = useQuery({
    queryKey: ["scores"],
    queryFn: () => api.get<ScoreListResponse>("/scores"),
  })

  const scores = data?.scores ?? []
  const [activeTab, setActiveTab] = useState<string | undefined>(undefined)
  const currentDomain = activeTab ?? scores[0]?.domain

  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Scores</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Identity risk scores by domain, updated after each scan
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}
        </div>
      ) : scores.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-14 text-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <BarChart2 className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="font-semibold">No scores yet</p>
              <p className="text-sm text-muted-foreground mt-0.5">
                Run a scan to generate your identity score.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Score cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {scores.map((s) => {
              const grade = scoreGrade(s.score)
              return (
                <Card
                  key={s.domain}
                  className={cn(
                    "cursor-pointer transition-all hover:shadow-md border-l-4",
                    currentDomain === s.domain ? "ring-2 ring-primary/20" : "",
                  )}
                  style={{ borderLeftColor: scoreColor(s.score) }}
                  onClick={() => setActiveTab(s.domain)}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground truncate">
                          {s.domain}
                        </p>
                        <p
                          className="text-4xl font-bold tabular-nums leading-none"
                          style={{ color: scoreColor(s.score) }}
                        >
                          {s.score}
                        </p>
                        <span className={cn(
                          "inline-block mt-1 rounded-full px-2 py-0.5 text-[11px] font-semibold border",
                          grade.bg, grade.text, grade.border,
                        )}>
                          {grade.label}
                        </span>
                      </div>
                      <div className="text-right shrink-0 space-y-0.5 mt-0.5">
                        <p className="text-xs text-muted-foreground">{s.signal_count} signals</p>
                        <p className="text-xs text-muted-foreground">
                          {format(parseISO(s.calculated_at), "MMM d")}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Score history chart */}
          {scores.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Score History
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs value={currentDomain} onValueChange={setActiveTab}>
                  {scores.length > 1 && (
                    <TabsList className="mb-4">
                      {scores.map((s) => (
                        <TabsTrigger key={s.domain} value={s.domain} className="capitalize text-xs">
                          {s.domain}
                        </TabsTrigger>
                      ))}
                    </TabsList>
                  )}
                  {scores.map((s) => (
                    <TabsContent key={s.domain} value={s.domain}>
                      <ScoreHistoryChart domain={s.domain} />
                    </TabsContent>
                  ))}
                </Tabs>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
