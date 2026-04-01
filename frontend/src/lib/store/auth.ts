"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

interface AuthState {
  /** true once the user has successfully verified OTP (cookie is set) */
  isAuthenticated: boolean
  setAuthenticated: (value: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      setAuthenticated: (value) => set({ isAuthenticated: value }),
    }),
    {
      name: "zima-auth",
    },
  ),
)
