"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowRight,
  CheckCircle2,
  Mailbox,
  ShieldAlert,
  Sparkles,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { api, ApiRequestError } from "@/lib/api/client"
import { useOnboardingStore } from "@/lib/store/onboarding"
import type { MboxUpload, VaultImportDetailResponse } from "@/types/api"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
  { label: "Import & Enrich" },
]

type ImportSummary =
  | {
      kind: "mbox"
      accountsDiscovered: number
      signalsCreated: number
    }
  | {
      kind: "vault"
      accountsDiscovered: number
      signalsCreated: number
    }

export default function OnboardingImportCompletePage() {
  const router = useRouter()
  const importJob = useOnboardingStore((s) => s.importJob)
  const setCompleted = useOnboardingStore((s) => s.setCompleted)
  const setImportJob = useOnboardingStore((s) => s.setImportJob)
  const setScanId = useOnboardingStore((s) => s.setScanId)
  const [isExiting, setIsExiting] = useState(false)
  const [summary, setSummary] = useState<ImportSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!importJob) {
      if (!isExiting) router.replace("/onboarding/import")
      return
    }

    const currentImportJob = importJob
    let cancelled = false

    async function loadSummary() {
      try {
        if (currentImportJob.kind === "mbox") {
          const upload = await api.get<MboxUpload>(`/email-accounts/uploads/${currentImportJob.jobId}`)
          if (cancelled) return
          setSummary({
            kind: "mbox",
            accountsDiscovered: upload.accounts_discovered,
            signalsCreated: upload.signals_created,
          })
          return
        }

        const vaultImport = await api.get<VaultImportDetailResponse>(`/imports/vault/${currentImportJob.jobId}`)
        if (cancelled) return
        setSummary({
          kind: "vault",
          accountsDiscovered: vaultImport.accounts_discovered,
          signalsCreated: 0,
        })
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiRequestError ? err.detail : "Could not load the import summary.")
      }
    }

    void loadSummary()
    return () => {
      cancelled = true
    }
  }, [importJob, isExiting, router])

  function finishOnboarding() {
    setIsExiting(true)
    setCompleted(true)
    setImportJob(null)
    setScanId(null)
    router.push("/dashboard")
  }

  if (!importJob) return null

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={4} />
      </div>

      <div className="w-full max-w-3xl space-y-6">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-500/20 bg-emerald-500/10 mb-5">
            <CheckCircle2 className="h-8 w-8 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Your onboarding evidence is in</h1>
          <p className="text-sm text-slate-400 max-w-2xl mx-auto">
            We kept this step inside onboarding because account evidence can change what Zima surfaces next. You are
            now ready to move into the account-inventory workflow with the imported context included.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <SummaryCard
            icon={<Mailbox className="h-4 w-4 text-violet-400" />}
            label="Accounts discovered"
            value={summary?.accountsDiscovered ?? 0}
          />
          <SummaryCard
            icon={<ShieldAlert className="h-4 w-4 text-amber-400" />}
            label="Signals created"
            value={summary?.signalsCreated ?? 0}
          />
          <SummaryCard
            icon={<Sparkles className="h-4 w-4 text-emerald-400" />}
            label="Import type"
            value={summary?.kind === "vault" ? "Vault" : "Mailbox"}
            isText
          />
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">What changed after the import</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-400">
            {error ? (
              <p>{error}</p>
            ) : (
              <>
                <p>
                  Your first scan only had verified assets to work from, so it could surface breach and exposure
                  evidence already tied to those assets.
                </p>
                <p>
                  This import adds service-level context. For mailbox imports that means sender and registration
                  evidence; for vault imports it means a cleaner inventory of the accounts you already maintain.
                </p>
                <p>
                  That is why we do not show the full account picture on the first results screen: without this step,
                  the findings are still missing the account map needed for the next stage of remediation.
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-center">
          <Button size="lg" className="gap-2 px-10" onClick={finishOnboarding}>
            Continue to account inventory
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function SummaryCard({
  icon,
  label,
  value,
  isText = false,
}: {
  icon: React.ReactNode
  label: string
  value: number | string
  isText?: boolean
}) {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4 text-center">
      <div className="mb-2 flex justify-center">{icon}</div>
      <p className={`font-bold text-white ${isText ? "text-lg" : "text-2xl"}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-500">{label}</p>
    </div>
  )
}
