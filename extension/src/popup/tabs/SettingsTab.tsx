import type { AuthState } from "../../shared/types";
import { clearAuth } from "../../shared/auth";
import { useLocalStorage } from "../hooks/useStorage";

const APP_URL = (import.meta.env.VITE_APP_URL as string | undefined) ?? "https://app.zima.app";

interface ToggleRowProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}

function ToggleRow({ label, description, checked, onChange }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 px-3 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted mt-0.5 leading-relaxed">{description}</p>
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={[
          "relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors cursor-pointer",
          checked ? "bg-primary" : "bg-border",
        ].join(" ")}
      >
        <span
          className={[
            "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transition-transform duration-200",
            checked ? "translate-x-5" : "translate-x-0",
          ].join(" ")}
        />
      </button>
    </div>
  );
}

interface Props {
  auth: AuthState | null;
  onDisconnect: () => void;
}

export function SettingsTab({ auth, onDisconnect }: Props) {
  const [settings] = useLocalStorage<{ notifications: boolean }>("zima_settings", {
    notifications: true,
  });

  function setNotifications(v: boolean) {
    void chrome.storage.local.set({ zima_settings: { notifications: v } });
  }

  function handleDisconnect() {
    void clearAuth().then(onDisconnect);
  }

  const version = chrome.runtime.getManifest().version;

  return (
    <div className="p-4 space-y-4">
      {/* Notifications */}
      <div className="space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted px-0.5">
          Notifications
        </p>
        <div className="rounded-xl border border-border overflow-hidden bg-surface divide-y divide-border">
          <ToggleRow
            label="Browser alerts"
            description="Notify when a privacy setting changes from the recommended value."
            checked={settings.notifications}
            onChange={setNotifications}
          />
        </div>
      </div>

      {/* Account */}
      <div className="space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted px-0.5">
          Account
        </p>
        <div className="rounded-xl border border-border overflow-hidden bg-surface">
          <div className="flex items-center gap-3 px-3 py-3 border-b border-border">
            <div
              className={`w-2 h-2 rounded-full shrink-0 ${auth ? "bg-success" : "bg-muted"}`}
            />
            <p className="text-sm text-foreground flex-1">
              {auth ? "Extension connected" : "Not connected"}
            </p>
          </div>
          {auth ? (
            <button
              onClick={handleDisconnect}
              className="flex w-full items-center justify-between px-3 py-3 hover:bg-danger/10 transition-colors cursor-pointer bg-transparent border-0 text-left"
            >
              <span className="text-sm text-danger">Disconnect extension</span>
              <span className="text-xs text-danger opacity-60">×</span>
            </button>
          ) : (
            <button
              onClick={() => chrome.tabs.create({ url: `${APP_URL}/connect-extension` })}
              className="flex w-full items-center justify-between px-3 py-3 hover:bg-surface-hover transition-colors cursor-pointer bg-transparent border-0 text-left"
            >
              <span className="text-sm text-primary">Connect to Zima</span>
              <span className="text-xs text-primary">→</span>
            </button>
          )}
        </div>
      </div>

      {/* Links */}
      <div className="space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted px-0.5">
          More
        </p>
        <div className="rounded-xl border border-border overflow-hidden bg-surface divide-y divide-border">
          <button
            onClick={() => chrome.tabs.create({ url: `${APP_URL}/dashboard` })}
            className="flex w-full items-center justify-between px-3 py-3 hover:bg-surface-hover transition-colors cursor-pointer bg-transparent border-0 text-left"
          >
            <span className="text-sm text-foreground">Open Zima dashboard</span>
            <span className="text-xs text-muted">↗</span>
          </button>
          <div className="flex items-center justify-between px-3 py-3">
            <span className="text-sm text-muted">Version</span>
            <span className="text-xs text-muted">{version}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
