import { getAuth } from "../shared/auth";
import { GUIDES } from "../shared/guides";
import { ZimaOverlay } from "./overlay/overlay";

const TRIGGER_KEY = "zima_gmail_guide_triggered";

async function init(): Promise<void> {
  const auth = await getAuth();
  if (!auth) return;

  // Only mount once per page load
  const alreadyTriggered = sessionStorage.getItem(TRIGGER_KEY);
  if (alreadyTriggered) return;

  // Listen for the service worker to request the guide
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "SHOW_GUIDE" && msg.provider === "gmail") {
      sessionStorage.setItem(TRIGGER_KEY, "1");
      ZimaOverlay.mount(GUIDES.gmail);
    }
  });
}

init();
