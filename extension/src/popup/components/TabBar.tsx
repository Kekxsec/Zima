export type Tab = "dashboard" | "browser-check" | "settings";

interface Props {
  tab: Tab;
  onTab: (tab: Tab) => void;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "browser-check", label: "Browser" },
  { id: "settings", label: "Settings" },
];

export function TabBar({ tab, onTab }: Props) {
  return (
    <div className="px-3 py-2.5 border-b border-border shrink-0 bg-backdrop">
      <div className="flex bg-surface rounded-xl p-1 gap-0.5">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => onTab(id)}
            className={[
              "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer border-0",
              tab === id
                ? "bg-surface-raised text-foreground shadow-sm"
                : "text-muted hover:text-muted-light bg-transparent",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
