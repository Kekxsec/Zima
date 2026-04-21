export interface PrivacySettingMeta {
  key: string;
  label: string;
  category: string;
  relevance: "high" | "medium" | "low";
  rationale: string;
  recommended_value: boolean | string;
}

export const PRIVACY_SETTINGS_MAP: PrivacySettingMeta[] = [
  // ── High priority ────────────────────────────────────────────────────────
  {
    key: "webRTCIPHandlingPolicy",
    label: "WebRTC IP handling",
    category: "Network",
    relevance: "high",
    rationale: "Can leak your real IP address even when using a VPN.",
    recommended_value: "disable_non_proxied_udp",
  },
  {
    key: "safeBrowsingEnabled",
    label: "Safe Browsing",
    category: "Services",
    relevance: "high",
    rationale: "Protects against phishing sites and malware downloads.",
    recommended_value: true,
  },
  {
    key: "thirdPartyCookiesAllowed",
    label: "Third-party cookies",
    category: "Websites",
    relevance: "high",
    rationale: "Third-party cookies are the primary mechanism for cross-site tracking.",
    recommended_value: false,
  },

  // ── Medium priority ───────────────────────────────────────────────────────
  {
    key: "networkPredictionEnabled",
    label: "Network prediction",
    category: "Network",
    relevance: "medium",
    rationale: "Pre-fetches DNS and TCP connections for pages you have not yet visited.",
    recommended_value: false,
  },
  {
    key: "autofillCreditCardEnabled",
    label: "Autofill credit cards",
    category: "Services",
    relevance: "medium",
    rationale: "Storing card numbers in the browser expands the attack surface if compromised.",
    recommended_value: false,
  },
  {
    key: "passwordSavingEnabled",
    label: "Password saving",
    category: "Services",
    relevance: "medium",
    rationale: "Use a dedicated password manager — browser password stores are higher-value targets.",
    recommended_value: false,
  },
  {
    key: "safeBrowsingExtendedReportingEnabled",
    label: "Safe Browsing extended reporting",
    category: "Services",
    relevance: "medium",
    rationale: "Sends additional browsing data to Google for threat analysis.",
    recommended_value: false,
  },
  {
    key: "hyperlinkAuditingEnabled",
    label: "Hyperlink auditing",
    category: "Websites",
    relevance: "medium",
    rationale: "Allows websites to track which links you click via ping requests.",
    recommended_value: false,
  },
  {
    key: "referrersEnabled",
    label: "Referrer headers",
    category: "Websites",
    relevance: "medium",
    rationale: "Exposes the page you came from to destination sites on every navigation.",
    recommended_value: false,
  },
  {
    key: "adMeasurementEnabled",
    label: "Ad measurement",
    category: "Websites",
    relevance: "medium",
    rationale: "Privacy-preserving ad API still shares conversion data with advertisers.",
    recommended_value: false,
  },
  {
    key: "topicsEnabled",
    label: "Topics API",
    category: "Websites",
    relevance: "medium",
    rationale: "Lets sites infer your browsing interests for targeted advertising.",
    recommended_value: false,
  },
  {
    key: "fledgeEnabled",
    label: "Protected Audience API",
    category: "Websites",
    relevance: "medium",
    rationale: "On-device interest-based ad targeting shared with sites you visit.",
    recommended_value: false,
  },

  // ── Low priority ─────────────────────────────────────────────────────────
  {
    key: "alternateErrorPagesEnabled",
    label: "Alternate error pages",
    category: "Services",
    relevance: "low",
    rationale: "Sends failed URLs to a Google web service to generate error pages.",
    recommended_value: false,
  },
  {
    key: "autofillAddressEnabled",
    label: "Autofill addresses",
    category: "Services",
    relevance: "low",
    rationale: "Convenience feature; low privacy impact but stores personal data in the browser.",
    recommended_value: false,
  },
  {
    key: "searchSuggestEnabled",
    label: "Search suggestions",
    category: "Services",
    relevance: "low",
    rationale: "Partial search queries are sent to Google before you finish typing.",
    recommended_value: false,
  },
  {
    key: "spellingServiceEnabled",
    label: "Spell check service",
    category: "Services",
    relevance: "low",
    rationale: "Text you type in forms can be sent to Google's cloud spell checker.",
    recommended_value: false,
  },
  {
    key: "translationServiceEnabled",
    label: "Translation service",
    category: "Services",
    relevance: "low",
    rationale: "Prompts to send page content to Google Translate.",
    recommended_value: false,
  },
  {
    key: "doNotTrackEnabled",
    label: "Do Not Track",
    category: "Websites",
    relevance: "low",
    rationale: "DNT header is widely ignored — enable it anyway as a signal.",
    recommended_value: true,
  },
  {
    key: "relatedWebsiteSetsEnabled",
    label: "Related Website Sets",
    category: "Websites",
    relevance: "low",
    rationale: "Allows cookie sharing across a declared group of related domains.",
    recommended_value: false,
  },
];
