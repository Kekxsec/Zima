import type { Guide } from "../types";

export const fastmailGuide: Guide = {
  provider: "fastmail",
  title: "Export your Fastmail as mbox",
  steps: [
    {
      id: "step_1",
      title: "Open Fastmail Privacy settings",
      instruction:
        "Go to Settings → Privacy & Security → Export data.",
      navigateTo: "https://app.fastmail.com/settings/privacy",
    },
    {
      id: "step_2",
      title: "Select mail export",
      instruction:
        'Under "Export data", click "Export mail". Choose "MBOX" as the format.',
    },
    {
      id: "step_3",
      title: "Download the export",
      instruction:
        "Fastmail will generate the file and prompt you to download it immediately.",
    },
    {
      id: "mbox_downloaded",
      title: "Done — upload to Zima",
      instruction:
        'Once you have the .mbox file, click "I have the file" below.',
    },
  ],
};
