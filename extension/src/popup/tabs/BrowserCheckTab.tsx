import type { PrivacySnapshot, BrowserCheckScore } from "../../shared/types";
import type { PrivacySettingMeta } from "../constants/privacyMap";
import { PRIVACY_SETTINGS_MAP } from "../constants/privacyMap";
import { CheckItem } from "../components/CheckItem";
import { ScoreBadge } from "../components/ScoreBadge";
import { useLocalStorage } from "../hooks/useStorage";

function computeScore(snapshot: PrivacySnapshot): BrowserCheckScore {
  let highMismatch = false;
  let medMismatch = false;
  for (const meta of PRIVACY_SETTINGS_MAP) {
    const raw = snapshot[meta.key];
    if (!raw || raw.error) continue;
    if (raw.value !== meta.recommended_value) {
      if (meta.relevance === "high") highMismatch = true;
      if (meta.relevance === "medium") medMismatch = true;
    }
  }
  if (highMismatch) return "vulnerable";
  if (medMismatch) return "fair";
  return "good";
}

function countResolved(snapshot: PrivacySnapshot): number {
  return PRIVACY_SETTINGS_MAP.filter((m) => {
    const raw = snapshot[m.key];
    return raw && !raw.error && raw.value === m.recommended_value;
  }).length;
}

const RELEVANCE_GROUPS: {
  rel: PrivacySettingMeta["relevance"];
  label: string;
  dotColor: string;
}[] = [
  { rel: "high", label: "High Priority", dotColor: "bg-danger" },
  { rel: "medium", label: "Medium Priority", dotColor: "bg-warning" },
  { rel: "low", label: "Low Priority", dotColor: "bg-muted" },
];

export function BrowserCheckTab() {
  const [snapshot, loaded] = useLocalStorage<PrivacySnapshot>("zima_privacy_snapshot", {});

  if (!loaded) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    );
  }

  const hasSnapshot = Object.keys(snapshot).length > 0;

  if (!hasSnapshot) {
    return (
      <div className="flex flex-col items-center px-6 py-10 text-center gap-3">
        <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center">
          <svg className="w-7 h-7 text-primary" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
          </svg>
        </div>
        <p className="text-sm font-bold text-foreground">No snapshot yet</p>
        <p className="text-xs text-muted leading-relaxed max-w-[260px]">
          Connect the extension and wait a moment. The first snapshot runs automatically after connection.
        </p>
      </div>
    );
  }

  const score = computeScore(snapshot);
  const resolved = countResolved(snapshot);
  const total = PRIVACY_SETTINGS_MAP.length;

  return (
    <div className="flex flex-col">
      {/* Score hero */}
      <div className="border-b border-border bg-surface">
        <ScoreBadge score={score} resolved={resolved} total={total} />
      </div>

      {/* Checklists */}
      <div className="p-4 space-y-4">
        {RELEVANCE_GROUPS.map(({ rel, label, dotColor }) => {
          const items = PRIVACY_SETTINGS_MAP.filter((m) => m.relevance === rel);
          const groupResolved = items.filter((m) => {
            const raw = snapshot[m.key];
            return raw && !raw.error && raw.value === m.recommended_value;
          }).length;
          return (
            <div key={rel} className="space-y-1.5">
              <div className="flex items-center justify-between px-0.5">
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}`} />
                  <p className="text-[10px] font-bold uppercase tracking-widest text-muted">
                    {label}
                  </p>
                </div>
                <p className="text-[10px] text-muted">
                  {groupResolved}/{items.length}
                </p>
              </div>
              <div className="rounded-xl border border-border overflow-hidden bg-surface">
                {items.map((meta) => (
                  <CheckItem key={meta.key} meta={meta} raw={snapshot[meta.key]} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
