"use client"

import { useEffect, useRef, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { AlertTriangle, ArrowRight, CheckCircle2, Mailbox, Shield } from "lucide-react"
import { format, parseISO } from "date-fns"
import { api } from "@/lib/api/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { SeverityBadge } from "@/components/ui/SeverityBadge"
import { getAdvisorNextAction } from "@/lib/advisorJourney"
import { hasCompletedBrowserReview } from "@/lib/browserReview"
import { usePasswordManagerFlow } from "@/lib/usePasswordManagerFlow"
import type {
  AccountResponse,
  DiscoveredAccountListResponse,
  Finding,
  FindingListResponse,
  MboxUploadListResponse,
  Scan,
  ScanListResponse,
} from "@/types/api"

const PROGRESS_MESSAGES = [
  "Checking breach databases…",
  "Looking for exposed credentials…",
  "Discovering linked accounts…",
  "Correlating findings…",
  "Finishing your results…",
]

const MBOX_STEPS = [
  "Export the mailbox you use for sign-ups and password resets.",
  "Upload the .mbox file on the accounts page.",
  "We use it to find services that may not appear in breach data alone.",
]

function useElapsedSeconds(startedAt: string | null): number {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!startedAt) return

    const base = new Date(startedAt).getTime()
    const update = () => setElapsed(Math.floor((Date.now() - base) / 1000))
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [startedAt])

  return elapsed
}

function formatElapsed(seconds: number) {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return remainder === 0 ? `${minutes}m` : `${minutes}m ${remainder}s`
}

