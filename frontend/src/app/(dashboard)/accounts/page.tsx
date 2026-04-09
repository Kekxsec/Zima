"use client"

import { useCallback, useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import {
  Mailbox,
  Upload,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  ExternalLink,
  Eye,
  ArrowRight,
} from "lucide-react"
import { format, parseISO } from "date-fns"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useOnboardingStore } from "@/lib/store/onboarding"
import { hasCompletedBrowserReview } from "@/lib/browserReview"
import type {
  AccountResponse,
  MboxUpload,
  MboxUploadListResponse,
  MboxUploadResponse,
  DiscoveredAccountListResponse,
  DiscoveredAccount,
  FindingListResponse,
  ScanListResponse,
} from "@/types/api"
import { cn } from "@/lib/utils"
import { usePasswordManagerFlow } from "@/lib/usePasswordManagerFlow"

// ─── Upload card ─────────────────────────────────────────────────────────────

function uploadStatusIcon(status: MboxUpload["status"]) {
  switch (status) {
    case "pending":    return <Clock className="h-4 w-4 text-muted-foreground" />
    case "processing": return <Loader2 className="h-4 w-4 text-primary animate-spin" />
    case "completed":  return <CheckCircle2 className="h-4 w-4 text-emerald-300" />
    case "failed":     return <XCircle className="h-4 w-4 text-red-300" />
  }
}

function UploadRow({ upload }: { upload: MboxUpload }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-border last:border-0">
      <div className="mt-0.5 shrink-0">{uploadStatusIcon(upload.status)}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{upload.filename}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground mt-0.5">
          <span className="capitalize">{upload.status}</span>
          {upload.status === "completed" && (
            <>
              <span>{upload.accounts_discovered} account{upload.accounts_discovered !== 1 ? "s" : ""} found</span>
              <span>{upload.signals_created} signal{upload.signals_created !== 1 ? "s" : ""}</span>
            </>
          )}
          {upload.processed_at && (
            <span>{format(parseISO(upload.processed_at), "MMM d, HH:mm")}</span>
          )}
        </div>
        {upload.error_detail && (
          <p className="mt-1 rounded border border-red-500/25 bg-red-500/10 px-2 py-1 text-xs text-red-200">
            {upload.error_detail}
          </p>
        )}
      </div>
    </div>
  )
}

