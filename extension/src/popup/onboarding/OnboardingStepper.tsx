import { useState } from "react";

const APP_URL = (import.meta.env.VITE_APP_URL as string | undefined) ?? "https://app.zima.app";

interface Step {
  icon: string;
  title: string;
  body: string;
  cta?: string;
}

const STEPS: Step[] = [
  {
    icon: "shield",
    title: "Welcome to Zima",
    body: "Your privacy audit starts here. Zima guides you through exporting your email data and checks your browser's privacy settings.",
  },
  {
    icon: "pin",
    title: "Pin Zima to your toolbar",
    body: "Click the puzzle piece icon (🧩) in your browser toolbar, find Zima Security, then click the pin icon to keep it one click away.",
  },
  {
    icon: "link",
    title: "Connect your extension",
    body: "Open the Zima app and follow the connection prompt to link your browser. This lets Zima take a privacy snapshot of your settings.",
    cta: "Open Zima to connect",
  },
  {
    icon: "check",
    title: "You're all set",
    body: "Use the Dashboard tab to start a guide for your email provider, and Browser Check to review your privacy settings.",
  },
];

function StepIcon({ icon, active }: { icon: string; active: boolean }) {
  const cls = `w-7 h-7 ${active ? "text-primary" : "text-muted"}`;
  if (icon === "shield") return (
    <svg className={cls} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
    </svg>
  );
  if (icon === "pin") return (
    <svg className={cls} viewBox="0 0 24 24" fill="currentColor">
      <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z" />
    </svg>
  );
  if (icon === "link") return (
    <svg className={cls} viewBox="0 0 24 24" fill="currentColor">
      <path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z" />
    </svg>
  );
  return (
    <svg className={cls} viewBox="0 0 24 24" fill="currentColor">
      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
    </svg>
  );
}

interface Props {
  onComplete: () => void;
}

export function OnboardingStepper({ onComplete }: Props) {
  const [step, setStep] = useState(0);
  const current = STEPS[step]!;
  const isLast = step === STEPS.length - 1;
  const total = STEPS.length;

  function advance() {
    if (isLast) {
      void chrome.storage.local.set({ zima_onboarding_complete: true });
      onComplete();
    } else {
      setStep((s) => s + 1);
    }
  }

  return (
    <div className="flex flex-col min-h-[420px]">
      {/* Header bar */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border shrink-0">
        <svg className="w-4 h-4 text-primary" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
        </svg>
        <span className="text-sm font-black tracking-widest text-primary">ZIMA</span>
      </div>

      <div className="flex flex-col flex-1 px-5 pt-6 pb-5">
        {/* Progress dots */}
        <div className="flex gap-1.5 mb-7 shrink-0">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                i < step ? "bg-primary/60" : i === step ? "bg-primary" : "bg-border"
              }`}
            />
          ))}
        </div>

        {/* Icon */}
        <div className="mb-4 shrink-0">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center">
            <StepIcon icon={current.icon} active={true} />
          </div>
        </div>

        <p className="text-[10px] font-bold uppercase tracking-widest text-muted mb-1.5 shrink-0">
          Step {step + 1} of {total}
        </p>
        <h2 className="text-lg font-bold text-foreground mb-3 shrink-0">
          {current.title}
        </h2>
        <p className="text-sm text-muted leading-relaxed flex-1">
          {current.body}
        </p>

        <div className="mt-6 space-y-2 shrink-0">
          {current.cta !== undefined && (
            <button
              onClick={() => chrome.tabs.create({ url: `${APP_URL}/connect-extension` })}
              className="w-full rounded-xl border border-primary py-2.5 text-sm font-semibold text-primary hover:bg-primary/10 transition-colors cursor-pointer bg-transparent"
            >
              {current.cta} ↗
            </button>
          )}
          <button
            onClick={advance}
            className="w-full rounded-xl bg-primary py-2.5 text-sm font-bold text-backdrop hover:bg-primary-hover transition-colors cursor-pointer border-0"
          >
            {isLast ? "Get started →" : "Continue →"}
          </button>
          {step > 0 && (
            <button
              onClick={() => setStep((s) => s - 1)}
              className="w-full py-2 text-xs text-muted hover:text-muted-light transition-colors cursor-pointer bg-transparent border-0"
            >
              ← Back
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
