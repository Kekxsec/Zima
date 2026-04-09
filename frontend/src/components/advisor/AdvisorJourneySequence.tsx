"use client"

import Link from "next/link"
import { ArrowRight, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type JourneyStage = {
  title: string
  description: string
  state: "done" | "current" | "upcoming"
}

export function AdvisorJourneySequence({
  stages,
  actionHref,
  actionLabel,
  title = "Your simple plan",
  description = "Take one step at a time. A step only changes when the real work is complete.",
}: {
  stages: JourneyStage[]
  actionHref?: string
  actionLabel?: string
  title?: string
  description?: string
}) {
  return (
    <Card className="border-border bg-card/75">
      <CardContent className="p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Process flow
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">{title}</span>
              {" "}
              {description}
            </p>
          </div>
          {actionHref && actionLabel && (
            <Button size="sm" className="gap-2" asChild>
              <Link href={actionHref}>
                {actionLabel}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          )}
        </div>

        <div className="mt-5 space-y-3">
          {stages.map((stage, index) => (
            <div
              key={stage.title}
              className={cn(
                "rounded-xl border px-4 py-4",
                stage.state === "done"
                  ? "border-emerald-500/25 bg-emerald-500/10"
                  : stage.state === "current"
                  ? "border-primary/30 bg-primary/10"
                  : "border-border bg-background/70",
              )}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold",
                    stage.state === "done"
                      ? "border-emerald-500/25 bg-emerald-500/15 text-emerald-200"
                      : stage.state === "current"
                      ? "border-primary/20 bg-primary/15 text-primary"
                      : "border-border bg-muted/70 text-muted-foreground",
                  )}
                >
                  {stage.state === "done" ? <CheckCircle2 className="h-4 w-4" /> : index + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <p className="text-sm font-semibold text-foreground">{stage.title}</p>
                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                      {stage.state === "done" ? "Done" : stage.state === "current" ? "Now" : "Later"}
                    </p>
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{stage.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
