import type { Guide } from "../types";

export const protonGuide: Guide = {
  provider: "proton",
  title: "Export your Proton Mail",
  steps: [
    {
      id: "step_1",
      title: "Open Proton Mail export settings",
      instruction:
        "Go to your Proton Account settings to access the export tool.",
      navigateTo: "https://account.proton.me/mail/import-export",
    },
    {
      id: "step_2",
      title: "Download Proton Mail Export Tool",
      instruction:
        "Proton provides an official Export Tool app. Download and install it from the Import/Export page.",
    },
    {
      id: "step_3",
      title: "Sign in to the Export Tool",
      instruction:
        "Open the Proton Mail Export Tool and sign in with your Proton credentials.",
    },
    {
      id: "step_4",
      title: "Export your mailbox",
      instruction:
        'In the Export Tool, select "Export" and choose the mailboxes you want. The tool will save them as .mbox files.',
    },
    {
      id: "step_5",
      title: "Locate the exported file",
      instruction:
        "Find the exported .mbox file in the folder you chose during export (defaults to your Documents folder).",
    },
    {
      id: "mbox_downloaded",
      title: "Done — upload to Zima",
      instruction:
        'Once you have the .mbox file, click "I have the file" below.',
    },
  ],
};
