"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { format, parseISO } from "date-fns"
import {
  CheckCircle2,
  XCircle,
  Loader2,
  KeyRound,
  Unplug,
  BadgeCheck,
  ExternalLink,
} from "lucide-react"
import { api, ApiRequestError } from "@/lib/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
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
import type {
  IntegrationListResponse,
  Integration,
  IntegrationVerifyResponse,
} from "@/types/api"

// ─── Provider metadata ────────────────────────────────────────────────────────

const PROVIDER_META: Record<
  string,
  { label: string; description: string; docsUrl: string }
> = {
  simplelogin: {
    label: "SimpleLogin",
    description:
      "Generate alias email addresses to protect your real inbox. Zima can use your SimpleLogin API key to list your mailboxes for deeper account discovery.",
    docsUrl: "https://simplelogin.io/docs/api/",
  },
  addy_io: {
    label: "Addy.io",
    description:
      "Open-source email alias and forwarding service. Connect your Addy.io API key so Zima can surface aliases that may be exposed in breaches.",
    docsUrl: "https://addy.io/help/api/",
  },
}

// ─── Connect dialog ───────────────────────────────────────────────────────────

function ConnectDialog({
  provider,
  open,
  onClose,
}: {
  provider: string
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const meta = PROVIDER_META[provider]
  const [apiKey, setApiKey] = useState("")

  const { mutate: connect, isPending } = useMutation({
    mutationFn: () =>
      api.put(`/integrations/${provider}`, { api_key: apiKey }),
    onSuccess: () => {
      toast.success(`${meta?.label ?? provider} connected.`)
      qc.invalidateQueries({ queryKey: ["integrations"] })
      setApiKey("")
      onClose()
    },
    onError: (err) => {
      toast.error(
        err instanceof ApiRequestError ? err.detail : "Failed to connect.",
      )
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (apiKey.trim()) connect()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) { setApiKey(""); onClose() }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect {meta?.label ?? provider}</DialogTitle>
          <DialogDescription>{meta?.description}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              placeholder="Paste your API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              autoComplete="off"
            />
          </div>
          {meta?.docsUrl && (
            <a
              href={meta.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-sky-500 hover:text-sky-400"
            >
              How to get your API key <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" onClick={() => { setApiKey(""); onClose() }}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending || !apiKey.trim()}>
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
              Connect
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Integration card ─────────────────────────────────────────────────────────

function IntegrationCard({ integration }: { integration: Integration }) {
  const qc = useQueryClient()
  const [connectOpen, setConnectOpen] = useState(false)
  const meta = PROVIDER_META[integration.provider]

  const { mutate: disconnect, isPending: disconnecting } = useMutation({
    mutationFn: () => api.delete(`/integrations/${integration.provider}`),
    onSuccess: () => {
      toast.success(`${meta?.label ?? integration.provider} disconnected.`)
      qc.invalidateQueries({ queryKey: ["integrations"] })
    },
    onError: (err) => {
      toast.error(
        err instanceof ApiRequestError ? err.detail : "Failed to disconnect.",
      )
    },
  })

  const { mutate: verify, isPending: verifying } = useMutation({
    mutationFn: () =>
      api.post<IntegrationVerifyResponse>(
        `/integrations/${integration.provider}/verify`,
      ),
    onSuccess: (data) => {
      if (data.valid) {
        toast.success("API key is valid.")
      } else {
        toast.error(`Key invalid: ${data.detail}`)
      }
    },
    onError: (err) => {
      toast.error(
        err instanceof ApiRequestError ? err.detail : "Verification failed.",
      )
    },
  })

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-0.5">
              <CardTitle className="text-base flex items-center gap-2">
                {meta?.label ?? integration.provider}
                {integration.connected ? (
                  <Badge
                    variant="outline"
                    className="text-xs text-green-600 border-green-200 bg-green-50"
                  >
                    <CheckCircle2 className="h-3 w-3 mr-1" /> Connected
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs text-slate-500">
                    <XCircle className="h-3 w-3 mr-1" /> Not connected
                  </Badge>
                )}
              </CardTitle>
              {integration.connected && integration.connected_at && (
                <p className="text-xs text-muted-foreground">
                  Connected {format(parseISO(integration.connected_at), "PPP")}
                </p>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {meta?.description ?? `Connect your ${integration.provider} account.`}
          </p>

          <div className="flex items-center gap-2 flex-wrap">
            {integration.connected ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={verifying}
                  onClick={() => verify()}
                >
                  {verifying ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <BadgeCheck className="h-3.5 w-3.5" />
                  )}
                  Verify key
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  disabled={disconnecting || verifying}
                  onClick={() => setConnectOpen(true)}
                >
                  <KeyRound className="h-3.5 w-3.5" /> Update key
                </Button>

                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-500 hover:text-red-600 hover:bg-red-50"
                      disabled={disconnecting}
                    >
                      {disconnecting ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Unplug className="h-3.5 w-3.5" />
                      )}
                      Disconnect
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        Disconnect {meta?.label ?? integration.provider}?
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        Your stored API key will be permanently deleted. Zima will
                        no longer query this integration during scans.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        onClick={() => disconnect()}
                      >
                        Disconnect
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </>
            ) : (
              <Button size="sm" onClick={() => setConnectOpen(true)}>
                <KeyRound className="h-3.5 w-3.5" /> Connect
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <ConnectDialog
        provider={integration.provider}
        open={connectOpen}
        onClose={() => setConnectOpen(false)}
      />
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => api.get<IntegrationListResponse>("/integrations"),
  })

  const integrations = data?.integrations ?? []
  const connectedCount = integrations.filter((integration) => integration.connected).length

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Integrations</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          Integrations are optional. Connect alias services to give Zima broader scan coverage.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(2)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : integrations.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No integrations available.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {integrations.map((i) => (
            <IntegrationCard key={i.provider} integration={i} />
          ))}
        </div>
      )}
    </div>
  )
}
