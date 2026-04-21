"use client"

import { Mailbox } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import type { DiscoveredAccount } from "@/types/api"
import { AccountListRow } from "./AccountListRow"

function SectionHeader({
  label,
  count,
  accent,
}: {
  label: string
  count: number
  accent?: boolean
}) {
  return (
    <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-border/40 bg-background px-4 py-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <span
        className={
          accent
            ? "rounded-full bg-violet-400/15 px-1.5 py-px text-[10px] font-semibold text-violet-300"
            : "rounded-full bg-muted px-1.5 py-px text-[10px] font-semibold text-muted-foreground"
        }
      >
        {count}
      </span>
    </div>
  )
}

export function AccountListPane({
  accounts,
  isLoading,
  selectedId,
  onSelect,
  onImport,
  hasFilter,
  onClearFilter,
  showDismissed,
}: {
  accounts: DiscoveredAccount[]
  isLoading: boolean
  selectedId: string | null
  onSelect: (id: string) => void
  onImport: () => void
  hasFilter: boolean
  onClearFilter: () => void
  showDismissed?: boolean
}) {
  if (isLoading) {
    return (
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-[68px] w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (accounts.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 overflow-y-auto px-6 py-12 text-center">
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-muted">
          <Mailbox className="h-5 w-5 text-muted-foreground" />
        </div>
        {hasFilter ? (
          <>
            <p className="text-sm font-medium">No accounts match this filter</p>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={onClearFilter}
            >
              Clear filters
            </Button>
          </>
        ) : (
          <>
            <p className="text-sm font-medium">No accounts discovered yet</p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Import an inbox export or run a scan to start.
            </p>
            <Button size="sm" className="mt-1 gap-1.5 text-xs" onClick={onImport}>
              Import sources
            </Button>
          </>
        )}
      </div>
    )
  }

  const active = showDismissed
    ? accounts
    : accounts.filter((a) => a.user_verdict !== "dismissed")
  const dismissed = accounts.filter((a) => a.user_verdict === "dismissed")

  const highConf = active.filter((a) => a.confidence_score >= 70)
  const midConf = active.filter((a) => a.confidence_score >= 40 && a.confidence_score < 70)
  const lowConf = active.filter((a) => a.confidence_score < 40)

  function renderRows(list: DiscoveredAccount[]) {
    return list
      .slice()
      .sort((a, b) => {
        const aTime = a.last_seen_at ? new Date(a.last_seen_at).getTime() : 0
        const bTime = b.last_seen_at ? new Date(b.last_seen_at).getTime() : 0
        if (bTime !== aTime) return bTime - aTime
        return b.email_count - a.email_count
      })
      .map((a) => (
        <AccountListRow
          key={a.id}
          account={a}
          selected={selectedId === a.id}
          onClick={() => onSelect(a.id)}
        />
      ))
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {highConf.length > 0 && (
        <section>
          <SectionHeader label="Confirmed · 70+" count={highConf.length} accent />
          {renderRows(highConf)}
        </section>
      )}

      {midConf.length > 0 && (
        <section>
          <SectionHeader label="Likely · 40–69" count={midConf.length} />
          {renderRows(midConf)}
        </section>
      )}

      {lowConf.length > 0 && (
        <section>
          <SectionHeader label="Review · &lt;40" count={lowConf.length} />
          {renderRows(lowConf)}
        </section>
      )}

      {showDismissed && dismissed.length > 0 && (
        <section>
          <SectionHeader label="Dismissed" count={dismissed.length} />
          {renderRows(dismissed)}
        </section>
      )}
    </div>
  )
}
