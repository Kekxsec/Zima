"use client"

import { format, parseISO, differenceInDays } from "date-fns"
import { cn } from "@/lib/utils"
import type { DiscoveredAccount } from "@/types/api"
import { SourceBadge } from "./SourceBadge"
import { ServiceLogo } from "./ServiceLogo"

function ConfidenceBadge({ score }: { score: number }) {
  const cls =
    score >= 70
      ? "bg-emerald-400/15 text-emerald-300"
      : score >= 40
        ? "bg-amber-400/15 text-amber-300"
        : "bg-muted text-muted-foreground"
  return (
    <span className={cn("rounded-full px-1.5 py-px text-[10px] font-semibold", cls)}>
      {score}%
    </span>
  )
}

export function AccountListRow({
  account,
  selected,
  onClick,
}: {
  account: DiscoveredAccount
  selected: boolean
  onClick: () => void
}) {
  const daysSinceSeen = account.last_seen_at
    ? differenceInDays(new Date(), parseISO(account.last_seen_at))
    : null
  const isRecent = daysSinceSeen !== null && daysSinceSeen <= 90
  const isMbox =
    account.source_type === "account_confirmation" ||
    account.source_type === "password_reset" ||
    account.source_type === "receipt" ||
    account.source_type === "newsletter" ||
    account.source_type === "security_alert" ||
    account.source_type === "other"
  const countLabel = `${account.email_count} ${isMbox ? "email" : "match"}${account.email_count !== 1 ? "s" : ""}`

  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative w-full border-b border-border/40 px-3 py-3 text-left transition-colors",
        "flex items-start gap-3",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-violet-400/50",
        selected
          ? "bg-violet-400/[0.08] before:absolute before:inset-y-0 before:left-0 before:w-[2px] before:bg-violet-400"
          : "hover:bg-white/[0.03]",
      )}
    >
      {/* Logo / monogram */}
      <ServiceLogo
        serviceName={account.service_name}
        domain={account.sender_domain}
        size="sm"
        className="mt-0.5"
      />

      {/* Text block */}
      <div className="min-w-0 flex-1">
        {/* Name + unreviewed dot */}
        <div className="flex items-center gap-1.5">
          <span className="truncate text-sm font-semibold leading-tight text-foreground">
            {account.display_name}
          </span>
          {!account.is_reviewed && (
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-violet-400" />
          )}
        </div>

        {/* Email + source badge */}
        <div className="mt-0.5 flex items-center gap-1.5 overflow-hidden">
          <span className="truncate text-xs text-muted-foreground">
            {account.email_used}
          </span>
          <SourceBadge source={account.source_type} />
        </div>

        {/* Count + confidence + last seen */}
        <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground/70">
          <span>{countLabel}</span>
          <ConfidenceBadge score={account.confidence_score} />
          {account.last_seen_at && (
            <span
              className={cn(isRecent && "font-medium text-emerald-400/80")}
            >
              {format(parseISO(account.last_seen_at), "MMM yyyy")}
            </span>
          )}
          {isRecent && (
            <span className="rounded-full bg-emerald-400/10 px-1.5 py-px text-[10px] font-semibold text-emerald-400">
              active
            </span>
          )}
        </div>
      </div>
    </button>
  )
}
