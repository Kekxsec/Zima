// Shared primitives
export type Severity = "critical" | "high" | "medium" | "low" | "info"
export type FindingStatus = "open" | "suppressed" | "resolved"
export type ScanStatus = "pending" | "running" | "completed" | "failed"
export type ScanTier = "basic" | "standard" | "deep"

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface OTPRequestPayload {
  email: string
}

export interface OTPVerifyPayload {
  email: string
  code: string
}

export interface MessageResponse {
  message: string
}

// ─── User / Account ──────────────────────────────────────────────────────────

export interface User {
  user_id: string
  created_at: string
  updated_at: string
}

export interface Asset {
  asset_id: string
  user_id: string
  entity_type: string
  value: string
  is_primary?: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface AccountResponse {
  user: User
  assets: Asset[]
}

// ─── Scans ───────────────────────────────────────────────────────────────────

export interface Scan {
  id: string
  status: ScanStatus
  tier: ScanTier
  started_at: string | null
  completed_at: string | null
  signals_created: number
  findings_created: number
  domains_run: string[]
  target_emails: string[]
  error_detail: string | null
  created_at: string
}

export interface ScanListResponse {
  scans: Scan[]
  total: number
  limit: number
  offset: number
}

export interface TriggerScanPayload {
  tier?: ScanTier
}

// ─── Signals ─────────────────────────────────────────────────────────────────

export interface Signal {
  signal_id: string
  signal_type: string
  category: string
  entity_type: string
  entity_value: string
  severity: Severity
  confidence: string
  source: string
  provider: string
  summary: string
  details: string | null
  evidence: Record<string, unknown> | null
  tags: string[] | null
  recommended_action: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface SignalListResponse {
  signals: Signal[]
  total: number
  limit: number
  offset: number
  filter_status: string
}

// ─── Findings ────────────────────────────────────────────────────────────────

export interface Finding {
  finding_id: string
  user_id: string
  finding_type: string
  severity: Severity
  confidence: number
  confidence_label: "high" | "medium" | "low"
  title: string
  explanation: string
  rule_name: string
  status: FindingStatus
  contributing_signal_ids: string[]
  affected_entity_ids: string[]
  recommended_actions: string[]
  supporting_signals: Array<{
    signal_id: string
    signal_type: string
    severity: Severity
    provider: string
    source: string
    summary: string
    details: string | null
    entity_type: string
    entity_value: string
    recommended_action: string | null
    breach_name: string | null
    breach_date: string | null
    data_classes: string[]
  }>
  impacted_breaches: Array<{
    email: string
    breach_name: string
    breach_date: string | null
    provider: string
    signal_type: string
    summary: string
    data_classes: string[]
  }>
  affected_entities: Array<{
    id: string
    entity_type: string
    value: string
    is_primary: boolean
    is_verified: boolean
  }>
  created_at: string
  updated_at: string
}

export interface FindingListResponse {
  findings: Finding[]
  signals_open: number
  total: number
  limit: number
  offset: number
  filter_status: string | null
}

export interface UpdateFindingPayload {
  status: FindingStatus
}

// ─── Scores ──────────────────────────────────────────────────────────────────

export interface DomainScore {
  domain: string
  score: number
  signal_count: number
  scorer_version: string
  calculated_at: string
}

export interface ScoreListResponse {
  scores: DomainScore[]
}

export interface ScoreHistoryEntry {
  score: number
  signal_count: number
  scorer_version: string
  calculated_at: string
}

export interface ScoreHistoryResponse {
  domain: string
  history: ScoreHistoryEntry[]
}

// ─── Audit log ───────────────────────────────────────────────────────────────

export interface AuditEvent {
  event_id: string
  user_id: string
  event_type: string
  detail: Record<string, unknown>
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

export interface AuditLogResponse {
  events: AuditEvent[]
  limit: number
  offset: number
}

// ─── GDPR export ─────────────────────────────────────────────────────────────

export interface GdprExportResponse {
  user: User
  assets: Asset[]
  signals: Signal[]
  findings: Finding[]
  scores: DomainScore[]
}

// ─── Billing ─────────────────────────────────────────────────────────────────

export interface BillingStatusResponse {
  plan: string
  status: string
  current_period_end: string | null
  cancel_at_period_end: boolean
}

export interface CheckoutSessionResponse {
  checkout_url: string
  tier?: string
}

export interface PortalSessionResponse {
  portal_url: string
}

// ─── Email Accounts / mbox ───────────────────────────────────────────────────

export type MboxUploadStatus = "pending" | "processing" | "completed" | "failed"

export interface MboxUpload {
  id: string
  filename: string
  status: MboxUploadStatus
  accounts_discovered: number
  signals_created: number
  error_detail: string | null
  processed_at: string | null
  created_at: string
}

export interface MboxUploadListResponse {
  uploads: MboxUpload[]
  limit: number
  offset: number
}

export interface MboxUploadResponse {
  upload_id: string
  status: MboxUploadStatus
  message?: string
}

export interface DiscoveredAccount {
  id: string
  service_name: string
  display_name: string
  email_used: string
  source_type: string
  sender_domain: string | null
  login_url: string | null
  password_reset_url: string | null
  email_count: number
  first_seen_at: string | null
  last_seen_at: string | null
  is_reviewed: boolean
  created_at: string
}

export interface DiscoveredAccountListResponse {
  accounts: DiscoveredAccount[]
  total: number
  limit: number
  offset: number
}

// ─── Assets ──────────────────────────────────────────────────────────────────

export type DeclaredEntityType = "username" | "phone_number" | "device" | "url"

export interface EmailOTPRequest {
  email: string
}

export interface EmailOTPVerify {
  email: string
  code: string
}

export interface AssetDeclarePayload {
  entity_type: DeclaredEntityType
  value: string
}

export interface AssetOut {
  asset_id: string
  entity_type: string
  value: string
  is_verified: boolean
  created_at: string
}

// ─── Integrations ────────────────────────────────────────────────────────────

export interface Integration {
  provider: string
  connected: boolean
  connected_at: string | null
}

export interface IntegrationListResponse {
  integrations: Integration[]
}

export interface ConnectIntegrationPayload {
  api_key: string
}

export interface IntegrationVerifyResponse {
  valid: boolean
  detail: string
}

// ─── Companion ───────────────────────────────────────────────────────────────

export interface SetupTokenResponse {
  setup_token: string
  expires_in: number
  user_id: string
}

export interface CompanionStatusResponse {
  connected: boolean
  last_seen_at: string | null
  platform: string | null
  version: string | null
  extension_count: number
}

// ─── API error ───────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
