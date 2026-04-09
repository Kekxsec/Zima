"use client"

import Link from "next/link"
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { AlertTriangle, ArrowRight, ChevronDown, ChevronUp, EyeOff, CheckCircle2, ShieldCheck, Link2, ShieldAlert, Sparkles } from "lucide-react"
import { format, parseISO } from "date-fns"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent } from "@/components/ui/card"
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
import { usePasswordManagerFlow } from "@/lib/usePasswordManagerFlow"
import type { AccountResponse, FindingListResponse, Finding, FindingStatus } from "@/types/api"

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "all",        label: "All statuses" },
  { value: "open",       label: "Open" },
  { value: "suppressed", label: "Suppressed" },
  { value: "resolved",   label: "Resolved" },
]

function confidenceLabel(confidence: Finding["confidence_label"], score: number) {
  return `${confidence[0].toUpperCase()}${confidence.slice(1)} confidence (${Math.round(score * 100)}%)`
}

function StatusBadge({ status }: { status: Finding["status"] }) {
  const cls =
    status === "open"       ? "border-sky-500/25 bg-sky-500/12 text-sky-200" :
    status === "resolved"   ? "border-emerald-500/25 bg-emerald-500/12 text-emerald-200" :
    /* suppressed */          "border-border bg-muted/70 text-muted-foreground"
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", cls)}>
      {status}
    </span>
  )
}

function formatBreachDate(value: string | null) {
  if (!value) return "Date unknown"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return format(parsed, "PPP")
}

