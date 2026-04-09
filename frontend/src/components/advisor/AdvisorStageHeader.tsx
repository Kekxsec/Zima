"use client"

import type { ReactNode } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type AdvisorStageStat = {
  label: string
  value: string
  detail?: string
}

export function AdvisorStageHeader({
  eyebrow,
  stageLabel,
  title,
  description,
  focus,
  outcome,
  actions,
  stats = [],
}: {
  eyebrow: string
  stageLabel: string
  title: string
  description: string
  focus: string
  outcome: string
  actions?: ReactNode
  stats?: AdvisorStageStat[]
}) {
  return (
    <Card className="border-primary/20 bg-card/80 shadow-[0_20px_60px_rgba(2,6,23,0.28)]">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-5 flex-wrap">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" className="rounded-full border border-primary/15 bg-primary/10 px-3 py-1 text-[11px] uppercase tracking-wider text-primary">
                {eyebrow}
              </Badge>
              <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                {stageLabel}
              </span>
            </div>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-foreground">{title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
            {actions && <div className="mt-4 flex items-center gap-3 flex-wrap">{actions}</div>}
          </div>

          <div className="min-w-[240px] max-w-sm rounded-2xl border border-border bg-background/70 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Current Focus
            </p>
            <p className="mt-2 text-sm font-semibold text-foreground">{focus}</p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{outcome}</p>
          </div>
        </div>

        {stats.length > 0 && (
          <div className={cn("mt-5 grid gap-3", stats.length >= 3 ? "md:grid-cols-3" : "md:grid-cols-2")}>
            {stats.map((stat) => (
              <div key={stat.label} className="rounded-xl border border-border bg-background/70 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {stat.label}
                </p>
                <p className="mt-1 text-2xl font-bold text-foreground">{stat.value}</p>
                {stat.detail && <p className="mt-1 text-xs text-muted-foreground">{stat.detail}</p>}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
