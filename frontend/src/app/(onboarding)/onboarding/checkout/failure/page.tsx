"use client"

import Link from "next/link"
import { AlertTriangle, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

export default function CheckoutFailurePage() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl items-center px-4 py-12">
      <Card className="w-full">
        <CardContent className="space-y-5 p-8 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/10">
            <AlertTriangle className="h-7 w-7 text-amber-400" />
          </div>
          <div className="space-y-2">
            <h1 className="text-2xl font-bold">Checkout was not completed</h1>
            <p className="text-sm text-muted-foreground">
              No payment was taken. You can return to Zima and try again whenever you are ready.
            </p>
          </div>
          <Button asChild className="gap-2">
            <Link href="/onboarding/checkout">
              Try checkout again
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
