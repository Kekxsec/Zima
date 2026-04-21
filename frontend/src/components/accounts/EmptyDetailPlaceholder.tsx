import { MousePointer2, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"

export function EmptyDetailPlaceholder({
  hasAccounts,
  onImport,
}: {
  hasAccounts: boolean
  onImport: () => void
}) {
  if (!hasAccounts) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
          <Upload className="h-6 w-6 text-muted-foreground" />
        </div>
        <div>
          <p className="text-sm font-semibold">Start discovering accounts</p>
          <p className="mt-1 max-w-xs text-xs leading-relaxed text-muted-foreground">
            Import an inbox export (.mbox) or password manager export to find all the
            services tied to your identity.
          </p>
        </div>
        <Button size="sm" className="gap-1.5" onClick={onImport}>
          <Upload className="h-3.5 w-3.5" />
          Import sources
        </Button>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted">
        <MousePointer2 className="h-5 w-5 text-muted-foreground" />
      </div>
      <div>
        <p className="text-sm font-semibold">Select an account</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Choose an account from the list to review its details and take action.
        </p>
      </div>
    </div>
  )
}
