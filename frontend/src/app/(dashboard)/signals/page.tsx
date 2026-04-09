"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Radio, ChevronDown, ChevronUp, EyeOff } from "lucide-react"
import { format, parseISO } from "date-fns"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { SeverityBadge } from "@/components/ui/SeverityBadge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import type { Signal, SignalListResponse } from "@/types/api"

const STATUS_OPTIONS = [
  { value: "open",       label: "Open" },
  { value: "suppressed", label: "Suppressed" },
]

const SORT_OPTIONS = [
  { value: "severity", label: "Severity" },
  { value: "date", label: "Date" },
  { value: "signal", label: "Signal" },
] as const

const SEVERITY_ORDER: Record<Signal["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
}

function ProviderBadge({ provider }: { provider: string }) {
  return (
    <span className="inline-flex items-center rounded border border-border bg-muted/70 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
      {provider}
    </span>
  )
}

function hasLegacyEmailPatternEvidence(signal: Signal) {
  if (!signal.evidence || typeof signal.evidence !== "object") return false
  const patterns = (signal.evidence as Record<string, unknown>).emailformat_patterns
  return Array.isArray(patterns) && patterns.length > 0
}

function SignalRow({
  signal,
  onSuppress,
  suppressing,
}: {
  signal: Signal
  onSuppress: (id: string) => void
  suppressing: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={cn("border-b border-border last:border-0", expanded && "bg-muted/20")}>
      <div
        className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-4 px-5 py-3.5 cursor-pointer hover:bg-muted/20 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <SeverityBadge severity={signal.severity as "critical" | "high" | "medium" | "low" | "info"} className="w-[72px] justify-center" />

        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium leading-snug truncate">{signal.summary}</p>
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-xs text-muted-foreground">{signal.signal_type}</span>
            <span className="text-muted-foreground/40">·</span>
            <ProviderBadge provider={signal.provider} />
            {signal.entity_value && (
              <>
                <span className="text-muted-foreground/40">·</span>
                <span className="text-xs text-muted-foreground truncate max-w-[160px]">{signal.entity_value}</span>
              </>
            )}
          </div>
        </div>

        <span className="hidden md:inline text-xs tabular-nums text-muted-foreground">
          {format(parseISO(signal.created_at), "MMM d")}
        </span>

        <div className="text-muted-foreground">
          {expanded
            ? <ChevronUp className="h-3.5 w-3.5 shrink-0" />
            : <ChevronDown className="h-3.5 w-3.5 shrink-0" />}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-border bg-muted/10 px-5 py-4 space-y-3">
          {signal.details && (
            <p className="text-sm text-foreground leading-relaxed">{signal.details}</p>
          )}

          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
            <div>
              <dt className="inline text-muted-foreground">Type: </dt>
              <dd className="inline font-medium text-foreground">{signal.signal_type}</dd>
            </div>
            <div>
              <dt className="inline text-muted-foreground">Category: </dt>
              <dd className="inline text-foreground">{signal.category}</dd>
            </div>
            <div>
              <dt className="inline text-muted-foreground">Confidence: </dt>
              <dd className="inline text-foreground capitalize">{signal.confidence}</dd>
            </div>
            <div>
              <dt className="inline text-muted-foreground">Source: </dt>
              <dd className="inline text-foreground">{signal.source}</dd>
            </div>
            <div>
              <dt className="inline text-muted-foreground">Detected: </dt>
              <dd className="inline text-foreground">{format(parseISO(signal.created_at), "PPP")}</dd>
            </div>
          </dl>

          {signal.recommended_action && (
            <div className="rounded-md bg-blue-50 border border-blue-100 px-3 py-2 text-xs text-blue-800">
              <span className="font-semibold">Recommended: </span>{signal.recommended_action}
            </div>
          )}

          {signal.signal_type === "alias_exposure_detected" && hasLegacyEmailPatternEvidence(signal) && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              <span className="font-semibold">Note: </span>
              Any `emailformat_patterns` shown below are generic naming examples for the email domain.
              They are not proof that this exact email address exists on the detected platform.
            </div>
          )}

          {signal.tags && signal.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {signal.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-[10px]">{tag}</Badge>
              ))}
            </div>
          )}

          {signal.evidence && Object.keys(signal.evidence).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-1.5">Evidence</p>
              <pre className="rounded-md bg-slate-900 text-slate-100 text-[11px] leading-relaxed p-3 overflow-x-auto whitespace-pre-wrap break-all">
                {JSON.stringify(signal.evidence, null, 2)}
              </pre>
            </div>
          )}

          {signal.status === "open" && (
            <Button
              size="sm"
              variant="outline"
              disabled={suppressing}
              onClick={(e) => { e.stopPropagation(); onSuppress(signal.signal_id) }}
            >
              <EyeOff className="h-3.5 w-3.5" /> Suppress
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

export default function SignalsPage() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState("open")
  const [sortBy, setSortBy] = useState<(typeof SORT_OPTIONS)[number]["value"]>("severity")
  const [offset, setOffset] = useState(0)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ["signals", { statusFilter, offset, limit }],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
        filter_status: statusFilter,
      })
      return api.get<SignalListResponse>(`/signals?${params}`)
    },
  })

  const { mutate: suppress, isPending } = useMutation({
    mutationFn: (id: string) => api.patch(`/signals/${id}/suppress`, {}),
    onSuccess: () => {
      toast.success("Signal suppressed.")
      qc.invalidateQueries({ queryKey: ["signals"] })
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Update failed.")
    },
  })

  const signals = data?.signals ?? []
  const sortedSignals = [...signals].sort((a, b) => {
    if (sortBy === "signal") {
      return a.summary.localeCompare(b.summary) || a.signal_type.localeCompare(b.signal_type)
    }

    if (sortBy === "date") {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    }

    const severityDelta = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
    if (severityDelta !== 0) return severityDelta
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
  const total = data?.total ?? 0
  const pages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Evidence</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Provider evidence behind the issues Zima found for you
          </p>
        </div>

        <div className="flex items-center gap-3">
          {!isLoading && (
            <span className="text-xs text-muted-foreground">
              {total} {total === 1 ? "signal" : "signals"}
            </span>
          )}
          <Select
            value={statusFilter}
            onValueChange={(v) => { setStatusFilter(v); setOffset(0) }}
          >
            <SelectTrigger className="w-36 h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as (typeof SORT_OPTIONS)[number]["value"])}>
            <SelectTrigger className="w-36 h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="p-0 divide-y divide-border">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-5 py-4">
                <Skeleton className="h-10 w-full" />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : signals.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-14 text-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Radio className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="font-semibold">No signals</p>
              <p className="text-sm text-muted-foreground mt-0.5">
                {statusFilter === "open"
                  ? "No open signals — run a scan to collect data."
                  : "No signals match this filter."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="hidden md:grid grid-cols-[auto_1fr_auto_auto] gap-4 border-b border-border bg-muted/30 px-5 py-2.5">
            <span className="w-[72px] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Severity
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Signal
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Date
            </span>
            <span />
          </div>
          <CardContent className="p-0">
            {sortedSignals.map((s) => (
              <SignalRow
                key={s.signal_id}
                signal={s}
                onSuppress={(id) => suppress(id)}
                suppressing={isPending}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {currentPage} of {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
