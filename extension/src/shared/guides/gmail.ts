import type { Guide } from "../types";

export const gmailGuide: Guide = {
  provider: "gmail",
  title: "Export your Gmail as an mbox file",
  steps: [
    {
      id: "step_1",
      title: "Open Google Takeout",
      instruction:
        "We'll open Google Takeout — Google's official export tool. Click Next to continue.",
      navigateTo: "https://takeout.google.com",
    },
    {
      id: "step_2",
      title: "Deselect all products",
      instruction:
        'Click "Deselect all" at the top of the product list. This ensures only your mail is included in the export.',
    },
    {
      id: "step_3",
      title: "Select Mail only",
      instruction:
        'Scroll down and find "Mail". Toggle it on. Leave the format as "mbox".',
    },
    {
      id: "step_4",
      title: "Proceed to delivery options",
      instruction: 'Click "Next step" at the bottom of the page.',
    },
    {
      id: "step_5",
      title: "Configure the export",
      instruction:
        'Set delivery method to "Send download link via email". Set frequency to "Export once". Leave file type as ".zip" and size at 2 GB.',
    },
    {
      id: "step_6",
      title: "Create the export",
      instruction:
        'Click "Create export". Google will email you a download link — this can take anywhere from a few minutes to a few hours depending on your mailbox size.',
    },
    {
      id: "step_7",
      title: "Download and extract",
      instruction:
        "When you receive the email from Google, click the download link. Extract the .zip file — inside you'll find a file ending in .mbox. That's the file to upload to Zima.",
    },
    {
      id: "mbox_downloaded",
      title: "Done — upload to Zima",
      instruction:
        "Once you have the .mbox file, click \"I have the file\" below. Zima will then prompt you to upload it.",
    },
  ],
};
