"use client"

import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import {
  ArrowRight,
  HardDrive,
  MonitorSmartphone,
  ShieldAlert,
  ShieldCheck,
  Wrench,
} from "lucide-react"
import { api } from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SeverityBadge } from "@/components/ui/SeverityBadge"
import { Skeleton } from "@/components/ui/skeleton"
import type {
  AccountResponse,
  CompanionStatusResponse,
  FindingListResponse,
  SignalListResponse,
} from "@/types/api"

function isDeviceSignal(signal: SignalListResponse["signals"][number]) {
  return signal.entity_type === "device" || signal.category.includes("device")
}

function isDeviceFinding(finding: FindingListResponse["findings"][number]) {
  return finding.affected_entities.some((entity) => entity.entity_type === "device")
}

export default function DevicePage() {
  const { data: accountData, isLoading: accountLoading } = useQuery({
    queryKey: ["device-account"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })
  const { data: signalsData, isLoading: signalsLoading } = useQuery({
    queryKey: ["device-signals"],
    queryFn: () => api.get<SignalListResponse>("/signals?limit=100&filter_status=open"),
  })
  const { data: findingsData, isLoading: findingsLoading } = useQuery({
    queryKey: ["device-findings"],
    queryFn: () => api.get<FindingListResponse>("/findings?limit=50&filter_status=open"),
  })
  const { data: companionData, isLoading: companionLoading } = useQuery({
    queryKey: ["device-companion-status"],
    queryFn: () => api.get<CompanionStatusResponse>("/companion/status"),
  })

  const deviceAssets =
    accountData?.assets.filter((asset) => asset.entity_type === "device") ?? []
  const deviceSignals = (signalsData?.signals ?? []).filter(isDeviceSignal)
  const deviceFindings = (findingsData?.findings ?? []).filter(isDeviceFinding)
  const loading =
    accountLoading || signalsLoading || findingsLoading || companionLoading

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Device baseline</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          This view consolidates device-level risk signals, companion visibility,
          and the next actions required to harden the machine you use most.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard
          title="Tracked devices"
          value={deviceAssets.length}
          loading={loading}
          icon={<HardDrive className="h-4 w-4 text-sky-400" />}
        />
        <SummaryCard
          title="Open device signals"
          value={deviceSignals.length}
          loading={loading}
          icon={<ShieldAlert className="h-4 w-4 text-amber-400" />}
        />
        <SummaryCard
          title="Open device findings"
          value={deviceFindings.length}
          loading={loading}
          icon={<ShieldCheck className="h-4 w-4 text-emerald-400" />}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Companion visibility</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <Skeleton className="h-24 w-full" />
            ) : companionData?.connected ? (
              <div className="space-y-3">
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4">
                  <p className="text-sm font-medium text-emerald-100">
                    Companion connected
                  </p>
                  <p className="mt-1 text-xs text-emerald-200/80">
                    Platform: {companionData.platform ?? "Unknown"} · Version:{" "}
                    {companionData.version ?? "Unknown"} · Extensions observed:{" "}
                    {companionData.extension_count}
                  </p>
                </div>
                <Button asChild variant="outline" className="gap-2">
                  <Link href="/companion">
                    Open companion details
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-4 rounded-xl border border-border bg-card/70 p-4">
                <div className="flex items-start gap-3">
                  <MonitorSmartphone className="mt-0.5 h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm font-medium">Connect the companion</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Device findings stay shallow until the local companion is installed and reporting snapshots.
                    </p>
                  </div>
                </div>
                <Button asChild className="gap-2">
                  <Link href="/companion">
                    Set up companion
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Priority hardening steps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {deviceSignals.length > 0 ? (
              deviceSignals.slice(0, 5).map((signal) => (
                <div
                  key={signal.signal_id}
                  className="rounded-xl border border-border bg-card/80 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{signal.summary}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {signal.provider} · {signal.entity_value}
                      </p>
                    </div>
                    <SeverityBadge severity={signal.severity} className="w-[72px] justify-center" />
                  </div>
                  {signal.recommended_action && (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {signal.recommended_action}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-border bg-card/70 p-4 text-sm text-muted-foreground">
                No device-specific signals are open yet. Run the companion and a fresh scan to populate this view.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Baseline checklist</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {[
            "Turn on automatic OS updates and restart promptly after security patches.",
            "Keep the firewall enabled on every network profile you use.",
            "Use full-disk encryption on laptops and desktops that leave home.",
            "Remove unused software so the vulnerability surface stays small.",
          ].map((item) => (
            <div key={item} className="flex items-start gap-3 rounded-xl border border-border bg-card/70 p-4">
              <Wrench className="mt-0.5 h-4 w-4 text-primary" />
              <p className="text-sm text-muted-foreground">{item}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function SummaryCard({
  title,
  value,
  loading,
  icon,
}: {
  title: string
  value: number
  loading: boolean
  icon: React.ReactNode
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">
            {title}
          </p>
          {loading ? (
            <Skeleton className="mt-2 h-8 w-14" />
          ) : (
            <p className="mt-2 text-3xl font-bold">{value}</p>
          )}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
          {icon}
        </div>
      </CardContent>
    </Card>
  )
}
