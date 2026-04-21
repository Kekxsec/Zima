"use client"

import { useEffect, useMemo, useRef, useState, type InputHTMLAttributes } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  Upload,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { ServiceLogo } from "@/components/accounts/ServiceLogo"
import { api, ApiRequestError } from "@/lib/api/client"
import {
  useOnboardingStore,
  type OnboardingImportSource,
} from "@/lib/store/onboarding"
import type { MboxUploadResponse, VaultImportResponse } from "@/types/api"
import { cn } from "@/lib/utils"
import type { UploadProgress } from "@/lib/api/client"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
  { label: "Import & Enrich" },
]

type ImportOption = {
  source: OnboardingImportSource
  label: string
  shortLabel: string
  kind: "mbox" | "vault"
  fileLabel: string
  fileFormat: string
  accept: string
  domain: string
  description: string
  helper: string
  steps: string[]
  guideUrl?: string
  guideLabel?: string
  vaultSource?: "bitwarden" | "proton_pass" | "1password"
}

type DirectoryInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string
  directory?: string
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
    description: "Best if the inbox you use for sign-ups and password resets lives in Gmail.",
    helper: "Export the mailbox you use for registrations via Google Takeout, then upload the .mbox file.",
    guideUrl: "https://takeout.google.com",
    guideLabel: "Open Google Takeout",
    steps: [
      "Go to Google Takeout and sign in.",
      "Click Deselect all, then scroll down and enable Mail only.",
      "Choose your export format and click Create export.",
      "Download the archive, extract it, and upload the .mbox file here.",
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
    description: "Use this when Outlook is the inbox where service registrations land.",
    helper: "Outlook exports PST natively. Use a mail client like Thunderbird to open the PST and export the folder as mbox.",
    steps: [
      "Open Thunderbird and add your Outlook / Microsoft account.",
      "Navigate to the folder that receives sign-up emails.",
      "Right-click the folder and choose Export → mbox format.",
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
    description: "Best when Apple Mail already holds the inbox you use for registrations.",
    helper: "Apple Mail can export a mailbox directly — no third-party tool needed.",
    steps: [
      "Open Apple Mail and select the mailbox used for sign-ups and resets.",
      "From the menu bar choose Mailbox → Export Mailbox…",
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
    description: "Use this when Proton Mail is the inbox receiving sign-ups, resets, and account alerts.",
    helper: "The Proton Export Tool produces a folder of .eml files, not a single mbox. Choose the whole folder here.",
    guideUrl: "https://proton.me/support/export-import-emails",
    guideLabel: "Proton Export Tool guide",
    steps: [
      "Download and install the Proton Mail Export Tool.",
      "Sign in and select the mailbox you use for registrations.",
      "Run the export — this creates a folder containing .eml files.",
      "Click below and select that folder (not a zip of it).",
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
    description: "Use this if Proton Pass is the cleaner source of the accounts you actively keep.",
    helper: "Export your vault as JSON from Proton Pass settings — this is the most accurate account inventory.",
    guideUrl: "https://proton.me/support/pass-import-export",
    guideLabel: "Proton Pass export guide",
    steps: [
      "Open Proton Pass and go to Settings → Security → Export.",
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
    description: "Use this if your account inventory already lives in Bitwarden.",
    helper: "Export your unencrypted vault as JSON. Delete the file after uploading.",
    steps: [
      "Open Bitwarden and go to Tools → Export Vault.",
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
    description: "Use this if 1Password is the cleanest source of the accounts you actually keep.",
    helper: "1PUX is the recommended format — it preserves the most account detail.",
    steps: [
      "Open 1Password and select File → Export → All Vaults (or a specific vault).",
      "Choose 1Password Unencrypted Export (.1pux) as the format.",
      "Save the archive to a private location.",
      "Upload the .1pux file here.",
    ],
    vaultSource: "1password",
  },
]

function isAllowedFile(option: ImportOption, file: File) {
  const lowerName = file.name.toLowerCase()

  if (option.kind === "mbox") {
    return (
      lowerName.endsWith(".mbox") ||
      file.type === "application/mbox" ||
      file.type === "text/plain" ||
      file.type === "application/octet-stream"
    )
  }

  if (option.source === "1password") {
    return (
      lowerName.endsWith(".1pux") ||
      lowerName.endsWith(".zip") ||
      file.type === "application/zip" ||
      file.type === "application/x-zip-compressed" ||
      file.type === "application/octet-stream"
    )
  }

  return (
    lowerName.endsWith(".json") ||
    file.type === "application/json" ||
    file.type === "text/plain" ||
    file.type === "application/octet-stream"
  )
}

function hasProtonFolderFiles(files: File[]) {
  return files.some((file) => file.name.toLowerCase().endsWith(".eml"))
}

function hasProtonFolderStructure(files: File[]) {
  return files.some((file) => file.webkitRelativePath.includes("/"))
}

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

type UploadProgressState = {
  label: string
  fileCount: number
  loaded: number
  total: number | null
  percent: number | null
}

export default function OnboardingImportPage() {
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)
  const pickerTriggerLockRef = useRef(false)
  const importJob = useOnboardingStore((s) => s.importJob)
  const setImportJob = useOnboardingStore((s) => s.setImportJob)
  const setCompleted = useOnboardingStore((s) => s.setCompleted)
  const setScanId = useOnboardingStore((s) => s.setScanId)
  const [selectedSource, setSelectedSource] = useState<OnboardingImportSource>("gmail")
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<UploadProgressState | null>(null)

  useEffect(() => {
    if (importJob) {
      router.replace("/onboarding/import/processing")
    }
  }, [importJob, router])

  const selectedOption = useMemo(
    () => IMPORT_OPTIONS.find((option) => option.source === selectedSource) ?? IMPORT_OPTIONS[0],
    [selectedSource],
  )

  function finishOnboarding() {
    setCompleted(true)
    setImportJob(null)
    setScanId(null)
    router.push("/accounts")
  }

  const FOLDER_BATCH_SIZE = 500

  function updateUploadProgress(progress: UploadProgress, label: string, fileCount: number) {
    setUploadProgress({
      label,
      fileCount,
      loaded: progress.loaded,
      total: progress.total,
      percent: progress.percent,
    })
  }

  function triggerPicker(ref: React.RefObject<HTMLInputElement | null>) {
    if (uploading || pickerTriggerLockRef.current) return
    pickerTriggerLockRef.current = true
    ref.current?.click()
    window.setTimeout(() => {
      pickerTriggerLockRef.current = false
    }, 0)
  }

  async function handleProtonFolder(files: File[]) {
    if (!files.length || !hasProtonFolderFiles(files)) {
      toast.error("Please choose the exported Proton Mail folder containing .eml files.")
      return
    }
    if (files.length > 1 && !hasProtonFolderStructure(files)) {
      toast.error("Use the Proton folder picker. Drag-and-drop can lose the folder paths required for upload.")
      return
    }

    setUploading(true)
    const token = crypto.randomUUID()
    const totalBatches = Math.max(1, Math.ceil(files.length / FOLDER_BATCH_SIZE))
    const totalBytes = files.reduce((sum, f) => sum + f.size, 0)
    let bytesUploaded = 0

    setUploadProgress({
      label: "Uploading Proton Mail export folder",
      fileCount: files.length,
      loaded: 0,
      total: totalBytes || null,
      percent: 0,
    })

    try {
      let finalResult: MboxUploadResponse | undefined

      for (let i = 0; i < totalBatches; i++) {
        const batch = files.slice(i * FOLDER_BATCH_SIZE, (i + 1) * FOLDER_BATCH_SIZE)
        const batchBytes = batch.reduce((sum, f) => sum + f.size, 0)
        const form = new FormData()
        form.append("token", token)
        form.append("batch_index", String(i))
        form.append("total_batches", String(totalBatches))
        batch.forEach((file) => {
          form.append("files", file, file.webkitRelativePath || file.name)
        })

        const prevBytes = bytesUploaded
        const res = await api.postFormWithProgress<MboxUploadResponse | { status: "received"; batch_index: number }>(
          "/email-accounts/uploads/folder",
          form,
          (progress) => {
            const batchDone = progress.total
              ? (progress.loaded / progress.total) * batchBytes
              : progress.percent != null
                ? (progress.percent / 100) * batchBytes
                : 0
            const loaded = Math.round(prevBytes + batchDone)
            setUploadProgress({
              label: "Uploading Proton Mail export folder",
              fileCount: files.length,
              loaded,
              total: totalBytes || null,
              percent: totalBytes > 0 ? Math.min(99, Math.round((loaded / totalBytes) * 100)) : null,
            })
          },
        )
        bytesUploaded += batchBytes

        if (i === totalBatches - 1) {
          finalResult = res as MboxUploadResponse
        }
      }

      if (!finalResult) throw new Error("Upload failed: no final response received.")

      setImportJob({
        kind: "mbox",
        jobId: finalResult.upload_id,
        source: selectedOption.source,
      })
      router.push("/onboarding/import/processing")
    } catch (err) {
      setUploadProgress(null)
      toast.error(err instanceof ApiRequestError ? err.detail : "Upload failed.")
    } finally {
      setUploading(false)
    }
  }

  async function handleFile(file: File) {
    if (selectedOption.source === "proton_mail") {
      await handleProtonFolder([file])
      return
    }

    if (!isAllowedFile(selectedOption, file)) {
      toast.error(`Please upload a ${selectedOption.fileLabel}.`)
      return
    }

    setUploading(true)
    setUploadProgress({
      label: selectedOption.kind === "mbox" ? "Uploading mailbox export" : "Uploading vault export",
      fileCount: 1,
      loaded: 0,
      total: file.size,
      percent: 0,
    })
    try {
      if (selectedOption.kind === "mbox") {
        const response = await api.postFileChunked<MboxUploadResponse>(
          "/email-accounts/uploads",
          file,
          2 * 1024 * 1024,
          (progress) => updateUploadProgress(progress, "Uploading mailbox export", 1),
        )
        setImportJob({
          kind: "mbox",
          jobId: response.upload_id,
          source: selectedOption.source,
        })
      } else {
        const form = new FormData()
        form.append("file", file)
        const response = await api.postFormWithProgress<VaultImportResponse>(
          `/imports/vault?source=${selectedOption.vaultSource}`,
          form,
          (progress) => updateUploadProgress(progress, "Uploading vault export", 1),
        )
        setImportJob({
          kind: "vault",
          jobId: response.import_id,
          source: selectedOption.source,
        })
      }

      router.push("/onboarding/import/processing")
    } catch (err) {
      setUploadProgress(null)
      toast.error(err instanceof ApiRequestError ? err.detail : "Upload failed.")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={4} />
      </div>

      <div className="w-full max-w-4xl space-y-6">
        {/* Header row */}
        <div className="flex items-center justify-between gap-4">
          <Button
            type="button"
            variant="ghost"
            disabled={uploading}
            className="px-0 text-slate-400 hover:bg-transparent hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => router.push("/onboarding/results")}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to first results
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={uploading}
            className="px-0 text-slate-500 hover:bg-transparent hover:text-slate-300 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={finishOnboarding}
          >
            Skip for now
            <X className="ml-1.5 h-3.5 w-3.5" />
          </Button>
        </div>

        {uploading && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-200">
            <Upload className="h-4 w-4 shrink-0 animate-pulse" />
            Upload in progress — please wait before navigating away
          </div>
        )}

        {/* Title */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-2">Add account evidence</h1>
          <p className="text-sm text-slate-400 max-w-2xl mx-auto">
            Your first scan found what is visible from verified assets. Importing a mailbox or password manager
            vault lets Zima map the services you actually use.
          </p>
        </div>

        {/* Source picker */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Select your source</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">Choose the app you can export from today</p>
          </CardHeader>
          <CardContent>
            {/* Email section */}
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Email mailboxes</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 mb-5">
              {IMPORT_OPTIONS.filter((o) => o.kind === "mbox").map((option) => {
                const selected = option.source === selectedSource
                return (
                  <button
                    key={option.source}
                    type="button"
                    onClick={() => setSelectedSource(option.source)}
                    className={cn(
                      "relative rounded-xl border p-3 text-left transition-all",
                      selected
                        ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                        : "border-slate-700/60 bg-slate-800/30 hover:border-primary/40 hover:bg-slate-800/60",
                    )}
                  >
                    {selected && (
                      <CheckCircle2 className="absolute right-2.5 top-2.5 h-3.5 w-3.5 text-emerald-400" />
                    )}
                    <ServiceLogo
                      serviceName={option.label}
                      domain={option.domain}
                      size="sm"
                      className="mb-2.5"
                    />
                    <p className="text-sm font-semibold text-white leading-tight">{option.label}</p>
                    <p className="mt-0.5 text-[11px] text-slate-500 uppercase tracking-wide">{option.fileFormat}</p>
                  </button>
                )
              })}
            </div>

            {/* Password manager section */}
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Password managers</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {IMPORT_OPTIONS.filter((o) => o.kind === "vault").map((option) => {
                const selected = option.source === selectedSource
                return (
                  <button
                    key={option.source}
                    type="button"
                    onClick={() => setSelectedSource(option.source)}
                    className={cn(
                      "relative rounded-xl border p-3 text-left transition-all",
                      selected
                        ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                        : "border-slate-700/60 bg-slate-800/30 hover:border-primary/40 hover:bg-slate-800/60",
                    )}
                  >
                    {selected && (
                      <CheckCircle2 className="absolute right-2.5 top-2.5 h-3.5 w-3.5 text-emerald-400" />
                    )}
                    <ServiceLogo
                      serviceName={option.label}
                      domain={option.domain}
                      size="sm"
                      className="mb-2.5"
                    />
                    <p className="text-sm font-semibold text-white leading-tight">{option.label}</p>
                    <p className="mt-0.5 text-[11px] text-slate-500 uppercase tracking-wide">{option.fileFormat}</p>
                  </button>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Walkthrough + Upload */}
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          {/* Walkthrough */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <ServiceLogo
                  serviceName={selectedOption.label}
                  domain={selectedOption.domain}
                  size="sm"
                />
                <div>
                  <CardTitle className="text-base leading-tight">
                    How to export from {selectedOption.label}
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-0.5">{selectedOption.helper}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2.5">
                {selectedOption.steps.map((step, index) => (
                  <div key={step} className="flex items-start gap-3">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[11px] font-bold text-primary border border-primary/25">
                      {index + 1}
                    </div>
                    <p className="pt-0.5 text-sm text-slate-300 leading-relaxed">{step}</p>
                  </div>
                ))}
              </div>

              {selectedOption.guideUrl && (
                <a
                  href={selectedOption.guideUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-primary hover:text-primary/80 transition-colors"
                >
                  {selectedOption.guideLabel ?? "Open official guide"}
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}

              {selectedOption.source === "proton_mail" && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-4 py-3">
                  <p className="text-sm font-medium text-amber-200">Folder, not a zip</p>
                  <p className="mt-1 text-xs leading-relaxed text-amber-100/80">
                    Proton Mail does not produce a single mbox file. Use the folder picker below to
                    select the exported folder directly — do not compress it first.
                  </p>
                </div>
              )}

              {selectedOption.kind === "vault" && (
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Security note</p>
                  <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                    Your vault export is uploaded over TLS and processed in isolation. Delete the export
                    file from your device after uploading.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Upload */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Upload your {selectedOption.kind === "mbox" && selectedOption.source === "proton_mail" ? "folder" : "file"}</CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                You will stay in onboarding while this processes
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                onDragOver={(event) => {
                  event.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => {
                  event.preventDefault()
                  setDragging(false)
                  const droppedFiles = Array.from(event.dataTransfer.files)
                  if (!droppedFiles.length) return

                  if (selectedOption.source === "proton_mail") {
                    void handleProtonFolder(droppedFiles)
                    return
                  }

                  const file = droppedFiles[0]
                  if (file) void handleFile(file)
                }}
                onClick={() => {
                  if (selectedOption.source === "proton_mail") {
                    triggerPicker(folderRef)
                    return
                  }
                  triggerPicker(fileRef)
                }}
                className={cn(
                  "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
                  dragging
                    ? "border-primary bg-primary/5"
                    : "border-slate-700/60 bg-slate-800/30 hover:border-primary/40 hover:bg-slate-800/50",
                )}
              >
                <div className={cn(
                  "flex h-12 w-12 items-center justify-center rounded-xl border border-slate-700/60 bg-slate-900/70",
                  dragging && "border-primary/50 bg-primary/10",
                )}>
                  <Upload className={cn(
                    "h-5 w-5 transition-colors",
                    uploading ? "animate-pulse text-primary" : dragging ? "text-primary" : "text-slate-400",
                  )} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">
                    {uploading
                      ? "Uploading and queueing…"
                      : selectedOption.source === "proton_mail"
                      ? "Choose export folder"
                      : `Drop ${selectedOption.shortLabel} file here or click to browse`}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{selectedOption.fileLabel}</p>
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept={selectedOption.accept}
                  className="hidden"
                  onChange={(event) => {
                    pickerTriggerLockRef.current = false
                    const file = event.target.files?.[0]
                    if (file) void handleFile(file)
                    event.target.value = ""
                  }}
                />
                <input
                  {...({
                    webkitdirectory: "",
                    directory: "",
                    multiple: true,
                  } satisfies DirectoryInputProps)}
                  ref={folderRef}
                  type="file"
                  className="hidden"
                  onChange={(event) => {
                    pickerTriggerLockRef.current = false
                    const files = Array.from(event.target.files ?? [])
                    if (!files.length) {
                      toast.error("No files found in the selected folder. Please choose the Proton Mail export folder.")
                      event.target.value = ""
                      return
                    }
                    void handleProtonFolder(files)
                    event.target.value = ""
                  }}
                />
              </div>

              {uploadProgress && (
                <div className="rounded-lg border border-primary/20 bg-primary/8 px-4 py-3">
                  <div className="flex items-center justify-between gap-3 text-sm text-slate-200">
                    <span>{uploadProgress.label}</span>
                    {uploadProgress.percent !== null && <span>{uploadProgress.percent}%</span>}
                  </div>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    {uploadProgress.percent !== null ? (
                      <div
                        className="h-full rounded-full bg-primary transition-[width] duration-150"
                        style={{ width: `${uploadProgress.percent}%` }}
                      />
                    ) : (
                      <div className="h-full w-full animate-pulse rounded-full bg-primary/60" />
                    )}
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-3 text-xs text-slate-400">
                    <span>
                      {uploadProgress.loaded > 0
                        ? `${formatBytes(uploadProgress.loaded)}${uploadProgress.total ? ` / ${formatBytes(uploadProgress.total)}` : ""}`
                        : "Uploading..."}
                    </span>
                    <span>
                      {uploadProgress.fileCount.toLocaleString()} file
                      {uploadProgress.fileCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
              )}

              <p className="text-center text-xs text-slate-500">
                You can also{" "}
                <button
                  type="button"
                  disabled={uploading}
                  onClick={finishOnboarding}
                  className="text-slate-400 underline underline-offset-2 hover:text-slate-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  skip this step
                </button>{" "}
                and import later from the dashboard.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
