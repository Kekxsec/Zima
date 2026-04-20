"use client"

import { useState, useRef, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { toast } from "sonner"
import { Shield, Loader2, ArrowRight, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api, ApiRequestError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/store/auth"
import { useOnboardingStore } from "@/lib/store/onboarding"
import { sanitizeNext } from "@/proxy"
import type { MessageResponse, ScanListResponse } from "@/types/api"

type Step = "email" | "otp"

function SignInForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const rawNext = searchParams.get("next")
  const next = sanitizeNext(rawNext)
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated)
  const resetOnboarding = useOnboardingStore((s) => s.reset)
  const setCompleted = useOnboardingStore((s) => s.setCompleted)
  const setScanId = useOnboardingStore((s) => s.setScanId)

  const [step, setStep] = useState<Step>("email")
  const [email, setEmail] = useState("")
  const [otp, setOtp] = useState(["", "", "", "", "", ""])
  const [loading, setLoading] = useState(false)

  const otpRefs = useRef<(HTMLInputElement | null)[]>([])

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    try {
      await api.post<MessageResponse>("/auth/otp/request", { email: email.trim() })
      setStep("otp")
      toast.info("Check your inbox — a 6-digit code is on its way.")
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.detail : "Something went wrong.")
    } finally {
      setLoading(false)
    }
  }

  async function submitOtp(code: string) {
    setLoading(true)
    try {
      await api.post<MessageResponse>("/auth/otp/verify", {
        email: email.trim(),
        code,
      })

      // Fetch scan history BEFORE mutating the store so we can compute the
      // target route atomically. setAuthenticated fires after all state is set.
      let targetRoute = "/onboarding"
      try {
        const scanHistory = await api.get<ScanListResponse>("/scans/?limit=20")
        const scans = scanHistory.scans ?? []
        const hasCompletedScan = scans.some((scan) => scan.status === "completed")
        const activeScan =
          scans.find((scan) => scan.status === "running") ??
          scans.find((scan) => scan.status === "pending") ??
          null

        if (hasCompletedScan) {
          setCompleted(true)
          setScanId(activeScan?.id ?? null)
          targetRoute = next
        } else if (activeScan) {
          resetOnboarding()
          setScanId(activeScan.id)
          targetRoute = "/onboarding/scan"
        } else {
          resetOnboarding()
        }
      } catch {
        // Can't confirm prior scans — route to onboarding without wiping
        // any existing store state (avoids discarding an in-progress scan id).
      }

      // Always honour an explicit ?next param — e.g. /connect-extension from the browser extension
      if (rawNext) targetRoute = next

      setAuthenticated(true)
      router.push(targetRoute)
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.detail : "Invalid code.")
      setOtp(["", "", "", "", "", ""])
      otpRefs.current[0]?.focus()
    } finally {
      setLoading(false)
    }
  }

  function handleOtpChange(index: number, value: string) {
    const cleaned = value.replace(/\D/g, "")
    if (cleaned.length > 1) {
      const digits = cleaned.slice(0, 6).split("")
      const next = [...otp]
      digits.forEach((d, i) => { if (i < 6) next[i] = d })
      setOtp(next)
      otpRefs.current[Math.min(digits.length, 5)]?.focus()
      if (digits.length === 6) submitOtp(digits.join(""))
      return
    }

    const next = [...otp]
    next[index] = cleaned
    setOtp(next)

    if (cleaned && index < 5) otpRefs.current[index + 1]?.focus()
    if (next.every((d) => d !== "") && next.join("").length === 6) {
      submitOtp(next.join(""))
    }
  }

  function handleOtpKeyDown(index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus()
    }
  }

  return (
    <div className="zima-stage-shell min-h-screen flex items-center justify-center px-4">
      {/* Subtle background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-primary/5 blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 mb-5">
            <Shield className="w-7 h-7 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Zima</h1>
          <p className="text-sm text-slate-400 mt-1">Identity protection platform</p>
        </div>

        {/* Card */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-8 backdrop-blur-sm">
          {step === "email" ? (
            <>
              <h2 className="text-lg font-semibold text-white mb-1">Sign in</h2>
              <p className="text-sm text-slate-400 mb-6">
                We&apos;ll send a one-time code to your email.
              </p>
              <form onSubmit={handleEmailSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-slate-300">Email address</Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoFocus
                    className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-primary"
                  />
                </div>
                <Button type="submit" className="w-full gap-2" disabled={loading}>
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      Continue <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>
            </>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-white mb-1">Enter your code</h2>
              <p className="text-sm text-slate-400 mb-6">
                Sent to{" "}
                <span className="font-medium text-slate-200">{email}</span>
              </p>

              <div className="flex gap-2 justify-center mb-6">
                {otp.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => { otpRefs.current[i] = el }}
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={digit}
                    autoFocus={i === 0}
                    onChange={(e) => handleOtpChange(i, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(i, e)}
                    disabled={loading}
                    className="w-11 h-13 rounded-lg border border-slate-700 bg-slate-800 text-center text-lg font-semibold text-white
                               focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
                               disabled:opacity-50 transition-all"
                  />
                ))}
              </div>

              {loading && (
                <div className="flex items-center justify-center gap-2 text-sm text-slate-400 mb-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Verifying…
                </div>
              )}

              <Button
                variant="ghost"
                size="sm"
                className="w-full text-slate-400 hover:text-slate-200 hover:bg-slate-700"
                onClick={() => {
                  setStep("email")
                  setOtp(["", "", "", "", "", ""])
                }}
                disabled={loading}
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Use a different email
              </Button>
            </>
          )}
        </div>

        <p className="text-center text-xs text-slate-500 mt-6">
          No password, ever. Codes expire in 10 minutes.
        </p>
      </div>
    </div>
  )
}

export default function SignInPage() {
  return (
    <Suspense>
      <SignInForm />
    </Suspense>
  )
}
