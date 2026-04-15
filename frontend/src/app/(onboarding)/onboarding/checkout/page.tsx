"use client"

import Link from "next/link"
import { ArrowLeft, ShieldCheck, Wallet } from "lucide-react"
import { CheckoutModal } from "@/components/billing/CheckoutModal"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function CheckoutPage() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl items-center px-4 py-12">
      <div className="w-full space-y-6">
        <div className="space-y-2">
          <Button variant="ghost" asChild className="gap-2 px-0 text-muted-foreground">
            <Link href="/onboarding/results">
              <ArrowLeft className="h-4 w-4" />
              Back to results
            </Link>
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Checkout</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Finish payment in Stripe, then return to Zima to continue the audit workflow.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wallet className="h-4 w-4 text-primary" />
              Secure payment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm">
              <p className="font-medium">What happens next</p>
              <div className="mt-3 space-y-2 text-muted-foreground">
                <p className="flex items-start gap-2">
                  <ShieldCheck className="mt-0.5 h-4 w-4 text-emerald-400" />
                  Payment happens on Stripe-hosted checkout.
                </p>
                <p className="flex items-start gap-2">
                  <ShieldCheck className="mt-0.5 h-4 w-4 text-emerald-400" />
                  You return to Zima automatically after completion.
                </p>
              </div>
            </div>

            <CheckoutModal triggerLabel="Continue to Stripe" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
