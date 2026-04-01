"use client"

import { useCallback, useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
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
import type {
  MboxUpload,
  MboxUploadListResponse,
  MboxUploadResponse,
  DiscoveredAccountListResponse,
  DiscoveredAccount,
} from "@/types/api"
import { cn } from "@/lib/utils"

// ─── Upload card ─────────────────────────────────────────────────────────────

function uploadStatusIcon(status: MboxUpload["status"]) {
  switch (status) {
    case "pending":    return <Clock className="h-4 w-4 text-muted-foreground" />
    case "processing": return <Loader2 className="h-4 w-4 text-primary animate-spin" />
    case "completed":  return <CheckCircle2 className="h-4 w-4 text-green-500" />
    case "failed":     return <XCircle className="h-4 w-4 text-red-500" />
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
          <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1 mt-1 border border-red-100">
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
          Upload mbox file
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

function sourceTypeBadge(sourceType: string) {
  const map: Record<string, string> = {
    mbox_sender: "bg-sky-100 text-sky-700",
    mbox_registration: "bg-violet-100 text-violet-700",
    epieos: "bg-emerald-100 text-emerald-700",
    holehe: "bg-amber-100 text-amber-700",
    maigret: "bg-orange-100 text-orange-700",
  }
  return map[sourceType] ?? "bg-slate-100 text-slate-600"
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
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-green-600 bg-green-50 border border-green-200 rounded-full px-1.5 py-0.5">
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
  const [exportFormat, setExportFormat] = useState<ExportFormat>("generic")
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

  async function handleExport() {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
    const url = `${base}/email-accounts/export?format=${exportFormat}`
    const a = document.createElement("a")
    a.href = url
    a.download = ""
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

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

            {/* Export */}
            <div className="flex items-center gap-1">
              <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as ExportFormat)}>
                <SelectTrigger className="h-8 w-32 text-xs rounded-r-none border-r-0">
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
                size="sm"
                className="h-8 px-2.5 rounded-l-none text-xs gap-1.5"
                onClick={handleExport}
                disabled={total === 0}
              >
                <Download className="h-3.5 w-3.5" />
                Export
              </Button>
            </div>
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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AccountsPage() {
  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Accounts</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Discover which services have your email address from scans and inbox analysis
        </p>
      </div>

      <UploadCard />
      <AccountsCard />
    </div>
  )
}
