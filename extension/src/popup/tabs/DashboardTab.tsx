import type { AuthState, Provider } from "../../shared/types";
import { isConnected } from "../../shared/auth";
import { useLocalStorage } from "../hooks/useStorage";

const APP_URL = (import.meta.env.VITE_APP_URL as string | undefined) ?? "https://app.zima.app";

const PROVIDERS: {
  provider: Provider;
  label: string;
  initial: string;
  color: string;
  url: string;
}[] = [
  { provider: "gmail", label: "Gmail", initial: "G", color: "#EA4335", url: "https://mail.google.com" },
  { provider: "outlook", label: "Outlook", initial: "O", color: "#0078d4", url: "https://outlook.live.com" },
  { provider: "yahoo", label: "Yahoo Mail", initial: "Y", color: "#720e9e", url: "https://mail.yahoo.com" },
  { provider: "proton", label: "Proton Mail", initial: "P", color: "#6d4aff", url: "https://mail.proton.me" },
  { provider: "fastmail", label: "Fastmail", initial: "F", color: "#4f81bd", url: "https://app.fastmail.com" },
];

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
    </svg>
  );
}

interface Props {
  auth: AuthState | null;
}

export function DashboardTab({ auth }: Props) {
  const [completions] = useLocalStorage<Record<string, boolean>>("zima_guide_completions", {});
  const [extCount] = useLocalStorage<number>("zima_extension_count", 0);

  const connected = isConnected(auth);

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <div
        className="px-4 pt-5 pb-4 border-b border-border"
        style={{
          background: connected
            ? "linear-gradient(160deg, #0a1f12 0%, #0a0f1e 60%)"
            : "linear-gradient(160deg, #1a0a0a 0%, #0a0f1e 60%)",
        }}
      >
        <div className="flex items-center gap-4">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0"
            style={{
              background: connected ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.12)",
            }}
          >
            <ShieldIcon
              className={`w-7 h-7 ${connected ? "text-success" : "text-danger"}`}
            />
          </div>
          <div>
            <p className={`text-base font-bold ${connected ? "text-success" : "text-danger"}`}>
              {connected ? "Protected" : "Not Connected"}
            </p>
            <p className="text-xs text-muted mt-0.5">
              {connected ? "Zima is monitoring your privacy" : "Connect to enable monitoring"}
            </p>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {!connected ? (
          <button
            onClick={() => chrome.tabs.create({ url: `${APP_URL}/connect-extension` })}
            className="w-full rounded-xl bg-primary py-3 text-sm font-bold text-backdrop hover:bg-primary-hover transition-colors cursor-pointer border-0"
          >
            Open Zima to connect →
          </button>
        ) : (
          <>
            {/* Guides */}
            <div className="space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted px-0.5">
                Email Export Guides
              </p>
              <div className="rounded-xl border border-border overflow-hidden bg-surface">
                {PROVIDERS.map(({ provider, label, initial, color, url }) => {
                  const done = completions[provider] === true;
                  return (
                    <button
                      key={provider}
                      onClick={() => {
                        chrome.runtime.sendMessage({ type: "TRIGGER_GUIDE", provider, url });
                        window.close();
                      }}
                      className="flex w-full items-center gap-3 border-b border-border px-3 py-2.5 text-left hover:bg-surface-hover transition-colors last:border-0 cursor-pointer bg-transparent"
                    >
                      <div
                        className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white shrink-0"
                        style={{ backgroundColor: color }}
                      >
                        {initial}
                      </div>
                      <span className={`flex-1 text-sm font-medium ${done ? "text-muted" : "text-foreground"}`}>
                        {label}
                      </span>
                      {done ? (
                        <span className="text-xs font-bold text-success">✓</span>
                      ) : (
                        <span className="text-xs text-muted">→</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Browser snapshot card */}
            <button
              onClick={() => chrome.tabs.create({ url: `${APP_URL}/device` })}
              className="flex w-full items-center gap-3 rounded-xl border border-border px-3 py-3 hover:bg-surface-hover transition-colors cursor-pointer bg-surface"
            >
              <div className="w-9 h-9 rounded-xl bg-primary/15 flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-primary" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12zM6 10h12v2H6zm0 4h8v2H6z" />
                </svg>
              </div>
              <div className="flex-1 text-left">
                <p className="text-xs font-bold text-foreground">Browser Snapshot</p>
                <p className="text-xs text-muted mt-0.5">
                  {extCount > 0
                    ? `${extCount} extension${extCount !== 1 ? "s" : ""} installed`
                    : "No snapshot yet"}
                </p>
              </div>
              <span className="text-xs text-primary shrink-0">View ↗</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
}
