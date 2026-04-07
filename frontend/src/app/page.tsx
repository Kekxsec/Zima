"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Shield, ArrowRight, LogIn, Eye, AlertTriangle, Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/lib/store/auth"
import { useOnboardingStore } from "@/lib/store/onboarding"

const FEATURES = [
  {
    icon: Eye,
    title: "Breach Detection",
    description: "Know instantly if your email or credentials have appeared in a data breach.",
  },
  {
    icon: AlertTriangle,
    title: "Exposure Signals",
    description: "See exactly where your personal data is publicly visible across the internet.",
  },
  {
    icon: Lock,
    title: "Actionable Steps",
    description: "Get clear, prioritised guidance to reduce your attack surface.",
  },
]

export default function LandingPage() {
  const router = useRouter()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const completed = useOnboardingStore((s) => s.completed)

  useEffect(() => {
    if (isAuthenticated && completed) {
      router.replace("/dashboard")
    } else if (isAuthenticated && !completed) {
      router.replace("/onboarding")
    }
  }, [isAuthenticated, completed, router])

  // Don't flash the landing page while redirecting authenticated users
  if (isAuthenticated) return null

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col items-center justify-center px-4 py-16">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-primary/5 blur-3xl" />
      </div>

      <div className="relative flex flex-col items-center text-center max-w-2xl w-full">
        {/* Logo */}
        <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 mb-6">
          <Shield className="w-8 h-8 text-primary" />
        </div>

        <h1 className="text-4xl font-bold text-white tracking-tight mb-4">
          Welcome to Zima
        </h1>
        <p className="text-slate-400 text-lg leading-relaxed mb-10 max-w-lg">
          Your personal identity protection platform. Find out where you&apos;re exposed
          and take back control.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-3 mb-14 w-full sm:w-auto">
          <Button
            size="lg"
            className="gap-2 px-8 w-full sm:w-auto"
            onClick={() => router.push("/sign-in?mode=register")}
          >
            Get started <ArrowRight className="w-4 h-4" />
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="gap-2 px-8 w-full sm:w-auto border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
            onClick={() => router.push("/sign-in")}
          >
            <LogIn className="w-4 h-4" /> Sign in
          </Button>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-5 text-left"
            >
              <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 mb-3">
                <Icon className="w-4 h-4 text-primary" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-1">{title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>

        <p className="mt-8 text-xs text-slate-600">
          No password required. No data sold. Codes expire in 15 minutes.
        </p>

        <div className="mt-4 flex items-center gap-4 text-xs text-slate-700">
          <a href="/privacy" className="hover:text-slate-500 transition-colors">
            Privacy Policy
          </a>
          <span>·</span>
          <a href="/terms" className="hover:text-slate-500 transition-colors">
            Terms of Service
          </a>
        </div>
      </div>
    </div>
  )
}
