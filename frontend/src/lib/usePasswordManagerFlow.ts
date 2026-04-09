"use client"

import { useCallback, useEffect, useState } from "react"

function storageKey(userId: string) {
  return `zima-password-manager-export:${userId}`
}

function readStorage(userId: string | undefined): boolean {
  if (typeof window === "undefined" || !userId) return false
  return window.localStorage.getItem(storageKey(userId)) === "done"
}

export function usePasswordManagerFlow(userId?: string) {
  const [exportCompleted, setExportCompleted] = useState(() => readStorage(userId))

  // Re-sync when userId changes (e.g. post-login hydration)
  useEffect(() => {
    setExportCompleted(readStorage(userId))
  }, [userId])

  const markExportCompleted = useCallback(() => {
    if (typeof window === "undefined" || !userId) return
    window.localStorage.setItem(storageKey(userId), "done")
    setExportCompleted(true)
  }, [userId])

  return { exportCompleted, markExportCompleted }
}
