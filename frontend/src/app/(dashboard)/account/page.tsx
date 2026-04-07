"use client"

import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { useRouter } from "next/navigation"
import {
  User,
  Download,
  Trash2,
  CreditCard,
  ClipboardList,
  Loader2,
  ShieldAlert,
} from "lucide-react"
import { format, parseISO } from "date-fns"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useAuthStore } from "@/lib/store/auth"
import type {
  AccountResponse,
  AuditLogResponse,
  BillingStatusResponse,
  CheckoutSessionResponse,
  PortalSessionResponse,
  GdprExportResponse,
  MessageResponse,
} from "@/types/api"

// ─── Billing section ──────────────────────────────────────────────────────────

function BillingSection() {
  const { data: billing, isLoading } = useQuery({
    queryKey: ["billing"],
    queryFn: () => api.get<BillingStatusResponse>("/billing/status"),
  })

  const { mutate: openCheckout, isPending: checkoutPending } = useMutation({
    mutationFn: () => api.post<CheckoutSessionResponse>("/billing/checkout"),
    onSuccess: (data) => { window.location.href = data.url },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Could not start checkout.")
    },
  })

  const { mutate: openPortal, isPending: portalPending } = useMutation({
    mutationFn: () => api.post<PortalSessionResponse>("/billing/portal"),
    onSuccess: (data) => { window.location.href = data.url },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Could not open billing portal.")
    },
  })

  const isPro = billing?.plan && billing.plan !== "free"

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <CreditCard className="h-4 w-4 text-primary" /> Billing
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <Skeleton className="h-12 w-48" />
        ) : billing ? (
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium capitalize">{billing.plan ?? "Free"} plan</p>
                <Badge variant={isPro ? "default" : "secondary"} className="text-xs">
                  {billing.status ?? "active"}
                </Badge>
              </div>
              {billing.current_period_end && (
                <p className="text-xs text-muted-foreground">
                  {billing.cancel_at_period_end ? "Cancels" : "Renews"} on{" "}
                  {format(parseISO(billing.current_period_end), "PPP")}
                </p>
              )}
            </div>
            {isPro ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => openPortal()}
                disabled={portalPending}
              >
                {portalPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Manage subscription"}
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => openCheckout()}
                disabled={checkoutPending}
              >
                {checkoutPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Upgrade to Pro"}
              </Button>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Billing information unavailable.</p>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Audit log section ────────────────────────────────────────────────────────

function AuditLogSection() {
  const [offset, setOffset] = useState(0)
  const limit = 15

  const { data, isLoading } = useQuery({
    queryKey: ["audit", { offset, limit }],
    queryFn: () => api.get<AuditLogResponse>(`/account/audit-log?limit=${limit}&offset=${offset}`),
  })

  const events = data?.events ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-primary" /> Audit Log
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : events.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">No events recorded yet.</p>
        ) : (
          <div>
            <ul className="divide-y divide-border text-sm">
              {events.map((ev) => (
                <li key={ev.event_id} className="flex items-start gap-3 py-2.5">
                  <div className="flex-1 min-w-0">
                    <span className="font-medium">{ev.event_type}</span>
                    {ev.ip_address && (
                      <span className="text-muted-foreground ml-2 text-xs">from {ev.ip_address}</span>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {format(parseISO(ev.created_at), "MMM d, HH:mm")}
                  </span>
                </li>
              ))}
            </ul>
            <div className="flex items-center justify-between mt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={events.length < limit}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── GDPR / data section ──────────────────────────────────────────────────────

function DataSection({ onDeleteAccount }: { onDeleteAccount: () => void }) {
  const [exporting, setExporting] = useState(false)

  async function handleExport() {
    setExporting(true)
    try {
      const data = await api.get<GdprExportResponse>("/account/export")
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `zima-export-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success("Export downloaded.")
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.detail : "Export failed.")
    } finally {
      setExporting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-primary" /> Privacy & Data
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Export your data</p>
            <p className="text-xs text-muted-foreground">Download all your signals, findings, and scores as JSON.</p>
          </div>
          <Button size="sm" variant="outline" onClick={handleExport} disabled={exporting}>
            {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Export
          </Button>
        </div>

        <Separator />

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <a href="/privacy" className="hover:text-foreground transition-colors underline underline-offset-2">
            Privacy Policy
          </a>
          <a href="/terms" className="hover:text-foreground transition-colors underline underline-offset-2">
            Terms of Service
          </a>
        </div>

        <Separator />

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-red-600">Delete account</p>
            <p className="text-xs text-muted-foreground">Permanently delete your account and all data. This cannot be undone.</p>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="destructive">
                <Trash2 className="h-4 w-4" /> Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete account?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will permanently erase all your data — scans, findings, signals, and scores.
                  This action cannot be reversed.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  onClick={onDeleteAccount}
                >
                  Yes, delete my account
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AccountPage() {
  const router = useRouter()
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated)

  const { data: account, isLoading } = useQuery({
    queryKey: ["account"],
    queryFn: () => api.get<AccountResponse>("/account"),
  })

  const { mutate: deleteAccount, isPending: deleting } = useMutation({
    mutationFn: () => api.delete<MessageResponse>("/account"),
    onSuccess: () => {
      toast.success("Account deleted.")
      setAuthenticated(false)
      router.push("/sign-in")
    },
    onError: (err) => {
      toast.error(err instanceof ApiRequestError ? err.detail : "Deletion failed.")
    },
  })

  const primaryEmail = account?.assets.find(
    (a) => a.entity_type === "email" && a.is_verified,
  )?.value

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Account</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Manage your identity, billing, and data
        </p>
      </div>

      {/* Profile summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4 text-primary" /> Profile
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-10 w-56" />
          ) : (
            <div className="space-y-1">
              {primaryEmail && (
                <p className="text-sm font-medium">{primaryEmail}</p>
              )}
              {account?.assets.map((a) => (
                <div key={a.asset_id} className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="capitalize">{a.entity_type}</span>
                  <span className="font-medium text-foreground">{a.value}</span>
                  {a.is_verified && (
                    <Badge variant="outline" className="text-xs text-green-600 border-green-200">verified</Badge>
                  )}
                </div>
              ))}
              {account?.user && (
                <p className="text-xs text-muted-foreground mt-2">
                  Member since {format(parseISO(account.user.created_at), "PPP")}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <BillingSection />
      <AuditLogSection />
      <DataSection onDeleteAccount={() => deleteAccount()} />
    </div>
  )
}
