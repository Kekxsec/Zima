"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/client"
import type { DiscoveredAccountListResponse } from "@/types/api"
import { WorkspaceHeader } from "./WorkspaceHeader"
import { AccountListPane } from "./AccountListPane"
import { AccountDetailPane } from "./AccountDetailPane"
import { EmptyDetailPlaceholder } from "./EmptyDetailPlaceholder"
import { ImportDrawer } from "./ImportDrawer"

export function AccountsWorkspace() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [sourceFilter, setSourceFilter] = useState("all")
  const [reviewedFilter, setReviewedFilter] = useState("all")
  const [priorityFilter, setPriorityFilter] = useState("all")
  const [showDismissed, setShowDismissed] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  // source + reviewed are server-side; priority + search are client-side
  const queryParams = useMemo(() => {
    const p = new URLSearchParams({ limit: "500" })
    if (sourceFilter !== "all") p.set("source_type", sourceFilter)
    if (reviewedFilter !== "all") p.set("is_reviewed", reviewedFilter)
    return p.toString()
  }, [sourceFilter, reviewedFilter])

  const { data, isLoading } = useQuery({
    queryKey: ["discovered-accounts", sourceFilter, reviewedFilter],
    queryFn: () =>
      api.get<DiscoveredAccountListResponse>(`/email-accounts/accounts?${queryParams}`),
  })

  const allAccounts = useMemo(() => data?.accounts ?? [], [data])
  const total = data?.total ?? 0

  // Client-side priority + search filter
  const filteredAccounts = useMemo(() => {
    let list = allAccounts
    if (priorityFilter !== "all") {
      const tier = parseInt(priorityFilter, 10)
      list = list.filter((a) => a.priority_tier === tier)
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(
        (a) =>
          a.display_name.toLowerCase().includes(q) ||
          a.email_used.toLowerCase().includes(q) ||
          a.service_name.toLowerCase().includes(q),
      )
    }
    return list
  }, [allAccounts, search, priorityFilter])

  const hasFilter =
    search.trim() !== "" ||
    sourceFilter !== "all" ||
    reviewedFilter !== "all" ||
    priorityFilter !== "all" ||
    showDismissed

  const selectedAccount = selectedId
    ? (filteredAccounts.find((a) => a.id === selectedId) ?? null)
    : null

  function handleClearFilter() {
    setSearch("")
    setSourceFilter("all")
    setReviewedFilter("all")
    setPriorityFilter("all")
    setShowDismissed(false)
  }

  return (
    <div className="grid h-full grid-cols-[320px_1fr] divide-x divide-border overflow-hidden">
      {/* ─── Left pane ─── */}
      <div className="flex flex-col overflow-hidden">
        <WorkspaceHeader
          search={search}
          onSearch={setSearch}
          sourceFilter={sourceFilter}
          onSourceFilter={setSourceFilter}
          reviewedFilter={reviewedFilter}
          onReviewedFilter={setReviewedFilter}
          priorityFilter={priorityFilter}
          onPriorityFilter={setPriorityFilter}
          showDismissed={showDismissed}
          onToggleDismissed={() => setShowDismissed((v) => !v)}
          onImport={() => setImportOpen(true)}
          total={total}
        />
        <AccountListPane
          accounts={filteredAccounts}
          isLoading={isLoading}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onImport={() => setImportOpen(true)}
          hasFilter={hasFilter}
          onClearFilter={handleClearFilter}
          showDismissed={showDismissed}
        />
      </div>

      {/* ─── Right pane ─── */}
      <div className="overflow-hidden">
        {selectedAccount ? (
          <AccountDetailPane account={selectedAccount} />
        ) : (
          <EmptyDetailPlaceholder
            hasAccounts={allAccounts.length > 0}
            onImport={() => setImportOpen(true)}
          />
        )}
      </div>

      <ImportDrawer
        open={importOpen}
        onClose={() => setImportOpen(false)}
        totalAccounts={total}
      />
    </div>
  )
}
