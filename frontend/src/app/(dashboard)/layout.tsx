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
  const completed = useOnboardingStore((s) => s.completed)

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/sign-in")
    } else if (!completed) {
      router.replace("/onboarding")
    }
  }, [isAuthenticated, completed, router])

  if (!isAuthenticated || !completed) return null

  return <DashboardShell>{children}</DashboardShell>
}
