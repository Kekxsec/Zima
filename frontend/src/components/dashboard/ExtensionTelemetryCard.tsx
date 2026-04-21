"use client"

import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { ExtensionStatusResponse } from "@/types/api"

type Props = {
  status: ExtensionStatusResponse | undefined
  isLoading: boolean
}

const RELEVANCE_ORDER: Record<string, number> = {
  high: 0,
  medium: 1,
  low: 2,
  info: 3,
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled"
  if (typeof value === "string" || typeof value === "number") return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function relevanceVariant(relevance: string): "destructive" | "secondary" | "outline" {
  if (relevance === "high") return "destructive"
  if (relevance === "medium") return "secondary"
  return "outline"
}

export function ExtensionTelemetryCard({ status, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Browser extension telemetry</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-56 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!status?.connected) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Browser extension telemetry</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            The browser extension is not connected yet. Connect it to start collecting installed extension inventory,
            guide progress, and privacy settings.
          </p>
          <Button size="sm" asChild>
            <Link href="/connect-extension">Connect extension</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  const mapped = [...status.privacy_settings_mapped].sort((a, b) => {
    const rankA = RELEVANCE_ORDER[a.relevance] ?? 99
    const rankB = RELEVANCE_ORDER[b.relevance] ?? 99
    if (rankA !== rankB) return rankA - rankB
    return a.label.localeCompare(b.label)
  })

  const recentEvents = status.recent_guide_events.slice(0, 8)
  const guideCompletions = Object.entries(status.guide_completions).sort(([a], [b]) =>
    a.localeCompare(b),
  )

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Browser extension telemetry</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3 lg:grid-cols-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider">Browser</p>
            <p className="mt-1">{status.browser ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider">Version</p>
            <p className="mt-1">{status.version ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider">Extensions</p>
            <p className="mt-1">{status.installed_extension_count}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider">Last seen</p>
            <p className="mt-1">
              {status.last_seen_at ? new Date(status.last_seen_at).toLocaleString() : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider">Snapshot storage</p>
            <p className="mt-1">{status.snapshot_encrypted ? "Encrypted" : "Plaintext"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider">Snapshot updated</p>
            <p className="mt-1">
              {status.latest_snapshot_at ? new Date(status.latest_snapshot_at).toLocaleString() : "—"}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-semibold">Installed extensions</p>
          {status.installed_extensions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No installed extensions reported yet.</p>
          ) : (
            <div className="max-h-52 overflow-auto rounded-lg border border-border/70">
              {status.installed_extensions.map((ext) => (
                <div key={ext.id} className="flex items-center justify-between gap-3 border-b border-border/70 px-3 py-2 text-sm last:border-b-0">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{ext.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {ext.id} · v{ext.version}
                    </p>
                  </div>
                  <Badge variant={ext.enabled ? "secondary" : "outline"}>
                    {ext.enabled ? "enabled" : "disabled"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <p className="text-sm font-semibold">Privacy settings relevance map</p>
          <div className="max-h-[28rem] overflow-auto rounded-lg border border-border/70">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-background">
                <tr className="border-b border-border/70 text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="px-3 py-2">Setting</th>
                  <th className="px-3 py-2">Current</th>
                  <th className="px-3 py-2">Recommended</th>
                  <th className="px-3 py-2">Hardened</th>
                  <th className="px-3 py-2">Relevance</th>
                </tr>
              </thead>
              <tbody>
                {mapped.map((setting) => (
                  <tr key={setting.key} className="border-b border-border/70 last:border-b-0">
                    <td className="px-3 py-2 align-top">
                      <p className="font-medium text-foreground">{setting.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {setting.category} · {setting.level_of_control ?? "unknown control"}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">{setting.rationale}</p>
                      {setting.error && (
                        <p className="mt-1 text-xs text-amber-300">Unavailable: {setting.error}</p>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">{formatValue(setting.current_value)}</td>
                    <td className="px-3 py-2 align-top">{formatValue(setting.recommended_value)}</td>
                    <td className="px-3 py-2 align-top">{formatValue(setting.hardened_value)}</td>
                    <td className="px-3 py-2 align-top">
                      <Badge variant={relevanceVariant(setting.relevance)}>{setting.relevance}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-2">
            <p className="text-sm font-semibold">Guide completion by provider</p>
            <div className="space-y-1 text-sm text-muted-foreground">
              {guideCompletions.map(([provider, done]) => (
                <div key={provider} className="flex items-center justify-between rounded-md border border-border/70 px-2 py-1.5">
                  <span>{provider}</span>
                  <Badge variant={done ? "secondary" : "outline"}>{done ? "complete" : "pending"}</Badge>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-semibold">Recent guide events</p>
            {recentEvents.length === 0 ? (
              <p className="text-sm text-muted-foreground">No guide events yet.</p>
            ) : (
              <div className="space-y-1 text-sm text-muted-foreground">
                {recentEvents.map((event, index) => (
                  <div
                    key={`${event.provider}:${event.step}:${event.created_at}:${index}`}
                    className="rounded-md border border-border/70 px-2 py-1.5"
                  >
                    <p className="font-medium text-foreground">
                      {event.provider} · {event.step}
                    </p>
                    <p className="text-xs">{new Date(event.created_at).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-sm font-semibold">Recent connect attempts</p>
            {status.recent_connect_attempts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No connect attempts recorded yet.</p>
            ) : (
              <div className="space-y-1 text-sm text-muted-foreground">
                {status.recent_connect_attempts.slice(0, 8).map((attempt, index) => (
                  <div
                    key={`${attempt.event_type}:${attempt.created_at}:${index}`}
                    className="rounded-md border border-border/70 px-2 py-1.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-foreground">
                        {attempt.outcome}
                        {attempt.reason ? ` · ${attempt.reason}` : ""}
                      </p>
                      <Badge variant={attempt.outcome === "failed" ? "destructive" : "outline"}>
                        {attempt.outcome}
                      </Badge>
                    </div>
                    <p className="text-xs">
                      {(attempt.browser ?? "unknown browser")}
                      {attempt.extension_version ? ` · v${attempt.extension_version}` : ""}
                      {attempt.ip_address ? ` · ${attempt.ip_address}` : ""}
                    </p>
                    <p className="text-xs">{new Date(attempt.created_at).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
