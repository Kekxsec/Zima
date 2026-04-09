"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

interface AuthState {
  /** true once the user has successfully verified OTP (cookie is set) */
  isAuthenticated: boolean
  /** true once zustand has finished rehydrating from localStorage */
  _hasHydrated: boolean
  setAuthenticated: (value: boolean) => void
  setHasHydrated: (value: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      _hasHydrated: false,
      setAuthenticated: (value) => set({ isAuthenticated: value }),
      setHasHydrated: (value) => set({ _hasHydrated: value }),
    }),
    {
      name: "zima-auth",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    },
  ),
)
