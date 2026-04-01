"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

export interface OnboardingIdentity {
  firstName: string
  lastName: string
  phone: string
  usernames: string[]
  emailDomains: string[]
}

interface OnboardingState {
  /** Persisted: marks the user has completed onboarding at least once */
  completed: boolean
  identity: OnboardingIdentity | null
  scanId: string | null
  /** Additional emails entered during identity step that need OTP verification */
  pendingEmailVerifications: string[]
  /** Phone number entered during identity step that needs OTP verification */
  pendingPhoneVerifications: string[]

  setCompleted: (value: boolean) => void
  setIdentity: (identity: OnboardingIdentity) => void
  setScanId: (id: string) => void
  setPendingEmailVerifications: (emails: string[]) => void
  setPendingPhoneVerifications: (phones: string[]) => void
  reset: () => void
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      completed: false,
      identity: null,
      scanId: null,
      pendingEmailVerifications: [],
      pendingPhoneVerifications: [],

      setCompleted: (value) => set({ completed: value }),
      setIdentity: (identity) => set({ identity }),
      setScanId: (id) => set({ scanId: id }),
      setPendingEmailVerifications: (emails) => set({ pendingEmailVerifications: emails }),
      setPendingPhoneVerifications: (phones) => set({ pendingPhoneVerifications: phones }),
      reset: () => set({ completed: false, identity: null, scanId: null, pendingEmailVerifications: [], pendingPhoneVerifications: [] }),
    }),
    {
      name: "zima-onboarding",
      // Only persist the `completed` flag — identity is session-only for privacy
      partialize: (state) => ({ completed: state.completed }),
    },
  ),
)
