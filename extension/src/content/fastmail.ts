import { getAuth } from "../shared/auth";
import { GUIDES } from "../shared/guides";
import { ZimaOverlay } from "./overlay/overlay";

async function init(): Promise<void> {
  const auth = await getAuth();
  if (!auth) return;

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "SHOW_GUIDE" && msg.provider === "fastmail") {
      ZimaOverlay.mount(GUIDES.fastmail);
    }
  });
}

init();
