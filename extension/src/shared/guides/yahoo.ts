import type { Guide } from "../types";

export const yahooGuide: Guide = {
  provider: "yahoo",
  title: "Export your Yahoo Mail",
  steps: [
    {
      id: "step_1",
      title: "Open Yahoo Privacy Dashboard",
      instruction:
        "Go to your Yahoo Privacy Dashboard to request a data export.",
      navigateTo: "https://yahoo.mydashboard.oath.com/",
    },
    {
      id: "step_2",
      title: "Request a data export",
      instruction:
        'Find "Download my data" and click "Request data". Select "Mail" from the list of data types.',
    },
    {
      id: "step_3",
      title: "Wait for the email",
      instruction:
        "Yahoo will send you an email when your export is ready. This typically takes a few hours.",
    },
    {
      id: "step_4",
      title: "Download and extract",
      instruction:
        "Follow the download link in the Yahoo email. Extract the archive — your mail will be in a folder that can be imported into a mail client.",
    },
    {
      id: "step_5",
      title: "Export as mbox via Thunderbird",
      instruction:
        "Import the downloaded mail into Thunderbird, then use File → Export → mbox to produce an .mbox file.",
    },
    {
      id: "mbox_downloaded",
      title: "Done — upload to Zima",
      instruction:
        'Once you have the .mbox file, click "I have the file" below.',
    },
  ],
};
