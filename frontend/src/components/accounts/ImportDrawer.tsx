"use client"

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type InputHTMLAttributes,
} from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  Loader2,
  Upload,
  XCircle,
} from "lucide-react"
import { format, parseISO } from "date-fns"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ServiceLogo } from "@/components/accounts/ServiceLogo"
import { api, ApiRequestError, type UploadProgress } from "@/lib/api/client"
import { usePasswordManagerFlow } from "@/lib/usePasswordManagerFlow"
import { cn } from "@/lib/utils"
import type {
  AccountResponse,
  MboxUpload,
  MboxUploadListResponse,
  MboxUploadResponse,
  VaultImportResponse,
} from "@/types/api"

// ─── Import source definitions ────────────────────────────────────────────────

type ImportSource =
  | "gmail"
  | "outlook"
  | "apple_mail"
  | "proton_mail"
  | "bitwarden"
  | "proton_pass"
  | "1password"

type ImportOption = {
  source: ImportSource
  label: string
  shortLabel: string
  kind: "mbox" | "vault"
  fileLabel: string
  fileFormat: string
  accept: string
  domain: string
  helper: string
  steps: string[]
  guideUrl?: string
  guideLabel?: string
  vaultSource?: "bitwarden" | "proton_pass" | "1password"
}

const IMPORT_OPTIONS: ImportOption[] = [
  {
    source: "gmail",
    label: "Gmail",
    shortLabel: "Gmail",
    kind: "mbox",
    fileLabel: ".mbox mailbox export",
    fileFormat: "mbox",
    accept: ".mbox,text/plain,application/mbox,application/octet-stream",
    domain: "mail.google.com",
    helper: "Export via Google Takeout, then upload the .mbox file.",
    guideUrl: "https://takeout.google.com",
    guideLabel: "Open Google Takeout",
    steps: [
      "Go to Google Takeout and sign in.",
      "Click Deselect all, then enable Mail only.",
      "Create export, download the archive, extract it.",
      "Upload the .mbox file here.",
    ],
  },
  {
    source: "outlook",
    label: "Outlook",
    shortLabel: "Outlook",
    kind: "mbox",
    fileLabel: ".mbox mailbox export",
    fileFormat: "mbox",
    accept: ".mbox,text/plain,application/mbox,application/octet-stream",
    domain: "outlook.live.com",
    helper: "Use Thunderbird to open the PST and export as mbox.",
    steps: [
      "Open Thunderbird and add your Outlook account.",
      "Navigate to the folder that receives sign-up emails.",
      "Right-click the folder → Export → mbox format.",
      "Upload the resulting .mbox file here.",
    ],
  },
  {
    source: "apple_mail",
    label: "Apple Mail",
    shortLabel: "Apple Mail",
    kind: "mbox",
    fileLabel: ".mbox mailbox export",
    fileFormat: "mbox",
    accept: ".mbox,text/plain,application/mbox,application/octet-stream",
    domain: "apple.com",
    helper: "Apple Mail can export a mailbox directly — no third-party tool needed.",
    steps: [
      "Open Apple Mail and select the mailbox used for sign-ups.",
      "From the menu bar: Mailbox → Export Mailbox…",
      "Pick a save location and click Choose.",
      "Upload the exported .mbox file here.",
    ],
  },
  {
    source: "proton_mail",
    label: "Proton Mail",
    shortLabel: "Proton",
    kind: "mbox",
    fileLabel: "Proton Mail export folder",
    fileFormat: "folder",
    accept: ".eml,.json,text/plain,application/octet-stream",
    domain: "proton.me",
    helper: "The Proton Export Tool produces a folder of .eml files. Choose the whole folder.",
    guideUrl: "https://proton.me/support/export-import-emails",
    guideLabel: "Proton Export Tool guide",
    steps: [
      "Download and install the Proton Mail Export Tool.",
      "Sign in and select the mailbox you use for registrations.",
      "Run the export — this creates a folder of .eml files.",
      "Use the folder picker below (not a zip).",
    ],
  },
  {
    source: "proton_pass",
    label: "Proton Pass",
    shortLabel: "Proton Pass",
    kind: "vault",
    fileLabel: "Proton Pass JSON export",
    fileFormat: "json",
    accept: ".json,application/json,text/plain,application/octet-stream",
    domain: "pass.proton.me",
    helper: "Export your vault as JSON from Proton Pass settings.",
    guideUrl: "https://proton.me/support/pass-import-export",
    guideLabel: "Proton Pass export guide",
    steps: [
      "Open Proton Pass → Settings → Security → Export.",
      "Choose the vault that contains your active accounts.",
      "Export as JSON (not CSV).",
      "Upload the JSON file here.",
    ],
    vaultSource: "proton_pass",
  },
  {
    source: "bitwarden",
    label: "Bitwarden",
    shortLabel: "Bitwarden",
    kind: "vault",
    fileLabel: "Bitwarden JSON export",
    fileFormat: "json",
    accept: ".json,application/json,text/plain,application/octet-stream",
    domain: "bitwarden.com",
    helper: "Export your unencrypted vault as JSON. Delete the file after uploading.",
    steps: [
      "Open Bitwarden → Tools → Export Vault.",
      "Choose .json as the file format.",
      "Enter your master password and click Export Vault.",
      "Upload the JSON file here, then delete it from your device.",
    ],
    vaultSource: "bitwarden",
  },
  {
    source: "1password",
    label: "1Password",
    shortLabel: "1Password",
    kind: "vault",
    fileLabel: "1Password 1PUX export",
    fileFormat: "1pux / zip",
    accept: ".1pux,.zip,application/zip,application/x-zip-compressed,application/octet-stream",
    domain: "1password.com",
    helper: "1PUX is the recommended format — it preserves the most account detail.",
    steps: [
      "Open 1Password → File → Export → All Vaults.",
      "Choose 1Password Unencrypted Export (.1pux).",
      "Save the archive to a private location.",
      "Upload the .1pux file here.",
    ],
    vaultSource: "1password",
  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

type DirectoryInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string
  directory?: string
}

type UploadProgressState = {
  phase: "uploading" | "processing"
  label: string
  fileCount: number
  loaded: number
  total: number | null
  percent: number | null
}

const FOLDER_BATCH_SIZE = 500

function formatBytes(bytes: number | null) {
  if (!bytes || bytes <= 0) return "0 B"
  const units = ["B", "KB", "MB", "GB"]
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value >= 10 || unitIndex === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`
}

function isAllowedFile(option: ImportOption, file: File) {
  const name = file.name.toLowerCase()
  if (option.kind === "mbox") {
    return name.endsWith(".mbox") || file.type === "application/mbox" || file.type === "text/plain" || file.type === "application/octet-stream"
  }
  if (option.source === "1password") {
    return name.endsWith(".1pux") || name.endsWith(".zip") || file.type === "application/zip" || file.type === "application/x-zip-compressed" || file.type === "application/octet-stream"
  }
  return name.endsWith(".json") || file.type === "application/json" || file.type === "text/plain" || file.type === "application/octet-stream"
}

function hasProtonFolderFiles(files: File[]) {
  return files.some((f) => f.name.toLowerCase().endsWith(".eml"))
}

function hasProtonFolderStructure(files: File[]) {
  return files.some((f) => f.webkitRelativePath.includes("/"))
}

// ─── Upload status row ────────────────────────────────────────────────────────

function UploadStatusIcon({ status }: { status: MboxUpload["status"] }) {
  switch (status) {
    case "pending":
      return <Clock className="h-4 w-4 text-slate-500" />
    case "processing":
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
    case "failed":
      return <XCircle className="h-4 w-4 text-red-400" />
  }
}

function UploadRow({ upload }: { upload: MboxUpload }) {
  return (
    <div className="flex items-start gap-3 border-b border-slate-700/50 py-3 last:border-0">
      <div className="mt-0.5 shrink-0">
        <UploadStatusIcon status={upload.status} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-200">{upload.filename}</p>
        <div className="mt-0.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
          <span className="capitalize">{upload.status}</span>
          {upload.status === "completed" && (
            <>
              <span>{upload.accounts_discovered} account{upload.accounts_discovered !== 1 ? "s" : ""} found</span>
              <span>{upload.signals_created} signal{upload.signals_created !== 1 ? "s" : ""}</span>
            </>
          )}
          {upload.processed_at && <span>{format(parseISO(upload.processed_at), "MMM d, HH:mm")}</span>}
        </div>
        {upload.error_detail && (
          <p className="mt-1 rounded border border-red-500/25 bg-red-500/10 px-2 py-1 text-xs text-red-300">
            {upload.error_detail}
          </p>
        )}
      </div>
    </div>
  )
}

// ─── Add-accounts tab ─────────────────────────────────────────────────────────

function AddAccountsTab() {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)
  const pickerTriggerLockRef = useRef(false)
  const [selectedSource, setSelectedSource] = useState<ImportSource>("gmail")
  const [dragging, setDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<UploadProgressState | null>(null)
  const [pendingFollowUpUploadId, setPendingFollowUpUploadId] = useState<string | null>(null)

  const selectedOption = useMemo(
    () => IMPORT_OPTIONS.find((o) => o.source === selectedSource) ?? IMPORT_OPTIONS[0],
    [selectedSource],
  )

  const { data: uploadsData, isLoading: uploadsLoading } = useQuery({
    queryKey: ["mbox-uploads"],
    queryFn: () => api.get<MboxUploadListResponse>("/email-accounts/uploads?limit=10"),
    refetchInterval: (query) => {
      const uploads = query.state.data?.uploads ?? []
      const active = uploads.some((u) => u.status === "pending" || u.status === "processing")
      return active ? 2_000 : false
    },
  })

  const uploads = uploadsData?.uploads ?? []
  const trackedUpload = pendingFollowUpUploadId
    ? (uploads.find((item) => item.id === pendingFollowUpUploadId) ?? null)
    : null

  useEffect(() => {
    if (!trackedUpload) return
    if (trackedUpload.status === "pending") {
      setUploadProgress((p) => p?.phase === "processing" ? { ...p, label: "Queued — waiting to start…" } : p)
      return
    }
    if (trackedUpload.status === "processing") {
      setUploadProgress((p) => p?.phase === "processing" ? { ...p, label: "Analysing mailbox…" } : p)
      return
    }
    if (trackedUpload.status === "failed") {
      setUploadProgress(null)
      setPendingFollowUpUploadId(null)
      return
    }
    if (trackedUpload.status !== "completed") return
    setUploadProgress(null)
    setPendingFollowUpUploadId(null)
    if (trackedUpload.signals_created <= 0) return
    void api.post("/scans", {
      tier: "standard",
      post_import_upload_id: trackedUpload.id,
    })
      .then(() => {
        toast.success(
          "Inbox parsed. Running a follow-up scan for provider checks, identity review, correlation, and score updates.",
        )
        qc.invalidateQueries({ queryKey: ["scans"] })
        qc.invalidateQueries({ queryKey: ["findings"] })
        qc.invalidateQueries({ queryKey: ["scores"] })
      })
      .catch((err) => {
        toast.error(err instanceof ApiRequestError ? err.detail : "Inbox parsed, but the follow-up scan could not be started.")
      })
  }, [qc, trackedUpload])

  function updateProgress(progress: UploadProgress, label: string, fileCount: number) {
    setUploadProgress({ phase: "uploading", label, fileCount, loaded: progress.loaded, total: progress.total, percent: progress.percent })
  }

  const handleMboxSuccess = (res: MboxUploadResponse) => {
    if (res.message) {
      setUploadProgress(null)
      toast.info(res.message)
    } else {
      setUploadProgress({ phase: "processing", label: "Queued — starting…", fileCount: 0, loaded: 0, total: null, percent: null })
      setPendingFollowUpUploadId(res.upload_id)
    }
    qc.invalidateQueries({ queryKey: ["mbox-uploads"] })
    qc.invalidateQueries({ queryKey: ["discovered-accounts"] })
  }

  const handleError = (err: unknown) => {
    setUploadProgress(null)
    toast.error(err instanceof ApiRequestError ? err.detail : "Upload failed.")
  }

  const { mutate: doMboxUpload, isPending: uploadingFile } = useMutation({
    mutationFn: async (file: File) => {
      setUploadProgress({ phase: "uploading", label: "Uploading mailbox export", fileCount: 1, loaded: 0, total: file.size, percent: 0 })
      return api.postFileChunked<MboxUploadResponse>("/email-accounts/uploads", file, 2 * 1024 * 1024, (p) => updateProgress(p, "Uploading mailbox export", 1))
    },
    onSuccess: handleMboxSuccess,
    onError: handleError,
  })

  const { mutate: doFolderUpload, isPending: uploadingFolder } = useMutation({
    mutationFn: async (files: File[]) => {
      const token = crypto.randomUUID()
      const totalBatches = Math.max(1, Math.ceil(files.length / FOLDER_BATCH_SIZE))
      const totalBytes = files.reduce((sum, f) => sum + f.size, 0)
      let bytesUploaded = 0
      setUploadProgress({ phase: "uploading", label: "Uploading Proton Mail export folder", fileCount: files.length, loaded: 0, total: totalBytes || null, percent: 0 })
      let finalResult: MboxUploadResponse | undefined
      for (let i = 0; i < totalBatches; i++) {
        const batch = files.slice(i * FOLDER_BATCH_SIZE, (i + 1) * FOLDER_BATCH_SIZE)
        const batchBytes = batch.reduce((sum, f) => sum + f.size, 0)
        const form = new FormData()
        form.append("token", token)
        form.append("batch_index", String(i))
        form.append("total_batches", String(totalBatches))
        batch.forEach((file) => form.append("files", file, file.webkitRelativePath || file.name))
        const prevBytes = bytesUploaded
        const res = await api.postFormWithProgress<MboxUploadResponse | { status: "received"; batch_index: number }>(
          "/email-accounts/uploads/folder",
          form,
          (progress) => {
            const batchDone = progress.total ? (progress.loaded / progress.total) * batchBytes : progress.percent != null ? (progress.percent / 100) * batchBytes : 0
            const loaded = Math.round(prevBytes + batchDone)
            setUploadProgress({ phase: "uploading", label: "Uploading Proton Mail export folder", fileCount: files.length, loaded, total: totalBytes || null, percent: totalBytes > 0 ? Math.min(99, Math.round((loaded / totalBytes) * 100)) : null })
          },
        )
        bytesUploaded += batchBytes
        if (i === totalBatches - 1) finalResult = res as MboxUploadResponse
      }
      if (!finalResult) throw new Error("Upload failed: no final response received.")
      return finalResult
    },
    onSuccess: handleMboxSuccess,
    onError: handleError,
  })

  const { mutate: doVaultUpload, isPending: uploadingVault } = useMutation({
    mutationFn: async (file: File) => {
      setUploadProgress({ phase: "uploading", label: "Uploading vault export", fileCount: 1, loaded: 0, total: file.size, percent: 0 })
      const form = new FormData()
      form.append("file", file)
      return api.postFormWithProgress<VaultImportResponse>(
        `/imports/vault?source=${selectedOption.vaultSource}`,
        form,
        (p) => updateProgress(p, "Uploading vault export", 1),
      )
    },
    onSuccess: (res) => {
      setUploadProgress(null)
      toast.success(res.message ?? "Vault import queued — processing in background.")
      qc.invalidateQueries({ queryKey: ["discovered-accounts"] })
    },
    onError: handleError,
  })

  const uploading = uploadingFile || uploadingFolder || uploadingVault

  function triggerPicker(ref: React.RefObject<HTMLInputElement | null>) {
    if (uploading || pickerTriggerLockRef.current) return
    pickerTriggerLockRef.current = true
    ref.current?.click()
    window.setTimeout(() => { pickerTriggerLockRef.current = false }, 0)
  }

  async function handleFile(file: File) {
    if (selectedOption.source === "proton_mail") {
      handleProtonFolder([file])
      return
    }
    if (!isAllowedFile(selectedOption, file)) {
      toast.error(`Please upload a ${selectedOption.fileLabel}.`)
      return
    }
    if (selectedOption.kind === "vault") {
      doVaultUpload(file)
    } else {
      doMboxUpload(file)
    }
  }

  function handleProtonFolder(files: File[]) {
    if (!files.length || !hasProtonFolderFiles(files)) {
      toast.error("Please choose the exported Proton Mail folder containing .eml files.")
      return
    }
    if (files.length > 1 && !hasProtonFolderStructure(files)) {
      toast.error("Use the Proton folder picker. Drag-and-drop can lose the folder paths required for upload.")
      return
    }
    doFolderUpload(files)
  }

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const droppedFiles = Array.from(e.dataTransfer.files)
      if (!droppedFiles.length) return
      if (selectedOption.source === "proton_mail") { handleProtonFolder(droppedFiles); return }
      const file = droppedFiles[0]
      if (file) void handleFile(file)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedOption],
  )

  return (
    <div className="space-y-5">
      {/* Source picker */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Email mailboxes</p>
        <div className="grid grid-cols-4 gap-2 mb-4">
          {IMPORT_OPTIONS.filter((o) => o.kind === "mbox").map((option) => {
            const selected = option.source === selectedSource
            return (
              <button
                key={option.source}
                type="button"
                onClick={() => setSelectedSource(option.source)}
                className={cn(
                  "relative rounded-xl border p-2.5 text-left transition-all",
                  selected
                    ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                    : "border-slate-700/60 bg-slate-800/30 hover:border-primary/40 hover:bg-slate-800/60",
                )}
              >
                {selected && <CheckCircle2 className="absolute right-2 top-2 h-3 w-3 text-emerald-400" />}
                <ServiceLogo serviceName={option.label} domain={option.domain} size="sm" className="mb-2" />
                <p className="text-xs font-semibold text-white leading-tight">{option.label}</p>
                <p className="mt-0.5 text-[10px] text-slate-500 uppercase tracking-wide">{option.fileFormat}</p>
              </button>
            )
          })}
        </div>

        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Password managers</p>
        <div className="grid grid-cols-3 gap-2">
          {IMPORT_OPTIONS.filter((o) => o.kind === "vault").map((option) => {
            const selected = option.source === selectedSource
            return (
              <button
                key={option.source}
                type="button"
                onClick={() => setSelectedSource(option.source)}
                className={cn(
                  "relative rounded-xl border p-2.5 text-left transition-all",
                  selected
                    ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                    : "border-slate-700/60 bg-slate-800/30 hover:border-primary/40 hover:bg-slate-800/60",
                )}
              >
                {selected && <CheckCircle2 className="absolute right-2 top-2 h-3 w-3 text-emerald-400" />}
                <ServiceLogo serviceName={option.label} domain={option.domain} size="sm" className="mb-2" />
                <p className="text-xs font-semibold text-white leading-tight">{option.label}</p>
                <p className="mt-0.5 text-[10px] text-slate-500 uppercase tracking-wide">{option.fileFormat}</p>
              </button>
            )
          })}
        </div>
      </div>

      {/* Walkthrough */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4">
        <div className="flex items-center gap-2.5 mb-3">
          <ServiceLogo serviceName={selectedOption.label} domain={selectedOption.domain} size="sm" />
          <div>
            <p className="text-sm font-semibold text-white leading-tight">
              How to export from {selectedOption.label}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">{selectedOption.helper}</p>
          </div>
        </div>
        <div className="space-y-2">
          {selectedOption.steps.map((step, i) => (
            <div key={step} className="flex items-start gap-2.5">
              <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] font-bold text-primary border border-primary/25">
                {i + 1}
              </div>
              <p className="pt-0.5 text-xs text-slate-300 leading-relaxed">{step}</p>
            </div>
          ))}
        </div>
        {selectedOption.guideUrl && (
          <a
            href={selectedOption.guideUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
          >
            {selectedOption.guideLabel ?? "Open official guide"}
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
        {selectedOption.source === "proton_mail" && (
          <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2.5">
            <p className="text-xs font-medium text-amber-200">Folder, not a zip</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-amber-100/80">
              Use the folder picker — do not compress the export first.
            </p>
          </div>
        )}
        {selectedOption.kind === "vault" && (
          <div className="mt-3 rounded-lg border border-slate-700/50 bg-slate-900/40 px-3 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Security note</p>
            <p className="mt-1 text-[11px] text-slate-400 leading-relaxed">
              Your vault export is uploaded over TLS and processed in isolation. Delete the file after uploading.
            </p>
          </div>
        )}
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => {
          if (selectedOption.source === "proton_mail") { triggerPicker(folderRef); return }
          triggerPicker(fileRef)
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2.5 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors",
          dragging
            ? "border-primary bg-primary/5"
            : "border-slate-700/60 bg-slate-800/30 hover:border-primary/40 hover:bg-slate-800/50",
        )}
      >
        <div className={cn(
          "flex h-10 w-10 items-center justify-center rounded-xl border border-slate-700/60 bg-slate-900/70",
          dragging && "border-primary/50 bg-primary/10",
        )}>
          <Upload className={cn("h-4 w-4 transition-colors", uploading ? "animate-pulse text-primary" : dragging ? "text-primary" : "text-slate-400")} />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">
            {uploading
              ? "Uploading and queueing…"
              : selectedOption.source === "proton_mail"
              ? "Choose export folder"
              : `Drop ${selectedOption.shortLabel} file here or click to browse`}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">{selectedOption.fileLabel}</p>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept={selectedOption.accept}
          className="hidden"
          onChange={(e) => {
            pickerTriggerLockRef.current = false
            const file = e.target.files?.[0]
            if (file) void handleFile(file)
            e.target.value = ""
          }}
        />
        <input
          {...({ webkitdirectory: "", directory: "", multiple: true } satisfies DirectoryInputProps)}
          ref={folderRef}
          type="file"
          className="hidden"
          onChange={(e) => {
            pickerTriggerLockRef.current = false
            const files = Array.from(e.target.files ?? [])
            if (!files.length) {
              toast.error("No files found in the selected folder.")
              e.target.value = ""
              return
            }
            handleProtonFolder(files)
            e.target.value = ""
          }}
        />
      </div>

      {uploadProgress && (
        <div className="rounded-lg border border-primary/20 bg-primary/8 px-4 py-3">
          <div className="flex items-center justify-between gap-3 text-sm text-slate-200">
            <span>{uploadProgress.label}</span>
            {uploadProgress.phase === "uploading" && uploadProgress.percent !== null && (
              <span>{uploadProgress.percent}%</span>
            )}
          </div>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
            {uploadProgress.phase === "uploading" && uploadProgress.percent !== null ? (
              <div className="h-full rounded-full bg-primary transition-[width] duration-150" style={{ width: `${uploadProgress.percent}%` }} />
            ) : (
              <div className="h-full animate-pulse rounded-full bg-primary/70" />
            )}
          </div>
          {uploadProgress.phase === "uploading" && (
            <div className="mt-2 flex items-center justify-between gap-3 text-xs text-slate-400">
              <span>
                {uploadProgress.loaded > 0
                  ? `${formatBytes(uploadProgress.loaded)}${uploadProgress.total ? ` / ${formatBytes(uploadProgress.total)}` : ""}`
                  : "Uploading…"}
              </span>
              <span>{uploadProgress.fileCount.toLocaleString()} file{uploadProgress.fileCount !== 1 ? "s" : ""}</span>
            </div>
          )}
          {uploadProgress.phase === "processing" && (
            <p className="mt-2 text-xs text-slate-400">This may take a minute for large mailboxes.</p>
          )}
        </div>
      )}

      {/* Recent uploads */}
      {uploadsLoading ? (
        <div className="space-y-2">
          {[...Array(2)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
        </div>
      ) : uploads.length > 0 ? (
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Recent uploads</p>
          {uploads.map((u) => <UploadRow key={u.id} upload={u} />)}
        </div>
      ) : null}
    </div>
  )
}

// ─── Export tab ───────────────────────────────────────────────────────────────

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

function ExportTab({ totalAccounts }: { totalAccounts: number }) {
  const [exportFormat, setExportFormat] = useState<ExportFormat>("generic")

  const { data: accountData } = useQuery({
    queryKey: ["accounts-profile"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })

  const { exportCompleted, markExportCompleted } = usePasswordManagerFlow(accountData?.user.user_id)

  const managerLabel =
    exportFormat === "1password" ? "1Password" : exportFormat === "bitwarden" ? "Bitwarden" : "Zima CSV"

  return (
    <div className="space-y-4">
      <p className="text-xs leading-relaxed text-slate-400">
        Export your discovered accounts into your password manager. Zima&apos;s exports include
        priority tags and breach-aware context so you can clean up methodically.
      </p>

      <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4">
        <p className="mb-2 text-sm font-semibold text-white">Password manager export</p>
        <p className="mb-3 text-xs text-slate-500">
          {totalAccounts > 0
            ? `${totalAccounts} discovered account${totalAccounts !== 1 ? "s" : ""} ready for export.`
            : "Discover accounts first so the export contains something useful."}
        </p>
        <div className="flex items-center gap-1">
          <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as ExportFormat)}>
            <SelectTrigger className="h-9 w-40 rounded-r-none border-r-0 text-xs">
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
            className="h-9 gap-1.5 rounded-l-none text-xs"
            disabled={totalAccounts === 0}
            onClick={() => downloadAccountExport(exportFormat)}
          >
            <Download className="h-3.5 w-3.5" />
            Export {managerLabel}
          </Button>
        </div>
      </div>

      <div className={cn(
        "rounded-xl border px-4 py-4",
        exportCompleted ? "border-emerald-500/25 bg-emerald-500/10" : "border-primary/25 bg-primary/10",
      )}>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white">
              {exportCompleted ? "Password manager prep marked complete" : "Mark complete after import and link verification"}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-slate-400">
              {exportCompleted
                ? "You've completed this checkpoint."
                : "Import the CSV into your password manager and check login/reset links before moving to findings."}
            </p>
          </div>
          <Button
            className="shrink-0 gap-1.5"
            variant={exportCompleted ? "outline" : "default"}
            disabled={totalAccounts === 0 || exportCompleted}
            onClick={markExportCompleted}
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            Done
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── ImportDrawer ─────────────────────────────────────────────────────────────

export function ImportDrawer({
  open,
  onClose,
  totalAccounts,
}: {
  open: boolean
  onClose: () => void
  totalAccounts: number
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="zima-deep-theme flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden p-0">
        <DialogHeader className="shrink-0 border-b border-slate-700/50 px-6 py-4">
          <DialogTitle className="text-base text-white">Import sources</DialogTitle>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <Tabs defaultValue="upload" className="flex h-full flex-col">
            <TabsList className="mx-6 mt-4 mb-0 w-auto shrink-0 self-start">
              <TabsTrigger value="upload">Add accounts</TabsTrigger>
              <TabsTrigger value="export">Export</TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="mt-4 flex-1 overflow-y-auto px-6 pb-6">
              <AddAccountsTab />
            </TabsContent>

            <TabsContent value="export" className="mt-4 flex-1 overflow-y-auto px-6 pb-6">
              <ExportTab totalAccounts={totalAccounts} />
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}
