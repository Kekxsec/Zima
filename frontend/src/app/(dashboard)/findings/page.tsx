"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { AlertTriangle, ChevronDown, ChevronUp, EyeOff, CheckCircle2, ShieldCheck } from "lucide-react"
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
import type { FindingListResponse, Finding, FindingStatus } from "@/types/api"

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "all",        label: "All statuses" },
  { value: "open",       label: "Open" },
  { value: "suppressed", label: "Suppressed" },
  { value: "resolved",   label: "Resolved" },
]

function StatusBadge({ status }: { status: Finding["status"] }) {
  const cls =
    status === "open"       ? "bg-blue-50 text-blue-700 border-blue-200" :
    status === "resolved"   ? "bg-green-50 text-green-700 border-green-200" :
    /* suppressed */          "bg-slate-100 text-slate-600 border-slate-200"
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", cls)}>
      {status}
    </span>
  )
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

        <span className="hidden sm:inline text-xs tabular-nums text-muted-foreground">
          {Math.round(finding.confidence * 100)}%
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

          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
            <div>
              <dt className="inline text-muted-foreground">Type: </dt>
              <dd className="inline font-medium text-foreground">{finding.finding_type}</dd>
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
  const total = data?.total ?? 0
  const pages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Findings</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Correlated threat intelligence for your identity
          </p>
        </div>

        <div className="flex items-center gap-3">
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
                ? <ShieldCheck className="h-6 w-6 text-green-500" />
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
