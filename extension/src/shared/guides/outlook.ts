import type { Guide } from "../types";

export const outlookGuide: Guide = {
  provider: "outlook",
  title: "Export your Outlook mail",
  steps: [
    {
      id: "step_1",
      title: "Open Privacy and data settings",
      instruction:
        'Go to Outlook Settings → General → Privacy and data. Or click Next and we\'ll take you there.',
      navigateTo:
        "https://outlook.live.com/mail/0/options/general/privacy",
    },
    {
      id: "step_2",
      title: "Request a mailbox export",
      instruction:
        'Click "Export mailbox". Outlook will prepare a .pst file containing your mail. This may take several minutes.',
    },
    {
      id: "step_3",
      title: "Download the export",
      instruction:
        "When the export is ready, a download button will appear on the same page. Download the .pst file.",
    },
    {
      id: "step_4",
      title: "Convert to mbox",
      instruction:
        "Outlook exports as .pst format. To convert to .mbox: open Thunderbird, import the .pst file via File → Import, then export the mailbox as mbox using ImportExportTools NG.",
    },
    {
      id: "mbox_downloaded",
      title: "Done — upload to Zima",
      instruction:
        'Once you have the .mbox file, click "I have the file" below.',
    },
  ],
};
