"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import {
  CheckCircle2,
  FileSearch,
  Loader2,
  Mailbox,
  Sparkles,
} from "lucide-react"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { api, ApiRequestError } from "@/lib/api/client"
import { useOnboardingStore } from "@/lib/store/onboarding"
import type {
  MboxUpload,
  Scan,
  VaultImportDetailResponse,
} from "@/types/api"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
  { label: "Import & Enrich" },
]

type ProcessingPhase = "waiting" | "scanning" | "done" | "failed"

function sourceLabel(source: string) {
  switch (source) {
    case "gmail":
      return "Gmail"
    case "outlook":
      return "Outlook"
    case "apple_mail":
      return "Apple Mail"
    case "proton_mail":
      return "Proton Mail"
    case "bitwarden":
      return "Bitwarden"
    case "proton_pass":
      return "Proton Pass"
    case "1password":
      return "1Password"
    default:
      return "your source"
  }
}

export default function OnboardingImportProcessingPage() {
  const router = useRouter()
  const importJob = useOnboardingStore((s) => s.importJob)
  const setScanId = useOnboardingStore((s) => s.setScanId)
  const [phase, setPhase] = useState<ProcessingPhase>("waiting")
  const [statusText, setStatusText] = useState("Preparing your upload…")
  const [error, setError] = useState<string | null>(null)
  const startedFollowUpRef = useRef(false)

  useEffect(() => {
    if (!importJob) {
      router.replace("/onboarding/import")
    }
  }, [importJob, router])

  useEffect(() => {
    if (!importJob) return

    const currentImportJob = importJob
    let cancelled = false
    let intervalId: ReturnType<typeof setInterval> | null = null

    async function handleCompletedMbox(upload: MboxUpload) {
      if (startedFollowUpRef.current) return

      if (upload.signals_created <= 0) {
        setPhase("done")
        router.replace("/onboarding/import/complete")
        return
      }

      startedFollowUpRef.current = true
      setPhase("scanning")
      setStatusText(
        "Inbox parsed. Running a follow-up scan for provider checks, identity review, correlation, and score refresh.",
      )

      try {
        const triggered = await api.post<Scan>("/scans", {
          tier: "standard",
          post_import_upload_id: upload.id,
        })
        if (cancelled) return
        setScanId(triggered.id)
        // Keep importJob until import/complete so that page can load summary
        // data and the user does not get redirected back to /onboarding/import.
        router.replace("/onboarding/scan?next=import-complete")
      } catch (err) {
        if (cancelled) return
        setPhase("failed")
        setError(err instanceof ApiRequestError ? err.detail : "Could not start the follow-up scan.")
      }
    }

    async function pollImportStatus() {
      try {
        if (currentImportJob.kind === "mbox") {
          const upload = await api.get<MboxUpload>(`/email-accounts/uploads/${currentImportJob.jobId}`)
          if (cancelled) return

          if (upload.status === "pending" || upload.status === "processing") {
            setPhase("waiting")
            setStatusText(
              upload.status === "pending"
                ? `Queued ${sourceLabel(currentImportJob.source)} upload.`
                : `Parsing the ${sourceLabel(currentImportJob.source)} file and extracting account evidence.`,
            )
            return
          }

          if (upload.status === "failed") {
            setPhase("failed")
            setError(upload.error_detail ?? "Upload processing failed.")
            return
          }

          await handleCompletedMbox(upload)
          return
        }

        const vaultImport = await api.get<VaultImportDetailResponse>(`/imports/vault/${currentImportJob.jobId}`)
        if (cancelled) return

        if (vaultImport.status === "pending" || vaultImport.status === "processing") {
          setPhase("waiting")
          setStatusText(`Processing the ${sourceLabel(currentImportJob.source)} export and building your account list.`)
          return
        }

        if (vaultImport.status === "failed") {
          setPhase("failed")
          setError(vaultImport.error_detail ?? "Import processing failed.")
          return
        }

        setPhase("done")
        router.replace("/onboarding/import/complete")
      } catch (err) {
        if (cancelled) return
        setPhase("failed")
        setError(err instanceof ApiRequestError ? err.detail : "Could not check import status.")
      }
    }

    void pollImportStatus()
    intervalId = setInterval(() => {
      void pollImportStatus()
    }, 3000)

    return () => {
      cancelled = true
      if (intervalId) clearInterval(intervalId)
    }
  }, [importJob, router, setScanId])

  if (!importJob) return null

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={4} />
      </div>

      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <div
            className={`inline-flex h-16 w-16 items-center justify-center rounded-2xl mb-5 ${
              phase === "failed"
                ? "border border-red-500/20 bg-red-500/10"
                : phase === "done"
                ? "border border-emerald-500/20 bg-emerald-500/10"
                : "border border-primary/20 bg-primary/10"
            }`}
          >
            {phase === "failed" ? (
              <FileSearch className="h-8 w-8 text-red-400" />
            ) : phase === "done" ? (
              <CheckCircle2 className="h-8 w-8 text-emerald-400" />
            ) : phase === "scanning" ? (
              <Sparkles className="h-8 w-8 text-primary animate-pulse" />
            ) : (
              <Mailbox className="h-8 w-8 text-primary animate-pulse" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">
            {phase === "waiting" && "Processing your import…"}
            {phase === "scanning" && "Running the follow-up scan…"}
            {phase === "done" && "Import complete"}
            {phase === "failed" && "Import failed"}
          </h1>
          <p className="text-sm text-slate-400">
            {phase === "failed"
              ? error ?? "An unexpected error occurred."
              : statusText}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-700/60 bg-slate-900/70">
              {phase === "failed" ? (
                <FileSearch className="h-4 w-4 text-red-400" />
              ) : (
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
              )}
            </div>
            <div className="space-y-3">
              <p className="text-sm font-semibold text-white">
                {importJob.kind === "mbox"
                  ? `${sourceLabel(importJob.source)} mailbox import`
                  : `${sourceLabel(importJob.source)} vault import`}
              </p>
              <p className="text-sm text-slate-400 leading-relaxed">
                We keep this inside onboarding so the upload can finish, any account evidence can be processed,
                and any required follow-up scan can run before you land in the main product.
              </p>
              <div className="grid gap-3 md:grid-cols-3">
                <StatusTile
                  title="Upload queued"
                  complete={phase !== "failed"}
                />
                <StatusTile
                  title="Evidence extracted"
                  complete={phase === "scanning" || phase === "done"}
                />
                <StatusTile
                  title="Ready to continue"
                  complete={phase === "done"}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusTile({
  title,
  complete,
}: {
  title: string
  complete: boolean
}) {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-900/50 px-4 py-3">
      <div className="flex items-center gap-2">
        {complete ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        ) : (
          <Loader2 className="h-4 w-4 text-primary animate-spin" />
        )}
        <p className="text-sm text-slate-200">{title}</p>
      </div>
    </div>
  )
}
