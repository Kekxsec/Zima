"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import type { ReactNode } from "react"
import { useAuthStore } from "@/lib/store/auth"

/** Onboarding pages — full screen, no sidebar, requires authentication */
export default function OnboardingLayout({ children }: { children: ReactNode }) {
  const router = useRouter()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/sign-in")
    }
  }, [isAuthenticated, router])

  if (!isAuthenticated) return null

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {children}
    </div>
  )
}
