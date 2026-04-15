"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Loader2, ShieldCheck, Wallet } from "lucide-react"
import { toast } from "sonner"
import { api, ApiRequestError } from "@/lib/api/client"
import type { CheckoutSessionResponse } from "@/types/api"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export function CheckoutModal({
  tier = "pro",
  triggerLabel = "Start checkout",
}: {
  tier?: string
  triggerLabel?: string
}) {
  const [open, setOpen] = useState(false)

  const { mutate: startCheckout, isPending } = useMutation({
    mutationFn: () => api.post<CheckoutSessionResponse>(`/billing/checkout/${tier}`),
    onSuccess: (data) => {
      window.location.href = data.checkout_url
    },
    onError: (err) => {
      toast.error(
        err instanceof ApiRequestError
          ? err.detail
          : "Could not start checkout.",
      )
    },
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wallet className="h-4 w-4 text-primary" />
            Continue to secure checkout
          </DialogTitle>
          <DialogDescription>
            Zima uses Stripe Checkout for payment. Card details stay on Stripe,
            not inside the app.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4 text-sm">
          <div className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 h-4 w-4 text-emerald-400" />
            <p>Hosted Stripe form with bank-card and wallet support.</p>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 h-4 w-4 text-emerald-400" />
            <p>Returns you to Zima automatically after payment succeeds or fails.</p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Not now
          </Button>
          <Button onClick={() => startCheckout()} disabled={isPending}>
            {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Continue to Stripe
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