function UploadCard() {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const { data: uploadsData, isLoading: uploadsLoading } = useQuery({
    queryKey: ["mbox-uploads"],
    queryFn: () => api.get<MboxUploadListResponse>("/email-accounts/uploads?limit=10"),
    refetchInterval: (query) => {
      const uploads = query.state.data?.uploads ?? []
      const active = uploads.some(
        (u) => u.status === "pending" || u.status === "processing",
      )
      return active ? 2_000 : false
    },
  })

  const { mutate: doUpload, isPending: uploading } = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append("file", file)
      return api.postForm<MboxUploadResponse>("/email-accounts/uploads", form)
    },
    onSuccess: (res) => {
      if (res.message) {
        toast.info(res.message)
      } else {
        toast.success("Upload queued — processing in background.")
      }
      qc.invalidateQueries({ queryKey: ["mbox-uploads"] })
      qc.invalidateQueries({ queryKey: ["discovered-accounts"] })
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Upload failed.")
    },
  })

  function handleFile(file: File) {
    if (!file.name.endsWith(".mbox") && file.type !== "text/plain" && file.type !== "application/octet-stream") {
      toast.error("Please upload an .mbox file.")
      return
    }
    doUpload(file)
  }

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  const uploads = uploadsData?.uploads ?? []

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
            <Upload className="h-3.5 w-3.5 text-primary" />
          </div>
          Upload inbox export
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground leading-relaxed">
          Export your inbox as an <strong>.mbox</strong> file (Gmail → Settings → All mail → Download) and upload it
          here. Zima will parse sender patterns to discover which services have your email address.
        </p>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
          className={cn(
            "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 cursor-pointer transition-colors",
            dragging
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/40 hover:bg-muted/30",
          )}
        >
          {uploading ? (
            <Loader2 className="h-7 w-7 text-primary animate-spin" />
          ) : (
            <Upload className="h-7 w-7 text-muted-foreground" />
          )}
          <p className="text-sm font-medium">
            {uploading ? "Uploading…" : "Drop .mbox file here or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground">Max 100 MB · 2 uploads per hour</p>
          <input
            ref={fileRef}
            type="file"
            accept=".mbox,text/plain,application/octet-stream"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleFile(f)
              e.target.value = ""
            }}
          />
        </div>

        {/* Upload history */}
        {uploadsLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : uploads.length > 0 ? (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Recent uploads
            </p>
            {uploads.map((u) => <UploadRow key={u.id} upload={u} />)}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

// ─── Accounts table ───────────────────────────────────────────────────────────

type ExportFormat = "generic" | "1password" | "bitwarden"

function downloadAccountExport(exportFormat: ExportFormat) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
  const url = `${base}/email-accounts/export?format=${exportFormat}`
  const a = document.createElement("a")
  a.href = url
  a.download = ""
  a.style.display = "none"
  a.click()
}

function sourceTypeBadge(sourceType: string) {
  const map: Record<string, string> = {
    mbox_sender: "border border-sky-500/20 bg-sky-500/12 text-sky-200",
    mbox_registration: "border border-violet-500/20 bg-violet-500/12 text-violet-200",
    epieos: "border border-emerald-500/20 bg-emerald-500/12 text-emerald-200",
    holehe: "border border-amber-500/20 bg-amber-500/12 text-amber-200",
    maigret: "border border-orange-500/20 bg-orange-500/12 text-orange-200",
  }
  return map[sourceType] ?? "border border-border bg-muted/70 text-muted-foreground"
}

function accountCountLabel(account: DiscoveredAccount) {
  if (["epieos", "holehe", "maigret"].includes(account.source_type)) {
    return `${account.email_count} scan match${account.email_count !== 1 ? "es" : ""}`
  }
  return `${account.email_count} email${account.email_count !== 1 ? "s" : ""}`
}

function AccountRow({
  account,
  onMarkReviewed,
  marking,
}: {
  account: DiscoveredAccount
  onMarkReviewed: (id: string) => void
  marking: boolean
}) {
  return (
    <div className="flex items-start gap-4 py-3.5 border-b border-border last:border-0">
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold truncate">{account.display_name}</span>
          {account.is_reviewed && (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-200">
              <Eye className="h-2.5 w-2.5" /> Reviewed
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
          <span>{account.email_used}</span>
          <span
            className={cn(
              "rounded-full px-1.5 py-0 font-medium text-[10px]",
              sourceTypeBadge(account.source_type),
            )}
          >
            {account.source_type.replace(/_/g, " ")}
          </span>
          <span>{accountCountLabel(account)}</span>
          {account.last_seen_at && (
            <span>last {format(parseISO(account.last_seen_at), "MMM d, yyyy")}</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {account.login_url && (
          <a
            href={account.login_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Login page"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        {!account.is_reviewed && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            disabled={marking}
            onClick={() => onMarkReviewed(account.id)}
          >
            {marking ? <Loader2 className="h-3 w-3 animate-spin" /> : "Mark reviewed"}
          </Button>
        )}
      </div>
    </div>
  )
}

function AccountsCard() {
  const qc = useQueryClient()
  const [sourceFilter, setSourceFilter] = useState<string>("all")
  const [reviewedFilter, setReviewedFilter] = useState<string>("all")
  const [markingId, setMarkingId] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const limit = 50

  const queryParams = new URLSearchParams({ limit: String(limit), offset: String(page * limit) })
  if (sourceFilter !== "all") queryParams.set("source_type", sourceFilter)
  if (reviewedFilter !== "all") queryParams.set("is_reviewed", reviewedFilter)

  const { data, isLoading } = useQuery({
    queryKey: ["discovered-accounts", sourceFilter, reviewedFilter, page],
    queryFn: () =>
      api.get<DiscoveredAccountListResponse>(`/email-accounts/accounts?${queryParams}`),
  })

  const { mutate: markReviewed } = useMutation({
    mutationFn: (id: string) =>
      api.patch<{ account_id: string; is_reviewed: boolean }>(
        `/email-accounts/accounts/${id}/reviewed`,
      ),
    onMutate: (id) => setMarkingId(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["discovered-accounts"] })
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Failed to mark as reviewed.")
    },
    onSettled: () => setMarkingId(null),
  })

  const accounts = data?.accounts ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / limit)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
              <Mailbox className="h-3.5 w-3.5 text-primary" />
            </div>
            Discovered accounts
            {total > 0 && (
              <Badge variant="secondary" className="text-xs font-semibold">
                {total}
              </Badge>
            )}
          </CardTitle>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Filters */}
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="h-8 w-40 text-xs">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All sources</SelectItem>
                <SelectItem value="mbox_sender">mbox sender</SelectItem>
                <SelectItem value="mbox_registration">mbox registration</SelectItem>
                <SelectItem value="epieos">Epieos</SelectItem>
                <SelectItem value="holehe">Holehe</SelectItem>
                <SelectItem value="maigret">Maigret</SelectItem>
              </SelectContent>
            </Select>

            <Select value={reviewedFilter} onValueChange={setReviewedFilter}>
              <SelectTrigger className="h-8 w-36 text-xs">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All accounts</SelectItem>
                <SelectItem value="false">Unreviewed</SelectItem>
                <SelectItem value="true">Reviewed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : accounts.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-muted">
              <Mailbox className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-medium">No accounts discovered yet</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Run a scan or upload an mbox file above to start discovering accounts.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div>
              {accounts.map((a) => (
                <AccountRow
                  key={a.id}
                  account={a}
                  onMarkReviewed={(id) => markReviewed(id)}
                  marking={markingId === a.id}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 text-xs text-muted-foreground">
                <span>
                  {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}
                </span>
                <div className="flex gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 px-2.5 text-xs"
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 px-2.5 text-xs"
                    disabled={page >= totalPages - 1}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function PasswordManagerExportCard({
  exportFormat,
  onExport,
  onConfirm,
  exportCompleted,
  totalAccounts,
  openFindings,
}: {
  exportFormat: ExportFormat
  onExport: (format: ExportFormat) => void
  onConfirm: () => void
  exportCompleted: boolean
  totalAccounts: number
  openFindings: number
}) {
  const managerLabel =
    exportFormat === "1password"
      ? "1Password"
      : exportFormat === "bitwarden"
      ? "Bitwarden"
      : "Zima review CSV"

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
            <Download className="h-3.5 w-3.5 text-primary" />
          </div>
          Export and verify before you touch priorities
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground leading-relaxed">
          Once the account list looks right, export it into your password manager first. Zima’s CSVs are ordered by
          priority and include breach-aware tags, service type context, and link-verification guidance so you can clean
          up methodically instead of jumping straight into findings.
        </p>

        <div className="rounded-xl border border-border bg-card/80 p-4">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">Password manager export</p>
              <p className="text-xs text-muted-foreground mt-1">
                {totalAccounts > 0
                  ? `${totalAccounts} discovered account${totalAccounts !== 1 ? "s" : ""} ready for export.`
                  : "Review discovered accounts first so the export contains something useful."}
              </p>
            </div>
            <div className="flex items-center gap-1">
              <Select value={exportFormat} onValueChange={(value) => onExport(value as ExportFormat)}>
                <SelectTrigger className="h-9 w-40 text-xs rounded-r-none border-r-0">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="generic">Zima CSV</SelectItem>
                  <SelectItem value="1password">1Password</SelectItem>
                  <SelectItem value="bitwarden">Bitwarden</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                className="h-9 rounded-l-none gap-1.5 text-xs"
                disabled={totalAccounts === 0}
                onClick={() => downloadAccountExport(exportFormat)}
              >
                <Download className="h-3.5 w-3.5" />
                Export {managerLabel}
              </Button>
            </div>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-border bg-card/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              What the export includes
            </p>
            <div className="mt-3 space-y-2 text-sm text-muted-foreground">
              <p>Priority tags so breached and higher-risk services rise to the top in your password manager.</p>
              <p>Category and source context so you know whether the account came from a receipt, reset, or signup trail.</p>
              <p>Verification guidance so login and reset links are checked before you use them.</p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Before opening any service link
            </p>
            <div className="mt-3 space-y-2 text-sm text-muted-foreground">
              <p>1. Import the CSV into your password manager of choice.</p>
              <p>2. Start with the items tagged as breached or financially sensitive.</p>
              <p>3. Check login and reset links with VirusTotal before opening them.</p>
              <p>4. Use manual review or an LLM second opinion only after the domain check passes.</p>
            </div>
          </div>
        </div>

        <div
          className={cn(
            "rounded-xl border px-4 py-4",
            exportCompleted ? "border-emerald-500/25 bg-emerald-500/10" : "border-primary/25 bg-primary/10",
          )}
        >
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">
                {exportCompleted ? "Password manager prep marked complete" : "Only move into priorities after export and verification"}
              </p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {exportCompleted
                  ? openFindings > 0
                    ? `${openFindings} open priorit${openFindings === 1 ? "y is" : "ies are"} ready once you’re satisfied the imported accounts and links look safe.`
                    : "You’ve completed this checkpoint. New priorities will make more sense once fresh evidence arrives."
                  : "This keeps remediation grounded in a password manager workflow instead of ad-hoc password changes."}
              </p>
            </div>
            <Button
              className="gap-1.5"
              variant={exportCompleted ? "outline" : "default"}
              disabled={totalAccounts === 0 || exportCompleted}
              onClick={onConfirm}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              I imported these and checked the links
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function IdentitySummaryCard({
  account,
  onboardingIdentity,
}: {
  account?: AccountResponse
  onboardingIdentity: {
    firstName: string
    lastName: string
    phone: string
    usernames: string[]
    emailDomains: string[]
  } | null
}) {
  const assets = account?.assets ?? []
  const primaryEmail = assets.find((asset) => asset.entity_type === "email" && asset.is_primary)
  const emails = assets.filter((asset) => asset.entity_type === "email")
  const phones = assets.filter((asset) => asset.entity_type === "phone_number")
  const usernames = assets.filter((asset) => asset.entity_type === "username")
  const domains = assets.filter((asset) => asset.entity_type === "domain")

  const submittedName = [onboardingIdentity?.firstName, onboardingIdentity?.lastName]
    .filter(Boolean)
    .join(" ")

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">Information we are using</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Profile
            </p>
            {submittedName ? (
              <p className="text-sm font-medium">{submittedName}</p>
            ) : (
              <p className="text-sm text-muted-foreground">Name not stored after onboarding.</p>
            )}
            {primaryEmail ? (
              <p className="text-xs text-muted-foreground">
                Primary email: <span className="font-medium text-foreground">{primaryEmail.value}</span>
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">No primary email available yet.</p>
            )}
          </div>

          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Why this matters
            </p>
            <p className="text-sm text-muted-foreground">
              These are the emails, phone numbers, and usernames helping Zima find your accounts.
            </p>
          </div>
        </div>

        <AssetGroup
          label="Email addresses"
          values={emails.map((asset) => ({
            key: asset.asset_id,
            value: asset.value,
            verified: asset.is_verified,
            primary: Boolean(asset.is_primary),
          }))}
          emptyLabel="No verified email assets yet."
        />

        <AssetGroup
          label="Phone numbers"
          values={
            phones.length > 0
              ? phones.map((asset) => ({
                  key: asset.asset_id,
                  value: asset.value,
                  verified: asset.is_verified,
                }))
              : onboardingIdentity?.phone
              ? [
                  {
                    key: onboardingIdentity.phone,
                    value: onboardingIdentity.phone,
                    verified: false,
                  },
                ]
              : []
          }
          emptyLabel="No verified phone numbers yet."
        />

        <AssetGroup
          label="Usernames"
          values={
            usernames.length > 0
              ? usernames.map((asset) => ({
                  key: asset.asset_id,
                  value: asset.value,
                  verified: asset.is_verified,
                }))
              : (onboardingIdentity?.usernames ?? []).map((username) => ({
                  key: username,
                  value: username,
                  verified: false,
                }))
          }
          emptyLabel="No usernames added yet."
        />

        <AssetGroup
          label="Additional emails and domains"
          values={
            domains.length > 0
              ? domains.map((asset) => ({
                  key: asset.asset_id,
                  value: asset.value,
                  verified: asset.is_verified,
                }))
              : (onboardingIdentity?.emailDomains ?? []).map((email) => ({
                  key: email,
                  value: email,
                  verified: false,
                }))
          }
          emptyLabel="No additional email addresses or domains added yet."
        />

        {account?.user && (
          <p className="text-xs text-muted-foreground">
            Account created {format(parseISO(account.user.created_at), "PPP")}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function AssetGroup({
  label,
  values,
  emptyLabel,
}: {
  label: string
  values: Array<{
    key: string
    value: string
    verified: boolean
    primary?: boolean
  }>
  emptyLabel: string
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      {values.length === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyLabel}</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {values.map((item) => (
            <div
              key={item.key}
              className="inline-flex items-center gap-2 rounded-full border bg-card/80 px-3 py-1.5 text-xs"
            >
              <span className="font-medium text-foreground">{item.value}</span>
              {item.primary && (
                <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                  primary
                </Badge>
              )}
              {item.verified && (
                <Badge variant="outline" className="h-5 border-emerald-500/25 px-1.5 text-[10px] text-emerald-200">
                  verified
                </Badge>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AccountsPage() {
  const searchParams = useSearchParams()
  const uploadRef = useRef<HTMLDivElement | null>(null)
  const exportRef = useRef<HTMLDivElement | null>(null)
  const fromOnboarding = searchParams.get("from") === "onboarding"
  const onboardingIdentity = useOnboardingStore((s) => s.identity)
  const [exportFormat, setExportFormat] = useState<ExportFormat>("generic")

  const { data: accountData } = useQuery({
    queryKey: ["accounts-profile"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })

  const { data: uploadsData } = useQuery({
    queryKey: ["accounts-guide-uploads"],
    queryFn: () => api.get<MboxUploadListResponse>("/email-accounts/uploads?limit=5"),
  })

  const { data: accountsData } = useQuery({
    queryKey: ["accounts-guide-count"],
    queryFn: () => api.get<DiscoveredAccountListResponse>("/email-accounts/accounts?limit=1"),
  })

  const { data: findingsData } = useQuery({
    queryKey: ["accounts-guide-findings"],
    queryFn: () => api.get<FindingListResponse>("/findings?limit=5&filter_status=open"),
  })
  const { data: scansData } = useQuery({
    queryKey: ["accounts-guide-scans"],
    queryFn: () => api.get<ScanListResponse>("/scans?limit=10"),
  })

  const uploads = uploadsData?.uploads ?? []
  const { exportCompleted, markExportCompleted } = usePasswordManagerFlow(accountData?.user.user_id)
  const hasUploadedInbox = uploads.length > 0
  const uploadProcessing = uploads.some((upload) => upload.status === "pending" || upload.status === "processing")
  const discoveredAccounts = accountsData?.total ?? 0
  const openFindings = findingsData?.total ?? 0
  const hasBrowserSetup = hasCompletedBrowserReview(accountData?.assets ?? [], scansData?.scans ?? [])

  const nextStep = !hasUploadedInbox
    ? "upload"
    : uploadProcessing
    ? "processing"
    : discoveredAccounts === 0
    ? "accounts"
    : !exportCompleted
    ? "export"
    : "findings"

  function handlePrimaryAction() {
    if (nextStep === "upload") {
      uploadRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
      return
    }
    if (nextStep === "export") {
      exportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Step 2
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Find and organise your accounts</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          First we find the services tied to your identity. Then we move them into your password manager before
          you start fixing urgent issues.
        </p>
      </div>

      <IdentitySummaryCard account={accountData} onboardingIdentity={onboardingIdentity} />

      <Card className={cn("border", fromOnboarding ? "border-primary/30 bg-primary/10" : "bg-card/80")}>
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">
                {fromOnboarding ? "Continue your setup" : "What to do on this page"}
              </p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {nextStep === "upload"
                  ? "Upload the inbox you use for sign-ups and password resets."
                  : nextStep === "processing"
                  ? "Wait while we turn your inbox into an account list."
                  : nextStep === "export"
                  ? "Review the discovered accounts, then export them into your password manager."
                  : "Your password-manager step is done. You can move on to priorities next."}
              </p>
            </div>
            {nextStep === "findings" ? (
              <Button size="sm" className="gap-1.5" asChild>
                <Link href="/findings">
                  Review findings <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </Button>
            ) : nextStep === "export" ? (
              <Button size="sm" className="gap-1.5" onClick={handlePrimaryAction}>
                Export and verify accounts <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            ) : nextStep === "processing" ? (
              <Button size="sm" variant="outline" disabled className="gap-1.5">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Analysing inbox
              </Button>
            ) : (
              <Button size="sm" className="gap-1.5" onClick={handlePrimaryAction}>
                Upload mbox below <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <div ref={uploadRef}>
        <UploadCard />
      </div>
      <AccountsCard />
      <div ref={exportRef}>
        <PasswordManagerExportCard
          exportFormat={exportFormat}
          onExport={setExportFormat}
          onConfirm={markExportCompleted}
          exportCompleted={exportCompleted}
          totalAccounts={discoveredAccounts}
          openFindings={openFindings}
        />
      </div>
    </div>
  )
}
