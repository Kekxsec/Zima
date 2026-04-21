export type Provider =
  | "gmail"
  | "outlook"
  | "yahoo"
  | "proton"
  | "fastmail"
  | "apple";

export type Browser = "chrome" | "brave" | "firefox" | "edge";

export interface GuideStep {
  id: string;
  title: string;
  instruction: string;
  /** URL to navigate to before this step, if any */
  navigateTo?: string;
}

export interface Guide {
  provider: Provider;
  title: string;
  steps: GuideStep[];
}

export interface AuthState {
  extensionToken: string;
  userId: string;
  expiresAt: number; // unix ms
}

export interface BrowserSnapshot {
  browser: Browser;
  version: string;
  extensions: InstalledExtension[];
  privacySettings: Record<string, unknown>;
}

export interface InstalledExtension {
  id: string;
  name: string;
  version: string;
  enabled: boolean;
}

export type BrowserCheckScore = "good" | "fair" | "vulnerable";

export interface RawPrivacySetting {
  value: unknown;
  levelOfControl: string | null;
  error?: string;
}

export type PrivacySnapshot = Record<string, RawPrivacySetting>;

export interface PopupSettings {
  notifications: boolean;
}
