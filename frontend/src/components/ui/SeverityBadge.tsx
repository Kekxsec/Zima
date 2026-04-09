import { cn } from "@/lib/utils"
import type { Severity } from "@/types/api"

const SEVERITY_CONFIG: Record<Severity, { label: string; dot: string; text: string; bg: string }> = {
  critical: { label: "Critical", dot: "bg-red-500",    text: "text-red-700    dark:text-red-300",    bg: "bg-red-50    dark:bg-red-500/20" },
  high:     { label: "High",     dot: "bg-orange-500", text: "text-orange-700 dark:text-orange-300", bg: "bg-orange-50 dark:bg-orange-500/20" },
  medium:   { label: "Medium",   dot: "bg-amber-400",  text: "text-amber-700  dark:text-amber-300",  bg: "bg-amber-50  dark:bg-amber-500/20" },
  low:      { label: "Low",      dot: "bg-sky-500",    text: "text-sky-700    dark:text-sky-300",    bg: "bg-sky-50    dark:bg-sky-500/20" },
  info:     { label: "Info",     dot: "bg-slate-400",  text: "text-slate-600  dark:text-slate-300",  bg: "bg-slate-100 dark:bg-slate-500/20" },
}

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity
  className?: string
}) {
  const cfg = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.info
  return (
    <span
      className={cn(
        `severity-badge severity-badge-${severity}`,
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold shrink-0",
        cfg.bg,
        cfg.text,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", cfg.dot)} />
      {cfg.label}
    </span>
  )
}
