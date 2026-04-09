"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ScanLine, Play, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react"
import { format, parseISO } from "date-fns"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ScanListResponse, Scan, ScanTier } from "@/types/api"
import { cn } from "@/lib/utils"

const TIER_INFO: Record<ScanTier, { label: string; description: string; badge: string }> = {
  basic:    { label: "Basic",    description: "Email breach check via HIBP and BreachDirectory",           badge: "Free" },
  standard: { label: "Standard", description: "Basic + stealer log exposure, reputation, and social data", badge: "Recommended" },
  deep:     { label: "Deep",     description: "Full scan across all available threat providers",            badge: "Comprehensive" },
}

function statusIcon(status: Scan["status"]) {
  switch (status) {
    case "pending":   return <Clock className="h-4 w-4 text-muted-foreground" />
    case "running":   return <Loader2 className="h-4 w-4 text-primary animate-spin" />
    case "completed": return <CheckCircle2 className="h-4 w-4 text-green-500" />
    case "failed":    return <XCircle className="h-4 w-4 text-red-500" />
  }
}

function statusBarColor(status: Scan["status"]): string {
  switch (status) {
    case "pending":   return "bg-slate-300"
    case "running":   return "bg-primary"
    case "completed": return "bg-green-500"
    case "failed":    return "bg-red-500"
  }
}

function ScanRow({ scan }: { scan: Scan }) {
  return (
    <div className="flex items-start gap-4 py-4 border-b border-border last:border-0">
      <div className={cn("mt-1 h-full w-0.5 rounded-full self-stretch shrink-0", statusBarColor(scan.status))} />
      <div className="mt-0.5 shrink-0">{statusIcon(scan.status)}</div>
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold capitalize text-foreground">{scan.status}</span>
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground capitalize">{scan.tier} tier</span>
          {scan.status === "running" && (
            <span className="text-xs text-primary font-medium animate-pulse">Scanning…</span>
          )}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
          {scan.started_at && (
            <span>Started {format(parseISO(scan.started_at), "MMM d, HH:mm")}</span>
          )}
          {scan.completed_at && (
            <span>Completed {format(parseISO(scan.completed_at), "HH:mm")}</span>
          )}
        </div>
        {scan.target_emails.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Scanned {scan.target_emails.join(", ")}
          </p>
        )}
        {scan.status === "completed" && (
          <div className="flex gap-4 text-xs">
            <span className="text-foreground font-medium">{scan.signals_created} signal{scan.signals_created !== 1 ? "s" : ""}</span>
            <span className="text-foreground font-medium">{scan.findings_created} finding{scan.findings_created !== 1 ? "s" : ""}</span>
            {scan.domains_run.length > 0 && (
              <span className="text-muted-foreground">{scan.domains_run.join(", ")}</span>
            )}
          </div>
        )}
        {scan.error_detail && (
          <p className="text-xs text-red-600 bg-red-50 rounded-md px-2.5 py-1.5 mt-1 border border-red-100">
            {scan.error_detail}
          </p>
        )}
      </div>
    </div>
  )
}

export default function ScansPage() {
  const qc = useQueryClient()
  const [tier, setTier] = useState<ScanTier>("standard")

  const { data, isLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: () => api.get<ScanListResponse>("/scans?limit=20"),
    refetchInterval: (query) => {
      const scans = query.state.data?.scans ?? []
      const active = scans.some((s) => s.status === "pending" || s.status === "running")
      return active ? 2_000 : false
    },
  })

  const { mutate: triggerScan, isPending: triggering } = useMutation({
    mutationFn: () => api.post<Scan>("/scans", { tier }),
    onSuccess: () => {
      toast.success("Scan started!")
      qc.invalidateQueries({ queryKey: ["scans"] })
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Failed to start scan.")
    },
  })

  const scans = data?.scans ?? []
  const hasActive = scans.some((s) => s.status === "pending" || s.status === "running")

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Scans</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          Re-run a scan after you change passwords, upload your inbox, or clean up accounts so Zima can reassess your exposure.
        </p>
      </div>

      {/* Trigger card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
              <Play className="h-3.5 w-3.5 text-primary" />
            </div>
            Run a new scan
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Tier selector */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {(Object.keys(TIER_INFO) as ScanTier[]).map((t) => {
              const info = TIER_INFO[t]
              const selected = tier === t
              return (
                <button
                  key={t}
                  onClick={() => setTier(t)}
                  className={cn(
                    "relative rounded-lg border p-4 text-left transition-all",
                    selected
                      ? "border-primary bg-primary/5 shadow-sm"
                      : "border-border hover:border-primary/40 hover:bg-muted/40",
                  )}
                >
                  {selected && (
                    <div className="absolute top-2.5 right-2.5 h-2 w-2 rounded-full bg-primary" />
                  )}
                  <p className="text-sm font-semibold">{info.label}</p>
                  <p className="text-[11px] text-muted-foreground mt-1 leading-snug">
                    {info.description}
                  </p>
                  <p className={cn(
                    "mt-2 text-[10px] font-semibold uppercase tracking-wide",
                    selected ? "text-primary" : "text-muted-foreground",
                  )}>
                    {info.badge}
                  </p>
                </button>
              )
            })}
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={() => triggerScan()}
              disabled={triggering || hasActive}
              className="gap-2"
            >
              {triggering ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ScanLine className="h-4 w-4" />
              )}
              {hasActive ? "Scan in progress…" : `Start ${TIER_INFO[tier].label} scan`}
            </Button>
            {hasActive && (
              <p className="text-xs text-muted-foreground">
                Results will appear below automatically, including the email address being scanned.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Scan history */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Scan History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}
            </div>
          ) : scans.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-muted">
                <ScanLine className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">No scans yet</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Run your first scan above to see results here.
                </p>
              </div>
            </div>
          ) : (
            <div>
              {scans.map((scan) => (
                <ScanRow key={scan.id} scan={scan} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
