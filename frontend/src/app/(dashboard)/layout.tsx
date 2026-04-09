"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { DashboardShell } from "@/components/layout/DashboardShell"
import { useAuthStore } from "@/lib/store/auth"
import { useOnboardingStore } from "@/lib/store/onboarding"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const hasHydrated = useAuthStore((s) => s._hasHydrated)
  const completed = useOnboardingStore((s) => s.completed)
  const scanId = useOnboardingStore((s) => s.scanId)
  const canAccessDashboard = completed || Boolean(scanId)

  useEffect(() => {
    if (!hasHydrated) return
    if (!isAuthenticated) {
      router.replace("/sign-in")
    } else if (!canAccessDashboard) {
      router.replace("/onboarding")
    }
  }, [hasHydrated, isAuthenticated, canAccessDashboard, router])

  if (!hasHydrated || !isAuthenticated || !canAccessDashboard) return null

  return <DashboardShell>{children}</DashboardShell>
}
