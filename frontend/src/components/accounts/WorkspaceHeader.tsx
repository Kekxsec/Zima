"use client"

import { Search, Upload } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function WorkspaceHeader({
  search,
  onSearch,
  sourceFilter,
  onSourceFilter,
  reviewedFilter,
  onReviewedFilter,
  priorityFilter,
  onPriorityFilter,
  showDismissed,
  onToggleDismissed,
  onImport,
  total,
}: {
  search: string
  onSearch: (v: string) => void
  sourceFilter: string
  onSourceFilter: (v: string) => void
  reviewedFilter: string
  onReviewedFilter: (v: string) => void
  priorityFilter: string
  onPriorityFilter: (v: string) => void
  showDismissed: boolean
  onToggleDismissed: () => void
  onImport: () => void
  total: number
}) {
  return (
    <div className="shrink-0 space-y-2 border-b border-border p-3">
      {/* Title row */}
      <div className="flex items-center justify-between gap-2 px-1 pb-0.5">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Accounts</h2>
          {total > 0 && (
            <p className="text-[11px] text-muted-foreground">{total} discovered</p>
          )}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1.5 text-xs"
          onClick={onImport}
        >
          <Upload className="h-3 w-3" />
          Import
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search accounts…"
          className="h-8 pl-8 text-xs"
        />
      </div>

      {/* Filters row 1 */}
      <div className="flex gap-1.5">
        <Select value={reviewedFilter} onValueChange={onReviewedFilter}>
          <SelectTrigger className="h-7 flex-1 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="false">Unreviewed</SelectItem>
            <SelectItem value="true">Reviewed</SelectItem>
          </SelectContent>
        </Select>

        <Select value={priorityFilter} onValueChange={onPriorityFilter}>
          <SelectTrigger className="h-7 flex-1 text-xs">
            <SelectValue placeholder="Priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priorities</SelectItem>
            <SelectItem value="1">P1 Critical</SelectItem>
            <SelectItem value="2">P2 High</SelectItem>
            <SelectItem value="3">P3 Medium</SelectItem>
            <SelectItem value="4">P4 Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Dismissed toggle */}
      <button
        type="button"
        onClick={onToggleDismissed}
        className={
          showDismissed
            ? "flex h-7 w-full items-center justify-center rounded-md border border-violet-400/40 bg-violet-400/10 text-[11px] font-medium text-violet-300"
            : "flex h-7 w-full items-center justify-center rounded-md border border-border/50 text-[11px] text-muted-foreground hover:text-foreground"
        }
      >
        {showDismissed ? "Hiding dismissed" : "Show dismissed"}
      </button>

      {/* Filters row 2 — source */}
      <Select value={sourceFilter} onValueChange={onSourceFilter}>
        <SelectTrigger className="h-7 w-full text-xs">
          <SelectValue placeholder="All sources" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All sources</SelectItem>
          <SelectGroup>
            <SelectLabel className="text-[10px]">Email import</SelectLabel>
            <SelectItem value="account_confirmation">Account registrations</SelectItem>
            <SelectItem value="receipt">Receipts</SelectItem>
            <SelectItem value="security_alert">Security alerts</SelectItem>
            <SelectItem value="password_reset">Password resets</SelectItem>
            <SelectItem value="newsletter">Newsletters</SelectItem>
            <SelectItem value="other">Other emails</SelectItem>
          </SelectGroup>
          <SelectGroup>
            <SelectLabel className="text-[10px]">Scan tools</SelectLabel>
            <SelectItem value="epieos">Epieos</SelectItem>
            <SelectItem value="holehe">Holehe</SelectItem>
            <SelectItem value="maigret">Maigret</SelectItem>
          </SelectGroup>
          <SelectGroup>
            <SelectLabel className="text-[10px]">Vault</SelectLabel>
            <SelectItem value="password_manager">Password manager</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  )
}