function FindingRow({
  finding,
  onUpdateStatus,
  updating,
}: {
  finding: Finding
  onUpdateStatus: (id: string, status: FindingStatus) => void
  updating: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const breachesByEmail = finding.impacted_breaches.reduce<Record<string, Finding["impacted_breaches"]>>(
    (acc, breach) => {
      if (!acc[breach.email]) acc[breach.email] = []
      acc[breach.email].push(breach)
      return acc
    },
    {},
  )

  return (
    <div className={cn("border-b border-border last:border-0", expanded && "bg-muted/20")}>
      {/* Main row */}
      <div
        className="grid grid-cols-[auto_1fr_auto_auto_auto] items-center gap-4 px-5 py-3.5 cursor-pointer hover:bg-muted/20 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <SeverityBadge severity={finding.severity} className="w-[72px] justify-center" />

        <div className="min-w-0">
          <p className="text-sm font-medium leading-snug truncate">{finding.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5 truncate">{finding.rule_name}</p>
        </div>

        <StatusBadge status={finding.status} />

        <span className="hidden sm:inline text-xs text-muted-foreground">
          {confidenceLabel(finding.confidence_label, finding.confidence)}
        </span>

        <div className="flex items-center gap-2 text-muted-foreground">
          <span className="hidden md:inline text-xs">
            {format(parseISO(finding.created_at), "MMM d")}
          </span>
          {expanded
            ? <ChevronUp className="h-3.5 w-3.5 shrink-0" />
            : <ChevronDown className="h-3.5 w-3.5 shrink-0" />}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border bg-muted/10 px-5 py-4 space-y-3">
          <p className="text-sm text-foreground leading-relaxed">{finding.explanation}</p>

          {finding.impacted_breaches.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5" />
                Impacted Services And Breaches
              </div>
              <div className="space-y-3">
                {Object.entries(breachesByEmail).map(([email, breaches]) => (
                  <div key={email} className="rounded-lg border border-border bg-background px-3 py-3">
                    <p className="text-sm font-semibold text-foreground">{email}</p>
                    <div className="mt-2 space-y-2">
                      {breaches.map((breach) => (
                        <div
                          key={`${breach.email}-${breach.breach_name}-${breach.provider}-${breach.signal_type}`}
                          className="rounded-md border border-border/70 bg-muted/20 px-3 py-2"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-foreground">{breach.breach_name}</p>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {breach.provider} · {formatBreachDate(breach.breach_date)}
                              </p>
                            </div>
                            <SeverityBadge severity={finding.severity} className="w-[72px] justify-center shrink-0" />
                          </div>
                          <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
                            {breach.summary}
                          </p>
                          {breach.data_classes.length > 0 && (
                            <p className="text-xs text-foreground mt-2">
                              Exposed data: {breach.data_classes.join(", ")}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {finding.recommended_actions.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-amber-800">
                <Sparkles className="h-3.5 w-3.5" />
                What To Do Now
              </div>
              <div className="mt-2 space-y-1.5">
                {finding.recommended_actions.map((action) => (
                  <p key={action} className="text-sm text-amber-950">
                    {action}
                  </p>
                ))}
              </div>
            </div>
          )}

          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
            <div>
              <dt className="inline text-muted-foreground">Type: </dt>
              <dd className="inline font-medium text-foreground">{finding.finding_type}</dd>
            </div>
            <div>
              <dt className="inline text-muted-foreground">Confidence: </dt>
              <dd className="inline text-foreground">
                {confidenceLabel(finding.confidence_label, finding.confidence)}
              </dd>
            </div>
            <div>
              <dt className="inline text-muted-foreground">First seen: </dt>
              <dd className="inline text-foreground">{format(parseISO(finding.created_at), "PPP")}</dd>
            </div>
            <div>
              <dt className="inline text-muted-foreground">Updated: </dt>
              <dd className="inline text-foreground">{format(parseISO(finding.updated_at), "PPP")}</dd>
            </div>
          </dl>

          {finding.affected_entities.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Link2 className="h-3.5 w-3.5" />
                Affected Assets
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {finding.affected_entities.map((entity) => (
                  <div key={entity.id} className="rounded-lg border border-border bg-background px-3 py-2">
                    <p className="text-sm font-medium text-foreground">{entity.value}</p>
                    <p className="text-xs text-muted-foreground">
                      {entity.entity_type.replace(/_/g, " ")}
                      {entity.is_primary ? " · primary" : ""}
                      {entity.is_verified ? " · verified" : ""}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {finding.supporting_signals.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <ShieldAlert className="h-3.5 w-3.5" />
                Why This Finding Exists
              </div>
              <div className="space-y-2">
                {finding.supporting_signals.map((signal) => (
                  <div key={signal.signal_id} className="rounded-lg border border-border bg-background px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground">{signal.summary}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {signal.provider} · {signal.entity_value}
                        </p>
                      </div>
                      <SeverityBadge severity={signal.severity} className="w-[72px] justify-center shrink-0" />
                    </div>
                    {signal.breach_name && (
                      <p className="text-xs text-foreground mt-2">
                        Breach: {signal.breach_name}
                        {signal.breach_date ? ` · ${formatBreachDate(signal.breach_date)}` : ""}
                      </p>
                    )}
                    {signal.details && (
                      <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{signal.details}</p>
                    )}
                    {signal.data_classes.length > 0 && (
                      <p className="text-xs text-foreground mt-2">
                        Exposed data: {signal.data_classes.join(", ")}
                      </p>
                    )}
                    {signal.recommended_action && (
                      <p className="text-xs text-foreground mt-2">
                        Action: {signal.recommended_action}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {finding.status === "open" && (
            <div className="flex gap-2 pt-1">
              <Button
                size="sm"
                variant="outline"
                disabled={updating}
                onClick={() => onUpdateStatus(finding.finding_id, "suppressed")}
              >
                <EyeOff className="h-3.5 w-3.5" /> Suppress
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={updating}
                onClick={() => onUpdateStatus(finding.finding_id, "resolved")}
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Mark resolved
              </Button>
            </div>
          )}
          {finding.status !== "open" && (
            <Button
              size="sm"
              variant="ghost"
              className="text-muted-foreground"
              disabled={updating}
              onClick={() => onUpdateStatus(finding.finding_id, "open")}
            >
              Reopen
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

export default function FindingsPage() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState("open")
  const [offset, setOffset] = useState(0)
  const limit = 20

  const { data: accountData } = useQuery({
    queryKey: ["findings-account"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })

  const { data, isLoading } = useQuery({
    queryKey: ["findings", { statusFilter, offset, limit }],
    queryFn: () => {
      const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
      if (statusFilter !== "all") params.set("filter_status", statusFilter)
      return api.get<FindingListResponse>(`/findings?${params}`)
    },
  })
  const { mutate: updateStatus, isPending } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: FindingStatus }) => {
      if (status === "suppressed") return api.patch(`/findings/${id}/suppress`, {})
      if (status === "resolved")   return api.patch(`/findings/${id}/resolve`, {})
      /* status === "open" (reopen) */
      return api.patch(`/findings/${id}/reopen`, {})
    },
    onSuccess: () => {
      toast.success("Finding updated.")
      qc.invalidateQueries({ queryKey: ["findings"] })
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Update failed.")
    },
  })

  const findings = data?.findings ?? []
  const { exportCompleted } = usePasswordManagerFlow(accountData?.user.user_id)
  const total = data?.total ?? 0
  const pages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1
  const urgentCount = findings.filter((finding) => finding.severity === "critical" || finding.severity === "high").length

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Step 4
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Fix the important issues</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          This page explains what needs attention and why. Start here after your accounts are sitting in your
          password manager.
        </p>
      </div>

      {!exportCompleted && (
        <Card className="border-primary/25 bg-primary/10">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">
                  Finish the password-manager checkpoint before remediation
                </p>
                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                  Export the discovered accounts, import them into your password manager, and verify login or reset
                  links with VirusTotal before you start working through urgent findings.
                </p>
              </div>
              <Button className="gap-2" asChild>
                <Link href="/accounts">
                  Go back to accounts <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {exportCompleted && (
        <Card className="border-border bg-card/80">
          <CardContent className="p-5">
            <p className="text-sm font-semibold text-foreground">
              {total === 0
                ? "No open priorities right now"
                : urgentCount > 0
                ? `Start with the ${urgentCount} highest-risk issue${urgentCount === 1 ? "" : "s"}`
                : "Review the open issues one at a time"}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              Each item below tells you which service was affected, why it was flagged, and what to do next.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between gap-3 flex-wrap">
        {!isLoading && (
          <span className="text-xs text-muted-foreground">
            {total} {total === 1 ? "finding" : "findings"}
          </span>
        )}
        <Select
          value={statusFilter}
          onValueChange={(v) => { setStatusFilter(v); setOffset(0) }}
        >
          <SelectTrigger className="w-40 h-9 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Findings table */}
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
      ) : findings.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-14 text-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              {statusFilter === "open"
                ? <ShieldCheck className="h-6 w-6 text-emerald-300" />
                : <AlertTriangle className="h-6 w-6 text-muted-foreground" />}
            </div>
            <div>
              <p className="font-semibold">No findings</p>
              <p className="text-sm text-muted-foreground mt-0.5">
                {statusFilter === "open"
                  ? "No open findings — your identity looks clean."
                  : "No findings match this filter."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          {/* Column header */}
          <div className="hidden md:grid grid-cols-[auto_1fr_auto_auto_auto] gap-4 border-b border-border bg-muted/30 px-5 py-2.5">
            <span className="w-[72px] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Severity
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Finding
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Status
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Conf.
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Date
            </span>
          </div>
          <CardContent className="p-0">
            {findings.map((f) => (
              <FindingRow
                key={f.finding_id}
                finding={f}
                onUpdateStatus={(id, status) => updateStatus({ id, status })}
                updating={isPending}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
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
