"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import {
  CheckCircle2,
  Loader2,
  Mail,
  Phone,
  ArrowLeft,
  ArrowRight,
  RotateCcw,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { useOnboardingStore } from "@/lib/store/onboarding"
import { api, ApiRequestError } from "@/lib/api/client"
import type { AssetOut } from "@/types/api"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
]

type VerifyStatus = "pending" | "sending" | "awaiting_code" | "verifying" | "verified" | "error"

interface VerifyItem {
  kind: "email" | "phone"
  value: string
  status: VerifyStatus
  otp: string[]
  error: string | null
}

export default function VerifyEmailsPage() {
  const router = useRouter()
  const pendingEmails = useOnboardingStore((s) => s.pendingEmailVerifications)
  const pendingPhones = useOnboardingStore((s) => s.pendingPhoneVerifications)
  const setPendingEmailVerifications = useOnboardingStore((s) => s.setPendingEmailVerifications)
  const setPendingPhoneVerifications = useOnboardingStore((s) => s.setPendingPhoneVerifications)

  const [items, setItems] = useState<VerifyItem[]>([])
  const otpRefs = useRef<Record<string, (HTMLInputElement | null)[]>>({})

  // Redirect away if there's nothing to verify
  useEffect(() => {
    if (pendingEmails.length === 0 && pendingPhones.length === 0) {
      router.replace("/onboarding/scan")
    } else {
      setItems([
        ...pendingEmails.map((value) => ({
          kind: "email" as const,
          value,
          status: "pending" as VerifyStatus,
          otp: ["", "", "", "", "", ""],
          error: null,
        })),
        ...pendingPhones.map((value) => ({
          kind: "phone" as const,
          value,
          status: "pending" as VerifyStatus,
          otp: ["", "", "", "", "", ""],
          error: null,
        })),
      ])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const allVerified = items.length > 0 && items.every((i) => i.status === "verified")

  function updateItem(value: string, patch: Partial<VerifyItem>) {
    setItems((prev) => prev.map((i) => (i.value === value ? { ...i, ...patch } : i)))
  }

  async function sendCode(item: VerifyItem) {
    updateItem(item.value, { status: "sending", error: null, otp: ["", "", "", "", "", ""] })
    try {
      if (item.kind === "email") {
        await api.post("/assets/email/otp/request", { email: item.value })
      } else {
        await api.post("/assets/phone/otp/request", { phone: item.value })
      }
      updateItem(item.value, { status: "awaiting_code" })
      toast.info(`Code sent to ${item.value}`)
    } catch (err) {
      const msg = err instanceof ApiRequestError ? err.detail : "Failed to send code."
      updateItem(item.value, { status: "error", error: msg })
      toast.error(msg)
    }
  }

  async function submitOtp(item: VerifyItem, code: string) {
    updateItem(item.value, { status: "verifying" })
    try {
      if (item.kind === "email") {
        await api.post<AssetOut>("/assets/email/otp/verify", { email: item.value, code })
      } else {
        await api.post<AssetOut>("/assets/phone/otp/verify", { phone: item.value, code })
      }
      updateItem(item.value, { status: "verified" })
      toast.success(`${item.value} verified`)
    } catch (err) {
      const msg = err instanceof ApiRequestError ? err.detail : "Invalid code."
      updateItem(item.value, { status: "awaiting_code", error: msg, otp: ["", "", "", "", "", ""] })
      toast.error(msg)
      setTimeout(() => otpRefs.current[item.value]?.[0]?.focus(), 50)
    }
  }

  function handleOtpChange(item: VerifyItem, index: number, inputVal: string) {
    if (item.status === "verifying" || item.status === "verified") return

    const cleaned = inputVal.replace(/\D/g, "")

    if (cleaned.length > 1) {
      const digits = cleaned.slice(0, 6).split("")
      const next = [...item.otp]
      digits.forEach((d, i) => { if (i < 6) next[i] = d })
      updateItem(item.value, { otp: next })
      otpRefs.current[item.value]?.[Math.min(digits.length, 5)]?.focus()
      if (digits.length === 6) submitOtp(item, digits.join(""))
      return
    }

    const next = [...item.otp]
    next[index] = cleaned
    updateItem(item.value, { otp: next })

    if (cleaned && index < 5) otpRefs.current[item.value]?.[index + 1]?.focus()
    if (next.every((d) => d !== "") && next.join("").length === 6) {
      submitOtp(item, next.join(""))
    }
  }

  function handleOtpKeyDown(item: VerifyItem, index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !item.otp[index] && index > 0) {
      otpRefs.current[item.value]?.[index - 1]?.focus()
    }
  }

  function handleContinue() {
    setPendingEmailVerifications([])
    setPendingPhoneVerifications([])
    router.push("/onboarding/scan")
  }

  function handleBack() {
    router.push("/onboarding/identity")
  }

  if (items.length === 0) return null

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={1} />
      </div>

      <div className="w-full max-w-lg">
        <div className="mb-4">
          <Button
            type="button"
            variant="ghost"
            className="px-0 text-slate-400 hover:bg-transparent hover:text-slate-200"
            onClick={handleBack}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to identity details
          </Button>
        </div>

        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 mb-5">
            <Mail className="w-7 h-7 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Verify your identity details</h1>
          <p className="text-slate-400 text-sm">
            We need to confirm you own each item before scanning it.
            Enter the 6-digit code for each address or number.
          </p>
        </div>

        <div className="space-y-4">
          {items.map((item) => (
            <div
              key={item.value}
              className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5"
            >
              {/* Header row */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {item.status === "verified" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : item.kind === "phone" ? (
                    <Phone className="w-4 h-4 text-slate-400 shrink-0" />
                  ) : (
                    <Mail className="w-4 h-4 text-slate-400 shrink-0" />
                  )}
                  <span className="text-sm font-medium text-slate-200 truncate">{item.value}</span>
                </div>
                {item.status === "verified" && (
                  <span className="text-xs text-emerald-400 font-medium">Verified</span>
                )}
              </div>

              {item.status === "pending" && (
                <Button
                  size="sm"
                  className="w-full"
                  onClick={() => sendCode(item)}
                >
                  Send verification code
                </Button>
              )}

              {item.status === "sending" && (
                <div className="flex items-center justify-center gap-2 text-sm text-slate-400 py-1">
                  <Loader2 className="w-4 h-4 animate-spin" /> Sending…
                </div>
              )}

              {item.kind === "phone" && item.status === "awaiting_code" && (
                <p className="text-xs text-slate-500 text-center mb-3">
                  Check your backend console for the verification code.
                </p>
              )}

              {(item.status === "awaiting_code" || item.status === "verifying") && (
                <div className="space-y-3">
                  <div className="flex gap-2 justify-center">
                    {item.otp.map((digit, i) => (
                      <input
                        key={i}
                        ref={(el) => {
                          if (!otpRefs.current[item.value]) otpRefs.current[item.value] = []
                          otpRefs.current[item.value][i] = el
                        }}
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={digit}
                        autoFocus={i === 0 && item.status === "awaiting_code"}
                        onChange={(e) => handleOtpChange(item, i, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(item, i, e)}
                        disabled={item.status === "verifying"}
                        className="w-10 h-12 rounded-lg border border-slate-700 bg-slate-800 text-center text-lg font-semibold text-white
                                   focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
                                   disabled:opacity-50 transition-all"
                      />
                    ))}
                  </div>

                  {item.status === "verifying" && (
                    <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
                      <Loader2 className="w-3 h-3 animate-spin" /> Verifying…
                    </div>
                  )}

                  {item.error && (
                    <p className="text-xs text-red-400 text-center">{item.error}</p>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full text-slate-500 hover:text-slate-300 hover:bg-slate-700 text-xs"
                    onClick={() => sendCode(item)}
                    disabled={item.status === "verifying"}
                  >
                    <RotateCcw className="w-3 h-3 mr-1" /> Resend code
                  </Button>
                </div>
              )}

              {item.status === "error" && (
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
                  onClick={() => sendCode(item)}
                >
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Try again
                </Button>
              )}
            </div>
          ))}
        </div>

        {allVerified && (
          <div className="mt-6 flex justify-end">
            <Button size="lg" className="gap-2 px-8" onClick={handleContinue}>
              Continue to scan <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        )}

        {!allVerified && (
          <p className="text-center text-xs text-slate-600 mt-6">
            Verify all addresses above to continue to your scan.
          </p>
        )}
      </div>
    </div>
  )
}
