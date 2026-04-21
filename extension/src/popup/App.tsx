import { useEffect, useState } from "react";
import type { AuthState } from "../shared/types";
import { getAuth } from "../shared/auth";
import { Header } from "./components/Header";
import { TabBar, type Tab } from "./components/TabBar";
import { DashboardTab } from "./tabs/DashboardTab";
import { BrowserCheckTab } from "./tabs/BrowserCheckTab";
import { SettingsTab } from "./tabs/SettingsTab";
import { OnboardingStepper } from "./onboarding/OnboardingStepper";

export function App() {
  const [auth, setAuth] = useState<AuthState | null | undefined>(undefined);
  const [onboardingDone, setOnboardingDone] = useState<boolean | undefined>(
    undefined,
  );
  const [tab, setTab] = useState<Tab>("dashboard");

  useEffect(() => {
    void getAuth().then(setAuth);

    chrome.storage.local.get("zima_onboarding_complete", (r) => {
      setOnboardingDone(r["zima_onboarding_complete"] === true);
    });

    const onSessionChange = (
      changes: Record<string, chrome.storage.StorageChange>,
    ) => {
      if ("zima_auth" in changes) {
        void getAuth().then(setAuth);
      }
    };
    chrome.storage.session.onChanged.addListener(onSessionChange);
    return () => chrome.storage.session.onChanged.removeListener(onSessionChange);
  }, []);

  if (auth === undefined || onboardingDone === undefined) {
    return (
      <div className="flex items-center justify-center min-h-[420px]">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    );
  }

  if (!onboardingDone) {
    return <OnboardingStepper onComplete={() => setOnboardingDone(true)} />;
  }

  return (
    <div className="flex flex-col min-h-[420px]">
      <Header />
      <TabBar tab={tab} onTab={setTab} />
      <div className="tab-content">
        {tab === "dashboard" && <DashboardTab auth={auth} />}
        {tab === "browser-check" && <BrowserCheckTab />}
        {tab === "settings" && (
          <SettingsTab auth={auth} onDisconnect={() => setAuth(null)} />
        )}
      </div>
    </div>
  );
}
