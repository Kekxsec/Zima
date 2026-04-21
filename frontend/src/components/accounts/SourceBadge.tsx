import { cn } from "@/lib/utils"

// Keys match DiscoveredAccountSourceType in backend/app/db/models/email_accounts.py
const SOURCE_STYLES: Record<string, string> = {
  account_confirmation: "border-violet-400/20 bg-violet-400/12 text-violet-300",
  password_reset:       "border-violet-500/20 bg-violet-500/12 text-violet-300",
  receipt:              "border-amber-500/20 bg-amber-500/12 text-amber-300",
  security_alert:       "border-rose-500/20 bg-rose-500/12 text-rose-300",
  newsletter:           "border-slate-500/20 bg-slate-500/12 text-slate-300",
  other:                "border-border/60 bg-muted/70 text-muted-foreground",
  epieos:               "border-emerald-500/20 bg-emerald-500/12 text-emerald-300",
  holehe:               "border-teal-500/20 bg-teal-500/12 text-teal-300",
  maigret:              "border-orange-500/20 bg-orange-500/12 text-orange-300",
  password_manager:     "border-indigo-500/20 bg-indigo-500/12 text-indigo-300",
  vault_import:         "border-indigo-500/20 bg-indigo-500/12 text-indigo-300",
}

const SOURCE_LABELS: Record<string, string> = {
  account_confirmation: "registration",
  password_reset:       "pwd reset",
  receipt:              "receipt",
  security_alert:       "security",
  newsletter:           "newsletter",
  other:                "email",
  epieos:               "epieos",
  holehe:               "holehe",
  maigret:              "maigret",
  password_manager:     "vault",
  vault_import:         "vault",
}

export function SourceBadge({ source }: { source: string }) {
  const style =
    SOURCE_STYLES[source] ?? "border-border/60 bg-muted/70 text-muted-foreground"
  const label = SOURCE_LABELS[source] ?? source.replace(/_/g, " ")
  return (
    <span
      className={cn(
        "shrink-0 rounded-full border px-1.5 py-px text-[10px] font-medium leading-none",
        style,
      )}
    >
      {label}
    </span>
  )
}

// ─── Monogram colour — deterministic hash of service name ────────────────────

const MONOGRAM_PALETTES = [
  "bg-violet-400/20 text-violet-300",
  "bg-violet-500/20 text-violet-300",
  "bg-emerald-500/20 text-emerald-300",
  "bg-amber-500/20 text-amber-300",
  "bg-rose-500/20 text-rose-300",
  "bg-orange-500/20 text-orange-300",
  "bg-indigo-500/20 text-indigo-300",
  "bg-teal-500/20 text-teal-300",
]

export function monogramColor(name: string): string {
  let hash = 0
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffffffff
  return MONOGRAM_PALETTES[Math.abs(hash) % MONOGRAM_PALETTES.length]
}

// ─── Priority badge ───────────────────────────────────────────────────────────

const PRIORITY_STYLES: Record<number, string> = {
  1: "border-red-500/30 bg-red-500/10 text-red-400",
  2: "border-orange-500/30 bg-orange-500/10 text-orange-400",
  3: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
  4: "border-slate-500/20 bg-slate-500/10 text-slate-400",
}

export function PriorityBadge({ tier, label }: { tier: number; label: string }) {
  const style = PRIORITY_STYLES[tier] ?? PRIORITY_STYLES[4]
  return (
    <span
      className={cn(
        "shrink-0 rounded-full border px-1.5 py-px text-[10px] font-semibold leading-none",
        style,
      )}
    >
      {label}
    </span>
  )
}
