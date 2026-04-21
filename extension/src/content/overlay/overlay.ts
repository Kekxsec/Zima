import { postGuideEvent } from "../../shared/api";
import { getAuth } from "../../shared/auth";
import type { Guide, GuideStep } from "../../shared/types";
import overlayStyles from "./overlay.css?inline";

const ALLOWED_NAVIGATION_ORIGINS = new Set([
  "https://mail.google.com",
  "https://outlook.live.com",
  "https://outlook.office.com",
  "https://mail.yahoo.com",
  "https://account.proton.me",
  "https://mail.proton.me",
  "https://app.fastmail.com",
]);

function isValidNavigationUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && ALLOWED_NAVIGATION_ORIGINS.has(parsed.origin);
  } catch {
    return false;
  }
}

export class ZimaOverlay {
  private host: HTMLElement;
  private shadow: ShadowRoot;
  private guide: Guide;
  private currentStepIndex = 0;
  private dismissed = false;
  private stepAdvancing = false;

  constructor(guide: Guide) {
    this.guide = guide;
    this.host = document.createElement("div");
    this.host.id = "zima-overlay-root";
    this.shadow = this.host.attachShadow({ mode: "closed" });
    document.body.appendChild(this.host);
    this.render();
  }

  private get currentStep(): GuideStep {
    return this.guide.steps[this.currentStepIndex]!;
  }

  private get totalSteps(): number {
    return this.guide.steps.length;
  }

  private async reportStep(stepId: string): Promise<void> {
    const auth = await getAuth();
    if (!auth) return;
    try {
      await postGuideEvent(this.guide.provider, stepId);
    } catch {
      // Non-fatal — guide continues even if reporting fails
    }
  }

  private render(): void {
    const step = this.currentStep;
    const stepNumber = this.currentStepIndex + 1;
    const progressPct = Math.round((stepNumber / this.totalSteps) * 100);
    const isFinal = step.id === "mbox_downloaded";

    this.shadow.innerHTML = `
      <style>${overlayStyles}</style>
      <div class="zima-panel">
        <div class="zima-header">
          <span class="zima-logo">ZIMA</span>
          <span class="zima-header-title">${this.guide.title}</span>
          <button class="zima-close" id="zima-close" aria-label="Dismiss">✕</button>
        </div>
        <div class="zima-progress">
          <div class="zima-progress-bar" style="width:${progressPct}%"></div>
        </div>
        <div class="zima-body">
          <div class="zima-step-count">Step ${stepNumber} of ${this.totalSteps}</div>
          <div class="zima-step-title">${step.title}</div>
          <div class="zima-step-instruction">${step.instruction}</div>
        </div>
        ${
          step.navigateTo
            ? `<button class="zima-navigate" id="zima-navigate">
                ↗ Open the page for this step
               </button>`
            : ""
        }
        <div class="zima-actions">
          ${
            this.currentStepIndex > 0
              ? `<button class="zima-btn zima-btn-secondary" id="zima-back">← Back</button>`
              : ""
          }
          ${
            isFinal
              ? `<button class="zima-btn zima-btn-success" id="zima-done">I have the file ✓</button>`
              : `<button class="zima-btn zima-btn-primary" id="zima-next">Next →</button>`
          }
        </div>
      </div>
    `;

    this.shadow
      .getElementById("zima-close")
      ?.addEventListener("click", () => this.dismiss());

    this.shadow
      .getElementById("zima-next")
      ?.addEventListener("click", () => this.advance());

    this.shadow
      .getElementById("zima-back")
      ?.addEventListener("click", () => this.back());

    this.shadow
      .getElementById("zima-done")
      ?.addEventListener("click", () => this.complete());

    this.shadow
      .getElementById("zima-navigate")
      ?.addEventListener("click", () => {
        if (step.navigateTo && isValidNavigationUrl(step.navigateTo)) {
          window.location.href = step.navigateTo;
        }
      });
  }

  private async advance(): Promise<void> {
    if (this.stepAdvancing) return;
    this.stepAdvancing = true;
    try {
      await this.reportStep(this.currentStep.id);
      if (this.currentStepIndex < this.totalSteps - 1) {
        this.currentStepIndex++;
        this.render();
      }
    } finally {
      this.stepAdvancing = false;
    }
  }

  private back(): void {
    if (this.currentStepIndex > 0) {
      this.currentStepIndex--;
      this.render();
    }
  }

  private async complete(): Promise<void> {
    await this.reportStep("mbox_downloaded");
    this.dismiss();
    // Notify the service worker so it can trigger the upload prompt on the Zima tab
    chrome.runtime.sendMessage({ type: "GUIDE_COMPLETE", provider: this.guide.provider });
  }

  private dismiss(): void {
    if (this.dismissed) return;
    this.dismissed = true;
    this.host.remove();
  }

  /** Show the overlay. Call once after constructing. */
  static mount(guide: Guide): ZimaOverlay {
    // Remove any existing overlay for this session
    document.getElementById("zima-overlay-root")?.remove();
    return new ZimaOverlay(guide);
  }
}
