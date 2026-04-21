"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  ExternalLink,
  CheckCircle2,
  Clock,
  Mail,
  Globe,
  Tag,
  Loader2,
  Copy,
  ShieldAlert,
  Link2,
  KeyRound,
  Download,
  ThumbsUp,
  ThumbsDown,
  Newspaper,
  Receipt,
} from "lucide-react"
import { format, parseISO } from "date-fns"
import { Button } from "@/components/ui/button"
import { api, ApiRequestError } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import type { AccountVerdict, DiscoveredAccount } from "@/types/api"
import { SourceBadge, PriorityBadge } from "./SourceBadge"
import { ServiceLogo } from "./ServiceLogo"

// ─── Section wrapper ─────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-border/50 px-5 py-4 last:border-0">
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {title}
      </p>
      {children}
    </div>
  )
}

// ─── Metadata row ─────────────────────────────────────────────────────────────

function MetaRow({
  icon: Icon,
  label,
  value,
  href,
  copyable,
}: {
  icon: React.ElementType
  label: string
  value: string
  href?: string
  copyable?: boolean
}) {
  function handleCopy() {
    void navigator.clipboard.writeText(value)
    toast.success("Copied to clipboard")
  }

  return (
    <div className="flex items-center gap-3 py-2 border-b border-border/30 last:border-0">
      <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <span className="w-20 shrink-0 text-xs text-muted-foreground">{label}</span>
      <div className="flex min-w-0 flex-1 items-center gap-1.5">
        {href ? (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-w-0 items-center gap-1 truncate text-xs font-medium text-violet-400 transition-colors hover:text-violet-300"
          >
            <span className="truncate">{value}</span>
            <ExternalLink className="h-3 w-3 shrink-0" />
          </a>
        ) : (
          <span className="truncate text-xs font-medium text-foreground">{value}</span>
        )}
        {copyable && (
          <button
            onClick={handleCopy}
            className="shrink-0 rounded p-0.5 text-muted-foreground/50 transition-colors hover:text-muted-foreground"
          >
            <Copy className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Confidence chip ─────────────────────────────────────────────────────────

function ConfidenceChip({ score }: { score: number }) {
  const cls =
    score >= 70
      ? "bg-emerald-400/15 text-emerald-300"
      : score >= 40
        ? "bg-amber-400/15 text-amber-300"
        : "bg-muted text-muted-foreground"
  return (
    <span className={cn("rounded-full px-1.5 py-px text-[10px] font-semibold", cls)}>
      {score}% confidence
    </span>
  )
}

// ─── Verdict chip ─────────────────────────────────────────────────────────────

const VERDICT_STYLES: Record<string, string> = {
  confirmed: "bg-emerald-400/15 text-emerald-300",
  dismissed: "bg-muted text-muted-foreground",
  newsletter: "bg-sky-400/15 text-sky-300",
  receipt: "bg-orange-400/15 text-orange-300",
}

function VerdictChip({ verdict }: { verdict: string }) {
  return (
    <span
      className={cn(
        "rounded-full px-1.5 py-px text-[10px] font-semibold capitalize",
        VERDICT_STYLES[verdict] ?? "bg-muted text-muted-foreground",
      )}
    >
      {verdict}
    </span>
  )
}

// ─── Priority indicator ───────────────────────────────────────────────────────

const PRIORITY_DESCRIPTIONS: Record<number, string> = {
  1: "Financial account in a breach — reset credentials immediately.",
  2: "High-risk: financial account or breach signal. Act this week.",
  3: "Confirmed account — review, set a unique password, enable MFA.",
  4: "Low-signal account (newsletter / unclassified). Audit or delete.",
}

function PriorityPanel({ tier, label }: { tier: number; label: string }) {
  const borderColor = tier === 1
    ? "border-red-500/30 bg-red-500/5"
    : tier === 2
      ? "border-orange-500/30 bg-orange-500/5"
      : tier === 3
        ? "border-yellow-500/30 bg-yellow-500/5"
        : "border-slate-500/20 bg-slate-500/5"

  return (
    <div className={cn("rounded-lg border px-3 py-2.5", borderColor)}>
      <div className="flex items-center gap-2">
        <PriorityBadge tier={tier} label={label} />
        <p className="text-xs text-muted-foreground">{PRIORITY_DESCRIPTIONS[tier] ?? ""}</p>
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export function AccountDetailPane({ account }: { account: DiscoveredAccount }) {
  const qc = useQueryClient()

  const isMbox =
    account.source_type === "account_confirmation" ||
    account.source_type === "password_reset" ||
    account.source_type === "receipt" ||
    account.source_type === "newsletter" ||
    account.source_type === "security_alert" ||
    account.source_type === "other"
  const evidenceLabel = `${account.email_count} ${isMbox ? "email" : "scan match"}${account.email_count !== 1 ? (isMbox ? "s" : "es") : ""}`

  const { mutate: markReviewed, isPending: marking } = useMutation({
    mutationFn: () =>
      api.patch<{ account_id: string; is_reviewed: boolean }>(
        `/email-accounts/accounts/${account.id}/reviewed`,
      ),
    onSuccess: () => {
      toast.success(`${account.display_name} marked as reviewed.`)
      qc.invalidateQueries({ queryKey: ["discovered-accounts"] })
    },
    onError: (err) => {
      toast.error(
        err instanceof ApiRequestError ? err.detail : "Failed to mark as reviewed.",
      )
    },
  })

  const { mutate: setVerdict, isPending: settingVerdict } = useMutation({
    mutationFn: (verdict: AccountVerdict) =>
      api.patch<{ account_id: string; user_verdict: string; is_reviewed: boolean }>(
        `/email-accounts/accounts/${account.id}/verdict`,
        { verdict },
      ),
    onSuccess: (_, verdict) => {
      const labels: Record<AccountVerdict, string> = {
        confirmed: "Confirmed",
        dismissed: "Dismissed",
        newsletter: "Marked as newsletter",
        receipt: "Marked as receipt",
      }
      toast.success(`${account.display_name}: ${labels[verdict]}`)
      qc.invalidateQueries({ queryKey: ["discovered-accounts"] })
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Failed to update verdict.")
    },
  })

  function copyEmail() {
    void navigator.clipboard.writeText(account.email_used)
    toast.success("Email address copied")
  }

  function copyLoginUrl() {
    if (!account.login_url) return
    void navigator.clipboard.writeText(account.login_url)
    toast.success("Login URL copied")
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* ─── Account header ─── */}
      <div className="shrink-0 border-b border-border/50 px-5 py-5">
        <div className="flex items-start gap-4">
          <ServiceLogo
            serviceName={account.service_name}
            domain={account.sender_domain}
            size="lg"
          />

          <div className="min-w-0 flex-1">
            <h2 className="text-base font-bold leading-tight text-foreground">
              {account.display_name}
            </h2>
            <p className="mt-0.5 text-sm text-muted-foreground">{account.email_used}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <SourceBadge source={account.source_type} />
              {account.category && (
                <span className="text-[10px] text-muted-foreground/60 capitalize">
                  {account.category}
                </span>
              )}
              <ConfidenceChip score={account.confidence_score} />
              {account.user_verdict && (
                <VerdictChip verdict={account.user_verdict} />
              )}
            </div>
          </div>

          {!account.is_reviewed && (
            <Button
              size="sm"
              className="shrink-0 gap-1.5 text-xs"
              disabled={marking}
              onClick={() => markReviewed()}
            >
              {marking ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5" />
              )}
              Mark reviewed
            </Button>
          )}
        </div>
      </div>

      {/* ─── Priority ─── */}
      <Section title="Priority">
        <PriorityPanel tier={account.priority_tier} label={account.priority_label} />
      </Section>

      {/* ─── Summary ─── */}
      <Section title="Summary">
        <MetaRow icon={Mail} label="Email" value={account.email_used} copyable />
        <MetaRow
          icon={Tag}
          label="Source"
          value={account.source_type.replace(/_/g, " ")}
        />
        {account.sender_domain && (
          <MetaRow icon={Globe} label="Domain" value={account.sender_domain} copyable />
        )}
        {account.login_url && (
          <MetaRow
            icon={Link2}
            label="Login"
            value={account.login_url}
            href={account.login_url}
            copyable
          />
        )}
        {account.password_reset_url && (
          <MetaRow
            icon={KeyRound}
            label="Reset"
            value={account.password_reset_url}
            href={account.password_reset_url}
          />
        )}
      </Section>

      {/* ─── Evidence ─── */}
      <Section title="Evidence">
        <div className="flex items-center gap-2.5 rounded-lg border border-border/50 bg-muted/20 px-3 py-2.5">
          <Mail className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="text-xs text-foreground">{evidenceLabel}</span>
        </div>
        {account.first_seen_at && (
          <p className="mt-2 text-xs text-muted-foreground">
            First seen {format(parseISO(account.first_seen_at), "PPP")}
          </p>
        )}
      </Section>

      {/* ─── Security status ─── */}
      <Section title="Security status">
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className={cn(
                "h-2 w-2 shrink-0 rounded-full",
                account.is_reviewed ? "bg-emerald-400" : "bg-amber-400",
              )}
            />
            {account.is_reviewed ? "Account reviewed" : "Awaiting review"}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-2 w-2 shrink-0 rounded-full bg-muted-foreground/30" />
            No breach signals detected for this source
          </div>
        </div>
      </Section>

      {/* ─── Triage ─── */}
      <Section title="Triage">
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={account.user_verdict === "confirmed" ? "default" : "outline"}
            className="gap-1.5 text-xs"
            disabled={settingVerdict}
            onClick={() => setVerdict("confirmed")}
          >
            <ThumbsUp className="h-3.5 w-3.5" />
            Confirm
          </Button>
          <Button
            size="sm"
            variant={account.user_verdict === "dismissed" ? "destructive" : "outline"}
            className="gap-1.5 text-xs"
            disabled={settingVerdict}
            onClick={() => setVerdict("dismissed")}
          >
            <ThumbsDown className="h-3.5 w-3.5" />
            Dismiss
          </Button>
          <Button
            size="sm"
            variant={account.user_verdict === "newsletter" ? "secondary" : "outline"}
            className="gap-1.5 text-xs"
            disabled={settingVerdict}
            onClick={() => setVerdict("newsletter")}
          >
            <Newspaper className="h-3.5 w-3.5" />
            Newsletter
          </Button>
          <Button
            size="sm"
            variant={account.user_verdict === "receipt" ? "secondary" : "outline"}
            className="gap-1.5 text-xs"
            disabled={settingVerdict}
            onClick={() => setVerdict("receipt")}
          >
            <Receipt className="h-3.5 w-3.5" />
            Receipt
          </Button>
        </div>
      </Section>

      {/* ─── Actions ─── */}
      <Section title="Actions">
        <div className="flex flex-wrap gap-2">
          {/* Always available */}
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs"
            onClick={copyEmail}
          >
            <Copy className="h-3.5 w-3.5" />
            Copy email
          </Button>

          {account.login_url && (
            <>
              <Button size="sm" variant="outline" className="gap-1.5 text-xs" asChild>
                <a href={account.login_url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-3.5 w-3.5" />
                  Open login
                </a>
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 text-xs"
                onClick={copyLoginUrl}
              >
                <Copy className="h-3.5 w-3.5" />
                Copy URL
              </Button>
            </>
          )}

          {account.password_reset_url && (
            <Button size="sm" variant="outline" className="gap-1.5 text-xs" asChild>
              <a href={account.password_reset_url} target="_blank" rel="noopener noreferrer">
                <KeyRound className="h-3.5 w-3.5" />
                Reset password
              </a>
            </Button>
          )}

          {/* Check findings for this email */}
          <Button size="sm" variant="outline" className="gap-1.5 text-xs" asChild>
            <a href={`/findings?email=${encodeURIComponent(account.email_used)}`}>
              <ShieldAlert className="h-3.5 w-3.5" />
              View findings
            </a>
          </Button>

          {/* Export this account */}
          <Button size="sm" variant="outline" className="gap-1.5 text-xs" asChild>
            <a href="/api/v1/email-accounts/export?format=generic">
              <Download className="h-3.5 w-3.5" />
              Export all
            </a>
          </Button>
        </div>

        {/* Alias creation hint */}
        <p className="mt-3 text-[11px] text-muted-foreground/60">
          To create an email alias for this account, connect SimpleLogin or Addy.io in{" "}
          <a href="/integrations" className="text-violet-400/80 hover:text-violet-400">
            Integrations
          </a>
          .
        </p>
      </Section>

      {/* ─── Activity ─── */}
      <Section title="Activity">
        <div className="space-y-2.5 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>
              Discovered {format(parseISO(account.created_at), "PPP")} via{" "}
              {account.source_type.replace(/_/g, " ")}
            </span>
          </div>
          {account.last_seen_at && (
            <div className="flex items-center gap-2">
              <Clock className="h-3.5 w-3.5 shrink-0" />
              <span>Last activity {format(parseISO(account.last_seen_at), "PPP")}</span>
            </div>
          )}
          {account.is_reviewed && (
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
              <span className="text-emerald-400/80">Marked as reviewed</span>
            </div>
          )}
        </div>
      </Section>
    </div>
  )
}
