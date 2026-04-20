"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import type { ReactNode } from "react"
import { useAuthStore } from "@/lib/store/auth"

/** Onboarding pages — full screen, no sidebar, requires authentication */
export default function OnboardingLayout({ children }: { children: ReactNode }) {
  const router = useRouter()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const hasHydrated = useAuthStore((s) => s._hasHydrated)

  useEffect(() => {
    if (hasHydrated && !isAuthenticated) {
      router.replace("/sign-in")
    }
  }, [hasHydrated, isAuthenticated, router])

  if (!hasHydrated || !isAuthenticated) return null

  return (
    <div className="zima-stage-shell zima-deep-theme min-h-screen">
      {children}
    </div>
  )
}
