import { getAuth } from "../shared/auth";
import { GUIDES } from "../shared/guides";
import { ZimaOverlay } from "./overlay/overlay";

const TRIGGER_KEY = "zima_outlook_guide_triggered";

async function init(): Promise<void> {
  const auth = await getAuth();
  if (!auth) return;

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "SHOW_GUIDE" && msg.provider === "outlook") {
      sessionStorage.setItem(TRIGGER_KEY, "1");
      ZimaOverlay.mount(GUIDES.outlook);
    }
  });
}

init();
