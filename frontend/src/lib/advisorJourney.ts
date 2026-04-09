export type AdvisorJourneyStageState = "done" | "current" | "upcoming"

export type AdvisorJourneyStage = {
  key: "scan" | "accounts" | "export" | "priorities" | "browser" | "progress"
  title: string
  description: string
  state: AdvisorJourneyStageState
}

type AdvisorJourneyInput = {
  hasCompletedScan: boolean
  hasUploadedInbox: boolean
  uploadProcessing: boolean
  discoveredAccounts: number
  exportCompleted: boolean
  openFindings: number
  hasBrowserSetup: boolean
}

function getCurrentStep({
  hasCompletedScan,
  hasUploadedInbox,
  uploadProcessing,
  discoveredAccounts,
  exportCompleted,
  openFindings,
  hasBrowserSetup,
}: AdvisorJourneyInput): AdvisorJourneyStage["key"] {
  if (!hasCompletedScan) return "scan"
  if (!hasUploadedInbox) return "accounts"
  if (uploadProcessing) return "accounts"
  if (discoveredAccounts === 0) return "accounts"
  if (!exportCompleted) return "export"
  if (openFindings > 0) return "priorities"
  if (!hasBrowserSetup) return "browser"
  return "progress"
}

export function buildAdvisorJourney(input: AdvisorJourneyInput): AdvisorJourneyStage[] {
  const currentStep = getCurrentStep(input)

  const stages: Omit<AdvisorJourneyStage, "state">[] = [
    {
      key: "scan",
      title: "First scan",
      description: "We look for breaches, exposed accounts, and other early warning signs.",
    },
    {
      key: "accounts",
      title: "Find your accounts",
      description: "Upload your inbox export so we can spot services tied to your email addresses.",
    },
    {
      key: "export",
      title: "Move them into your password manager",
      description: "Export the account list, then verify links before you trust them.",
    },
    {
      key: "priorities",
      title: "Fix the urgent issues",
      description: "Work through the breached services and risky accounts in a safe order.",
    },
    {
      key: "browser",
      title: "Secure your browser",
      description: "Review your browser, extensions, and settings after your accounts are in better shape.",
    },
    {
      key: "progress",
      title: "Check your progress",
      description: "Use the score page later to see whether your cleanup is helping.",
    },
  ]

  const currentIndex = stages.findIndex((stage) => stage.key === currentStep)

  return stages.map((stage, index) => ({
    ...stage,
    state: index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming",
  }))
}

export function getAdvisorNextAction(input: AdvisorJourneyInput) {
  const currentStep = getCurrentStep(input)

  switch (currentStep) {
    case "scan":
      return {
        title: "Run your first scan",
        description: "Start the scan so Zima can build your first security picture.",
        href: "/onboarding/scan",
        label: "Go to scan",
      }
    case "accounts":
      if (!input.hasUploadedInbox) {
        return {
          title: "Upload your inbox export",
          description: "This helps Zima find old accounts and services your scan cannot see by itself.",
          href: "/accounts",
          label: "Upload inbox export",
        }
      }
      if (input.uploadProcessing) {
        return {
          title: "Wait for account discovery to finish",
          description: "Your inbox upload is still being analysed. The account list will appear below once it is ready.",
          href: "/accounts",
          label: "Open account discovery",
        }
      }
      return {
        title: "Review the discovered accounts",
        description: "Check which services still matter before you export them.",
        href: "/accounts",
        label: "Review accounts",
      }
    case "export":
      return {
        title: "Export to your password manager",
        description: "Import the accounts there first so password changes are organised and safe.",
        href: "/accounts",
        label: "Export accounts",
      }
    case "priorities":
      return {
        title: "Work through the urgent issues",
        description: "Start with the breached services and high-risk accounts.",
        href: "/findings",
        label: "Open priorities",
      }
    case "progress":
      return {
        title: "Check your progress",
        description: "The score page is a simple health check after the main cleanup work.",
        href: "/scores",
        label: "Open progress",
      }
    case "browser":
      return {
        title: "Secure your browser",
        description: "Review the browser you use, check extensions, and tighten the most important settings.",
        href: "/browser",
        label: "Open browser review",
      }
  }
}