function ScanProgressBanner({ scan }: { scan: Scan }) {
  const qc = useQueryClient()
  const [messageIndex, setMessageIndex] = useState(0)
  const previousStatus = useRef(scan.status)
  const elapsed = useElapsedSeconds(scan.started_at)

  useEffect(() => {
    if (scan.status !== "running") return
    const id = setInterval(() => {
      setMessageIndex((current) => (current + 1) % PROGRESS_MESSAGES.length)
    }, 7000)
    return () => clearInterval(id)
  }, [scan.status])

  useEffect(() => {
    if (
      (previousStatus.current === "running" || previousStatus.current === "pending") &&
      scan.status === "completed"
    ) {
      qc.invalidateQueries({ queryKey: ["scores"] })
      qc.invalidateQueries({ queryKey: ["findings"] })
      qc.invalidateQueries({ queryKey: ["scans"] })
      qc.invalidateQueries({ queryKey: ["advisor-uploads"] })
      qc.invalidateQueries({ queryKey: ["advisor-accounts"] })
    }
    previousStatus.current = scan.status
  }, [qc, scan.status])

  if (scan.status === "completed") {
    return (
      <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-300" />
          <div>
            <p className="text-sm font-semibold text-emerald-100">Your scan is complete</p>
            <p className="text-xs text-emerald-200/80">
              The latest findings are now ready below.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (scan.status !== "running" && scan.status !== "pending") return null

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-4">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Shield className="h-5 w-5 animate-pulse text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-foreground">Your scan is still running</p>
            <span className="text-xs text-muted-foreground">· {formatElapsed(elapsed)} elapsed</span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{PROGRESS_MESSAGES[messageIndex]}</p>
        </div>
      </div>
    </div>
  )
}

function dedupeBreaches(findings: Finding[]) {
  const seen = new Set<string>()
  return findings
    .flatMap((finding) => finding.impacted_breaches)
    .filter((breach) => {
      const key = `${breach.email}:${breach.breach_name}:${breach.provider}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

export default function DashboardPage() {
  const searchParams = useSearchParams()
  const incomingScanId = searchParams.get("scan_id")

  const { data: accountData } = useQuery({
    queryKey: ["dashboard-account"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })

  const { data: findingsData, isLoading: findingsLoading } = useQuery({
    queryKey: ["findings", { limit: 10, status: "open" }],
    queryFn: () => api.get<FindingListResponse>("/findings?limit=10&filter_status=open"),
  })

  const { data: scansData } = useQuery({
    queryKey: ["scans", { limit: 5 }],
    queryFn: () => api.get<ScanListResponse>("/scans?limit=5"),
    refetchInterval: (query) => {
      const scans = query.state.data?.scans ?? []
      return scans.some((scan) => scan.status === "running" || scan.status === "pending")
        ? 5000
        : false
    },
  })

  const { data: accountsData } = useQuery({
    queryKey: ["advisor-accounts"],
    queryFn: () => api.get<DiscoveredAccountListResponse>("/email-accounts/accounts?limit=1"),
  })

  const { data: uploadsData } = useQuery({
    queryKey: ["advisor-uploads"],
    queryFn: () => api.get<MboxUploadListResponse>("/email-accounts/uploads?limit=5"),
  })

  const uploads = uploadsData?.uploads ?? []
  const openFindings = findingsData?.findings ?? []
  const totalOpenFindings = findingsData?.total ?? 0
  const criticalBreaches = dedupeBreaches(openFindings).slice(0, 4)
  const latestScan = scansData?.scans[0] ?? null
  const hasCompletedScan = Boolean(scansData?.scans.some((scan) => scan.status === "completed"))
  const hasUploadedInbox = uploads.length > 0
  const uploadProcessing = uploads.some((upload) => upload.status === "pending" || upload.status === "processing")
  const discoveredAccounts = accountsData?.total ?? 0
  const { exportCompleted } = usePasswordManagerFlow(accountData?.user.user_id)
  const hasBrowserSetup = hasCompletedBrowserReview(accountData?.assets ?? [], scansData?.scans ?? [])
  const runningScan =
    scansData?.scans.find((scan) => scan.status === "running" || scan.status === "pending") ??
    (incomingScanId && latestScan?.id === incomingScanId ? latestScan : null)
  const completedIncomingScan =
    scansData?.scans.find((scan) => scan.id === incomingScanId && scan.status === "completed") ?? null

  const journeyInput = {
    hasCompletedScan,
    hasUploadedInbox,
    uploadProcessing,
    discoveredAccounts,
    exportCompleted,
    openFindings: totalOpenFindings,
    hasBrowserSetup,
  }
  const nextAction = getAdvisorNextAction(journeyInput)

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Badge variant="secondary" className="rounded-full px-3 py-1 text-[11px] uppercase tracking-wider">
          Personal Cybersecurity Advisor
        </Badge>
        <h1 className="text-2xl font-bold tracking-tight">Your security plan</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          This page should answer two simple questions: what did we find, and what should you do next.
          Start with one step at a time.
        </p>
      </div>

      {(runningScan || completedIncomingScan) && (
        <ScanProgressBanner scan={runningScan ?? completedIncomingScan!} />
      )}

      <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">What we have found so far</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {findingsLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, index) => (
                  <Skeleton key={index} className="h-16 w-full" />
                ))}
              </div>
            ) : criticalBreaches.length > 0 ? (
              <>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  These services were already found in breach data. After your account export is in your password
                  manager, start with these first.
                </p>
                <div className="space-y-3">
                  {criticalBreaches.map((breach) => (
                    <div
                      key={`${breach.email}:${breach.breach_name}:${breach.provider}`}
                      className="rounded-xl border border-border bg-card/80 px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-foreground">{breach.breach_name}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {breach.email} · {breach.provider}
                            {breach.breach_date ? ` · ${format(parseISO(breach.breach_date), "PPP")}` : ""}
                          </p>
                        </div>
                        <SeverityBadge severity="high" className="w-[72px] justify-center shrink-0" />
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">{breach.summary}</p>
                    </div>
                  ))}
                </div>
                <Button variant="outline" className="gap-2" asChild>
                  <Link href={exportCompleted ? "/findings" : "/accounts"}>
                    {exportCompleted ? "Open priorities" : "Finish account export first"}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </>
            ) : totalOpenFindings > 0 ? (
              <>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  We found issues that need review. Open the priorities page for the full explanation.
                </p>
                <div className="space-y-3">
                  {openFindings.slice(0, 3).map((finding) => (
                    <div key={finding.finding_id} className="rounded-xl border border-border bg-card/80 px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-foreground">{finding.title}</p>
                          <p className="mt-2 text-sm text-muted-foreground">{finding.explanation}</p>
                        </div>
                        <SeverityBadge severity={finding.severity} className="w-[72px] justify-center shrink-0" />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-4">
                <p className="text-sm font-medium text-emerald-100">No urgent findings are open right now</p>
                <p className="mt-1 text-sm text-emerald-200/80">
                  The next useful step is usually account discovery, so we can check for more services tied to you.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Your next step</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-xl border border-primary/20 bg-primary/10 px-4 py-4">
              <p className="text-sm font-semibold text-foreground">{nextAction.title}</p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{nextAction.description}</p>
            </div>

            {!hasUploadedInbox && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Inbox upload in plain English
                </p>
                {MBOX_STEPS.map((step) => (
                  <div key={step} className="rounded-xl border border-border bg-card/80 px-4 py-3 text-sm text-muted-foreground">
                    {step}
                  </div>
                ))}
              </div>
            )}

            {hasUploadedInbox && uploadProcessing && (
              <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
                <p className="text-sm font-semibold text-foreground">Your inbox is being analysed</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  We are turning those emails into a list of accounts that matter to you.
                </p>
              </div>
            )}

            {discoveredAccounts > 0 && (
              <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
                <div className="flex items-center gap-2">
                  <Mailbox className="h-4 w-4 text-violet-300" />
                  <p className="text-sm font-semibold text-foreground">
                    {discoveredAccounts} account{discoveredAccounts === 1 ? "" : "s"} found
                  </p>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Review them on the accounts page, then export them into your password manager before you start
                  changing passwords.
                </p>
              </div>
            )}

            <Button className="w-full gap-2" asChild>
              <Link href={nextAction.href}>
                {nextAction.label}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>

            <div className="rounded-xl border border-border bg-card/80 px-4 py-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                <p className="text-sm text-muted-foreground">
                  The score page is only a later progress check. It is not the main thing to focus on right now.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
