"use client"

import { useRouter } from "next/navigation"
import { Shield, Eye, AlertTriangle, Lock, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
]

const FEATURES = [
  {
    icon: Eye,
    title: "Data Breach Detection",
    description: "Find out if your email has appeared in known data breaches and leaked credential databases.",
  },
  {
    icon: AlertTriangle,
    title: "Exposure Signals",
    description: "Identify where your personal information is publicly exposed across the internet.",
  },
  {
    icon: Lock,
    title: "Actionable Remediation",
    description: "Receive step-by-step guidance to reduce your attack surface and secure your accounts.",
  },
]

export default function WelcomePage() {
  const router = useRouter()

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      {/* Stepper */}
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={0} />
      </div>

      {/* Hero */}
      <div className="flex flex-col items-center text-center max-w-lg mb-12">
        <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/20 border border-primary/30 mb-6">
          <Shield className="w-8 h-8 text-primary" />
        </div>
        <h1 className="text-3xl font-bold text-white tracking-tight mb-3">
          Welcome to Zima
        </h1>
        <p className="text-slate-400 text-base leading-relaxed">
          Let&apos;s take five minutes to scan your digital identity and understand your current exposure.
          We&apos;ll check for breaches, leaked credentials, and public data tied to your email.
        </p>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl w-full mb-12">
        {FEATURES.map(({ icon: Icon, title, description }) => (
          <div
            key={title}
            className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-5"
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 mb-3">
              <Icon className="w-5 h-5 text-primary" />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1.5">{title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
          </div>
        ))}
      </div>

      <Button
        size="lg"
        className="gap-2 px-8"
        onClick={() => router.push("/onboarding/identity")}
      >
        Get started <ArrowRight className="w-4 h-4" />
      </Button>

      <p className="mt-4 text-xs text-slate-600">
        Your data is never sold or shared with third parties.
      </p>
    </div>
  )
}
