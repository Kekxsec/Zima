import { fastmailGuide } from "./fastmail";
import { gmailGuide } from "./gmail";
import { outlookGuide } from "./outlook";
import { protonGuide } from "./proton";
import { yahooGuide } from "./yahoo";
import type { Guide, Provider } from "../types";

export const GUIDES: Record<Provider, Guide> = {
  gmail: gmailGuide,
  outlook: outlookGuide,
  yahoo: yahooGuide,
  proton: protonGuide,
  fastmail: fastmailGuide,
  apple: {
    provider: "apple",
    title: "Export Apple Mail as mbox",
    steps: [
      {
        id: "step_1",
        title: "Open Apple Mail",
        instruction:
          "Apple Mail stores mailboxes as .mbox files natively. Open the Mail app on your Mac.",
      },
      {
        id: "step_2",
        title: "Select the mailbox to export",
        instruction:
          'In the sidebar, right-click the mailbox (e.g., Inbox) you want to export and choose "Export Mailbox…".',
      },
      {
        id: "step_3",
        title: "Save the file",
        instruction:
          "Choose a save location. Apple Mail will save a .mbox file directly.",
      },
      {
        id: "mbox_downloaded",
        title: "Done — upload to Zima",
        instruction:
          'Once you have the .mbox file, click "I have the file" below.',
      },
    ],
  },
};

export { gmailGuide, outlookGuide, yahooGuide, protonGuide, fastmailGuide };
