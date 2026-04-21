import { useState } from "react";
import type { PrivacySettingMeta } from "../constants/privacyMap";
import type { RawPrivacySetting } from "../../shared/types";

interface Props {
  meta: PrivacySettingMeta;
  raw?: RawPrivacySetting | undefined;
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "Enabled" : "Disabled";
  return String(v);
}

export function CheckItem({ meta, raw }: Props) {
  const [open, setOpen] = useState(false);
  const unavailable = raw !== undefined && !!raw.error;
  const resolved =
    raw !== undefined && !unavailable && raw.value === meta.recommended_value;

  const statusColor = unavailable
    ? "text-muted"
    : resolved
      ? "text-success"
      : "text-danger";
  const statusSymbol = unavailable ? "·" : resolved ? "✓" : "✕";

  return (
    <div className="border-b border-border last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-surface-hover transition-colors cursor-pointer bg-transparent border-0"
      >
        <span className={`text-sm font-bold shrink-0 w-3 ${statusColor}`}>
          {statusSymbol}
        </span>
        <span className="flex-1 text-sm text-foreground">{meta.label}</span>
        <span className="text-xs text-muted shrink-0">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-1.5">
          <p className="text-xs text-muted leading-relaxed">{meta.rationale}</p>
          {!unavailable && raw !== undefined && (
            <div className="flex gap-4 text-xs">
              <span>
                <span className="text-muted">Current: </span>
                <span className={resolved ? "text-success" : "text-danger"}>
                  {formatValue(raw.value)}
                </span>
              </span>
              <span>
                <span className="text-muted">Target: </span>
                <span className="text-foreground">
                  {formatValue(meta.recommended_value)}
                </span>
              </span>
            </div>
          )}
          {unavailable && (
            <p className="text-xs text-warning">{raw?.error}</p>
          )}
          {raw === undefined && (
            <p className="text-xs text-muted italic">Awaiting first snapshot…</p>
          )}
        </div>
      )}
    </div>
  );
}
