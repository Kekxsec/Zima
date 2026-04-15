"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { toast } from "sonner"
import {
  Shield,
  LayoutDashboard,
  AlertTriangle,
  Radio,
  ScanLine,
  BarChart2,
  Laptop,
  HardDrive,
  Mailbox,
  MonitorSmartphone,
  User,
  LogOut,
  Menu,
  X,
  Plug,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { api, ApiRequestError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/store/auth"
import { useOnboardingStore } from "@/lib/store/onboarding"
import type { MessageResponse } from "@/types/api"

const NAV_PRIMARY = [
  { label: "Your plan", href: "/dashboard", icon: LayoutDashboard },
  { label: "Accounts", href: "/accounts", icon: Mailbox },
  { label: "Priorities", href: "/findings", icon: AlertTriangle },
  { label: "Device", href: "/device", icon: HardDrive },
  { label: "Browser", href: "/browser", icon: Laptop },
]

const NAV_SECONDARY = [
  { label: "Progress", href: "/scores", icon: BarChart2 },
  { label: "Technical details", href: "/signals", icon: Radio },
  { label: "Recent scans", href: "/scans", icon: ScanLine },
]

const NAV_SETTINGS = [
  { label: "Companion", href: "/companion", icon: MonitorSmartphone },
  { label: "Integrations", href: "/integrations", icon: Plug },
  { label: "Account", href: "/account", icon: User },
]

const ALL_NAV = [...NAV_PRIMARY, ...NAV_SECONDARY, ...NAV_SETTINGS]

type NavItemProps = {
  href: string
  icon: React.ElementType
  label: string
  active: boolean
  onClick?: () => void
}

function NavItem({ href, icon: Icon, label, active, onClick }: NavItemProps) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "group flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm font-medium transition-all",
        active
          ? "border-sky-400/35 bg-sky-400/12 text-white shadow-[0_0_0_1px_rgba(56,189,248,0.08)]"
          : "border-transparent text-slate-400 hover:border-slate-700 hover:bg-white/5 hover:text-slate-200",
      )}
    >
      <Icon
        className={cn(
          "h-[18px] w-[18px] shrink-0 transition-colors",
          active ? "text-sky-400" : "text-slate-500 group-hover:text-slate-300",
        )}
      />
      {label}
    </Link>
  )
}

function NavSection({
  label,
  items,
  pathname,
  onNavigate,
}: {
  label: string
  items: typeof NAV_PRIMARY
  pathname: string
  onNavigate?: () => void
}) {
  return (
    <div className="space-y-0.5">
      <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
        {label}
      </p>
      {items.map((item) => (
        <NavItem
          key={item.href}
          {...item}
          active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
          onClick={onNavigate}
        />
      ))}
    </div>
  )
}

function Sidebar({
  onNavigate,
  onLogout,
}: {
  onNavigate?: () => void
  onLogout: () => void
}) {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col border-r border-white/[0.06] bg-[#091321]/85 backdrop-blur-xl">
      {/* Brand */}
      <div className="flex items-center gap-3 border-b border-white/[0.07] px-5 py-[18px]">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500 shadow-lg shadow-sky-500/30">
          <Shield className="h-4 w-4 text-white" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-bold tracking-tight text-white">Zima</p>
          <p className="text-[11px] text-slate-500">Personal Cyber Advisor</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-5">
        <NavSection label="Your next steps" items={NAV_PRIMARY} pathname={pathname} onNavigate={onNavigate} />
        <NavSection label="More detail" items={NAV_SECONDARY} pathname={pathname} onNavigate={onNavigate} />
        <NavSection label="Settings" items={NAV_SETTINGS} pathname={pathname} onNavigate={onNavigate} />
      </nav>

      {/* Sign out */}
      <div className="border-t border-white/[0.07] px-3 py-4">
        <button
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-md border-l-2 border-transparent px-3 py-2
                     text-sm font-medium text-slate-500 transition-all
                     hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400"
        >
          <LogOut className="h-[18px] w-[18px] shrink-0" />
          Sign out
        </button>
      </div>
    </div>
  )
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated)
  const resetOnboarding = useOnboardingStore((s) => s.reset)
  const [mobileOpen, setMobileOpen] = useState(false)
  const mountedRef = useRef(true)
  const logoutControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      logoutControllerRef.current?.abort()
    }
  }, [])

  const currentPage = ALL_NAV.find(
    (n) => pathname === n.href || pathname.startsWith(`${n.href}/`),
  )

  async function handleLogout() {
    const controller = new AbortController()
    logoutControllerRef.current = controller
    try {
      await api.post<MessageResponse>("/auth/logout")
    } catch (err) {
      if (!mountedRef.current) return
      if (!(err instanceof ApiRequestError && err.status === 401)) {
        toast.error("Sign-out failed — please try again.")
        return
      }
    }
    if (!mountedRef.current || controller.signal.aborted) return
    setAuthenticated(false)
    resetOnboarding()
    router.push("/sign-in")
  }

  return (
    <div className="zima-deep-theme zima-stage-shell flex h-screen overflow-hidden text-foreground">
      {/* Desktop sidebar */}
      <aside className="hidden w-56 shrink-0 md:flex md:flex-col">
        <Sidebar onLogout={handleLogout} />
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative z-50 flex h-full w-64 flex-col shadow-2xl">
            <Sidebar onNavigate={() => setMobileOpen(false)} onLogout={handleLogout} />
          </aside>
        </div>
      )}

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border/80 bg-card/80 px-6 backdrop-blur-xl">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>

          {/* Mobile brand */}
          <div className="flex items-center gap-2.5 md:hidden">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-sky-500">
              <Shield className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="text-sm font-bold text-white">Zima</span>
          </div>

          {/* Desktop breadcrumb */}
          {currentPage && (
            <div className="hidden md:flex md:flex-col">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Zima
              </span>
              <span className="text-sm font-semibold text-foreground">{currentPage.label}</span>
            </div>
          )}
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto bg-transparent p-6 md:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
