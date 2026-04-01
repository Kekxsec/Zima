---
title: "output / phone / textmagic"
aliases: ["textmagic output", "textmagic signal registry"]
tags: [zima, research, outputs, signal-registry, phone, textmagic, graph_exclude]
type: provider_research_output
provider: textmagic
provider_category: phone
status: not_started
prompt_note: prompt.md
provider_folder: textmagic.md
obsidianUIMode: preview
---
# Zima Integration Research: TextMagic Phone Alert Provider

## Overview

TextMagic is a cloud SMS gateway that exposes a REST API and legacy HTTPS API for sending and receiving text messages, managing two‑way SMS, and receiving delivery status callbacks. It does not expose any security analytics, threat intelligence, or scanning capabilities; its APIs are transport and messaging utilities only. For Zima, TextMagic should be treated as a non‑scan, alerts‑only transport provider that delivers notifications (outbound SMS) and optionally returns delivery status and inbound replies for workflow purposes, not as a signal‑producing security source.[1][2][3][4]

***

## A. API Surface Appendix

This appendix focuses on endpoints and artifacts relevant to a security alerting pipeline: sending SMS alerts, tracking delivery, and receiving inbound replies.

### Authentication and Base Endpoint (API v2)

- **Endpoint base**: `https://rest.textmagic.com/api/v2/`.[2]
- **Auth headers**:
  - `X-TM-Username`: TextMagic account username.[2]
  - `X-TM-Key`: API key generated from the TextMagic account API settings.[2]
- **Methods used**: standard HTTP `GET`, `POST`, `PUT`, `DELETE` with JSON bodies.[2]

**Purpose**: Authenticate and authorize all REST API calls, including message send and inbound message management.[2]

**Supported entity_type(s)**: `phone` (destination and source mobile numbers), `account` (implicit – the authenticated TextMagic account).[3][2]

**Requirements**:
- Valid username and API key generated from the TextMagic Online dashboard.
- HTTPS endpoint; authentication is per‑request using headers.

**Error behavior**:
- Docs state that unsuccessful requests return an HTTP error code with an error message, but do not specify a global error schema.[3]

**Schema notes**:
- No explicit JSON schema is defined for auth failures; response format for auth errors is undocumented/unclear.

**citation_refs**: https://www.textmagic.com/docs/api/start/[2]

***

### POST /api/v2/messages – Send SMS Messages

**Endpoint**: `POST https://rest.textmagic.com/api/v2/messages`.[3]

**Purpose**: Primary endpoint to send single or bulk SMS messages, optionally scheduled or recurring.[3]

**Supported entity_type(s)**: `phone` (recipient numbers), `account` (sender context).[3]

**Auth / execution requirements**:
- Auth via `X-TM-Username` and `X-TM-Key` headers.[2]
- At least one of `contacts`, `lists`, or `phones` must be provided.[3]
- Account must have sufficient SMS credit balance to complete the send.[3]

**Request parameters (body)**:[3]

| Field        | Type     | Required?                                  | Notes |
|-------------|----------|---------------------------------------------|-------|
| `text`      | string   | Supply `text` or `templateId` or both      | SMS body text, UTF‑8, URL‑encoded. |
| `templateId`| integer  | Supply `text` or `templateId` or both      | Template ID; merges contact custom fields. |
| `contacts`  | string   | Need ≥1 of `contacts`/`lists`/`phones`      | Comma‑separated contact IDs. |
| `lists`     | string   | Need ≥1 of `contacts`/`lists`/`phones`      | Comma‑separated list IDs. |
| `phones`    | string   | Need ≥1 of `contacts`/`lists`/`phones`      | Comma‑separated E.164 numbers without `+`. |
| `sendingTime`| integer | Optional                                   | UNIX timestamp for scheduled send. |
| `cutExtra`  | integer  | Optional                                   | `1` to truncate text to `partsCount`, else 400 error. |
| `partsCount`| integer  | Optional                                   | Max parts per recipient (1–6, default 6). |
| `referenceId`| string  | Optional                                   | Custom reference echoed in callbacks. |
| `from`      | string   | Optional                                   | Sender ID (phone or alphanumeric). |
| `rrule`     | string   | Optional                                   | iCal recurrence rule; requires `sendingTime`. |

Requiredness is explicitly indicated in the docs table; unspecified fields are optional.[3]

**Successful response (general)**:[3]

Returned on HTTP success (e.g. 200/201/204) with JSON body:

| Field        | Type     | Presence     | Notes |
|-------------|----------|--------------|-------|
| `id`        | integer  | Always       | ID of the main resource (`message`, `session`, `bulk`, or `schedule`). |
| `href`      | string   | Always       | Link to the main resource path (e.g. `/api/v2/messages/{id}`). |
| `type`      | string   | Always       | Enum: `message`, `session`, `bulk`, or `schedule`. |
| `sessionId` | integer\|null | Conditional | Populated for normal sessions (< 1000 recipients); `null` for bulk. |
| `bulkId`    | integer\|null | Conditional | Populated for bulk sessions (> 1000 recipients). |
| `messageId` | integer\|null | Conditional | Set when exactly one message is in the session. |
| `scheduleId`| integer\|null | Conditional | Set when `sendingTime`/`rrule` are used. |

- For **single‑recipient send**, `type` is `message`, and both `id` and `messageId` are set; `bulkId` and `scheduleId` are `null`.[3]
- For **multi‑recipient non‑bulk sessions**, `type` is `session`, `sessionId` equals `id`, and `messageId` is `null`.[3]
- For **bulk sends** (>1000 recipients), `type` is `bulk`, `bulkId` equals `id`, and `sessionId` is `null` because the session is created after processing.[3]

**Successful no‑hit variant**:
- Not applicable; a valid request that sends to zero recipients is not described. Behavior when all recipients are invalid is undocumented/unclear.[3]

**Partial/limited results**:
- Bulk sessions are queued; the send request returns a `bulk` object, and processing continues asynchronously. Progress is retrievable via `GET /api/v2/bulks/{id}`.[3]

**Error cases**:
- Unsuccessful requests return an HTTP error code (e.g. 400) and an error message; no detailed error schema is provided.[3]
- Example: if `cutExtra` is `0` and text exceeds `partsCount`, the API returns `400 Bad Request`.[3]

**Important example responses**:
- Single message send example returns `id`, `href`, `type: "message"`, `sessionId`, `bulkId: null`, `messageId`, `scheduleId: null`.[3]
- Bulk and template‑based examples show `type` switching between `session` and `bulk` and null vs non‑null ID fields.[3]

**citation_refs**: https://www.textmagic.com/docs/api/send-sms/, https://www.textmagic.com/docs/api/start/[2][3]

***

### Delivery Status Callback for Sent Messages

**Artifact**: Delivery status callback (webhook) triggered by TextMagic when an SMS reaches a final status.[3]

**Purpose**: Notify a client application of per‑message delivery results for sent SMS messages without active polling.[5][3]

**Supported entity_type(s)**: `phone` (sender and receiver numbers), `account` (implicit context), `message` (internal TextMagic message ID).[3]

**Configuration**:
- Callback URL is configured in the TextMagic Online dashboard under **API → Callback URL for delivery notifications**.[3]
- TextMagic validates the callback URL by expecting HTTP 200 OK.[5][3]

**Trigger conditions**:
- Callback is sent when an SMS message enters a **final delivery state**: `d` (delivered), `f` (failed), `j` (rejected), `u` (unknown).[3]

**Request method and encoding**:
- HTTP `POST` with JSON body matching the `message` resource plus `referenceId` (if supplied on send).[3]

**Callback payload fields**:[3]

| Field         | Type    | Notes |
|--------------|---------|-------|
| `id`         | integer | Message ID. |
| `sender`     | string  | Sender ID (phone or alphanumeric). |
| `receiver`   | string  | Recipient phone number. |
| `text`       | string  | Final message text after tag substitution. |
| `price`      | number  | Cost in account currency. |
| `status`     | string  | Final status enum: `d`, `f`, `j`, `u`. |
| `partsCount` | integer | Number of SMS parts billed. |
| `messageTime`| string  | Sending time in ISO8601 format. |
| `charset`    | string  | `ISO-8859-1` or `UTF-16BE`. |
| `firstName`  | string\|null | Contact first name (if resolvable). |
| `lastName`   | string\|null | Contact last name. |
| `country`    | string  | Recipient country ISO code. |
| `referenceId`| string\|null | Custom reference from send request. |

Presence of `firstName`, `lastName`, and `referenceId` is conditional based on available data and request parameters; docs state they "could" be present.[3]

**Error behavior**:
- If the callback endpoint does not return HTTP 200 OK, TextMagic considers the URL invalid and will not deliver callbacks; retry/backoff behavior is not documented.[5][3]

**citation_refs**: https://www.textmagic.com/docs/api/send-sms/, http://apitextmagic.voog.com/https-api/receiving-delivery-notifications-and-incoming-sms-messages-via-callback-urls[5][3]

***

### Incoming Messages Callback (Inbound SMS Webhook)

**Artifact**: Incoming messages callback (webhook) triggered when an inbound SMS reaches the TextMagic server.[1]

**Purpose**: Deliver inbound SMS (replies or messages sent to a dedicated number) to a client application in near real time.[1]

**Supported entity_type(s)**: `phone` (sender and receiver numbers), potentially `account`.

**Configuration**:
- Callback URL is configured under **API → Callback URL for incoming messages** in the TextMagic dashboard.[1]
- Callback URL must respond with HTTP 200 OK; otherwise, TextMagic treats it as invalid and stops delivering inbound messages.[1]

**Trigger conditions**:
- Triggered immediately after an inbound message reaches the TextMagic server.[1]

**Request method and encoding**:
- HTTP `POST` with JSON body representing the `reply` (inbound message) resource.[1]

**Callback payload fields**:[1]

| Field         | Type    | Notes |
|--------------|---------|-------|
| `id`         | integer | Inbound message ID. |
| `sender`     | string  | Sender phone number. |
| `receiver`   | string  | Receiver phone number (dedicated/shared reply number). |
| `messageTime`| string  | Time when message reached the TextMagic server (ISO8601). |
| `text`       | string  | Inbound message text. |

All listed fields appear to be always present for an inbound message per the documented table.[1]

**Error behavior**:
- Only behavior documented is invalidation of callback URL when a 200 OK is not returned. Other error semantics are unclear.[1]

**citation_refs**: https://www.textmagic.com/docs/api/receive-sms/[1]

***

### GET /api/v2/replies – List Inbound Messages

**Endpoint**: `GET /api/v2/replies`.[1]

**Purpose**: Retrieve a paginated collection of inbound messages (replies) via REST instead of using callbacks.[1]

**Supported entity_type(s)**: `phone` (sender/receiver), `account`.

**Auth requirements**:
- Uses the same `X-TM-Username` / `X-TM-Key` authentication.[2]

**Query parameters**:[1]

| Field  | Required? | Type    | Notes |
|--------|-----------|---------|-------|
| `page` | No        | integer | Page number (default 1). |
| `limit`| No        | integer | Results per page (default 10). |

**Successful response** (paginated):[1]

| Field      | Type     | Notes |
|-----------|----------|-------|
| `page`    | integer  | Current page number. |
| `limit`   | integer  | Page size. |
| `pageCount`| integer | Total number of pages. |
| `resources`| array   | Array of `reply` resources. |

Each `reply` resource has the following fields:[1]

| Field         | Type    | Notes |
|--------------|---------|-------|
| `id`         | integer | Inbound message ID. |
| `sender`     | string  | Sender’s phone number. |
| `receiver`   | string  | Receiver’s phone number (dedicated/shared number). |
| `messageTime`| string  | Time message reached the API endpoint. |
| `text`       | string  | Inbound message text. |

Docs present all of these as standard fields; optionality is not indicated, so they are assumed always present for each reply.[1]

**No‑hit variant**:
- Behavior when there are no inbound messages (e.g. empty `resources` array) is not explicitly described but is typical for pagination; marked as inferred.[1]

**Error cases**:
- Standard HTTP error code and message for failures; no specific schema documented.[1]

**citation_refs**: https://www.textmagic.com/docs/api/receive-sms/[1]

***

### GET /api/v2/replies/{id} – Get Single Inbound Message

**Endpoint**: `GET /api/v2/replies/{id}`.[1]

**Purpose**: Retrieve a single inbound message by its numeric ID.[1]

**Supported entity_type(s)**: `phone` (sender/receiver), `message`.

**Auth requirements**:
- Same as other v2 endpoints.[2]

**Path parameter**:
- `id` (integer): unique inbound message ID.[1]

**Successful response**:
- Returns a single `reply` resource with fields: `id`, `sender`, `receiver`, `messageTime`, `text`, with the same semantics as in the list endpoint.[1]

**No‑hit / error**:
- Behavior when ID does not exist (e.g. 404) is not explicitly documented; assume standard HTTP error without structured body schema.[1]

**citation_refs**: https://www.textmagic.com/docs/api/receive-sms/[1]

***

### DELETE /api/v2/replies/{id} – Delete Inbound Message

**Endpoint**: `DELETE /api/v2/replies/{id}`.[1]

**Purpose**: Permanently delete an inbound message from TextMagic (and associated UI views like TextMagic Online and chats).[1]

**Supported entity_type(s)**: `message` (inbound SMS record), with implicit `phone` context.

**Auth requirements**:
- Same as other v2 endpoints.[2]

**Path parameter**:
- `id` (integer): inbound message ID.[1]

**Successful response**:
- Returns HTTP 204 No Content on success; no JSON body.[1]

**Error cases**:
- Non‑204 status with error message for failures; schema not specified.[1]

**citation_refs**: https://www.textmagic.com/docs/api/receive-sms/[1]

***

### Legacy HTTPS API and Callbacks (v1)

The legacy documentation at `apitextmagic.voog.com` describes an older HTTPS API and callback mechanism separate from the v2 REST API.[4][5]

**Key features**:[4]

- HTTPS API commands:
  - `send` – send SMS.
  - `account` – check account balance.
  - `message_status` – retrieve delivery notifications.
  - `receive` – retrieve incoming SMS messages.
  - `delete_reply` – delete incoming messages.
  - `check_number` – validate phone numbers.
  - `callback URLs` – receive incoming SMS and delivery notifications via multipart POST.[4]

**Callback URL behavior**:[5]

- Callback URLs configured in TextMagic; TextMagic validates them by sending HTTP HEAD and expecting 200 OK.
- Uses multipart POST with UTF‑8 encoding.

**Delivery notification callback fields (legacy)**:[5]

| Field        | Notes |
|-------------|-------|
| `message_id`| Unique ID for the message. |
| `timestamp` | Unix time of delivery notification receipt. |
| `status`    | Delivery status (string; values not enumerated here). |
| `credits_cost`| Cost of message in SMS credits. |

**Incoming message callback fields (legacy)**:[5]

| Field        | Notes |
|-------------|-------|
| `message_id`| Unique incoming message ID. |
| `timestamp` | Unix time of inbound message. |
| `from`      | Sender’s phone number. |
| `text`      | Message text (UTF‑8). |

These legacy mechanisms are functionally equivalent to the v2 JSON callbacks but use different field names and encoding; they are mostly relevant if Zima must support historical integrations or customers still on v1.[4][5]

**citation_refs**: http://apitextmagic.voog.com, http://apitextmagic.voog.com/https-api/receiving-delivery-notifications-and-incoming-sms-messages-via-callback-urls[4][5]

***

## B. Module Mapping Table

Target module from the provider map: `alerts_only_not_scan_provider`.

TextMagic provides transport and messaging telemetry, not security findings or scans, so all usages for this module are utility‑only. No module should treat TextMagic outputs as direct security signals.

| module                         | provider_role        | provider_method                                | endpoint_or_artifact                                           | classification  | entity_types        | gating_logic                                                                                                                                              | citation_refs                                                                                                                                      | notes |
|--------------------------------|----------------------|------------------------------------------------|----------------------------------------------------------------|-----------------|---------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------|
| alerts_only_not_scan_provider | non_scan_alerting    | send_sms_alert                                 | `POST /api/v2/messages`                                        | utility_only    | phone, account      | Require valid `X-TM-Username`/`X-TM-Key`, at least one of `contacts`/`lists`/`phones`, and non‑empty `text` or `templateId`; ensure account has credit. | https://www.textmagic.com/docs/api/start/[2], https://www.textmagic.com/docs/api/send-sms/[3]                                           | Used solely to deliver Zima alerts via SMS; no security semantics in response IDs. |
| alerts_only_not_scan_provider | non_scan_alerting    | sms_delivery_status_callback                   | Delivery status callback webhook for sent messages             | utility_only    | phone, message      | Consume callbacks only for delivery telemetry (e.g. `status` in {`d`,`f`,`j`,`u`}); do not elevate to security signals.                               | https://www.textmagic.com/docs/api/send-sms/[3], http://apitextmagic.voog.com/https-api/receiving-delivery-notifications-and-incoming-sms-messages-via-callback-urls[5] | Operational monitoring of alert transport; not a threat indicator. |
| alerts_only_not_scan_provider | non_scan_alerting    | inbound_sms_callback                           | Incoming messages callback webhook                             | utility_only    | phone, message      | Use only if Zima implements SMS ACK/response workflows; treat inbound `text` as user interaction, not as a security event.                            | https://www.textmagic.com/docs/api/receive-sms/[1]                                                                                           | Could be used for "ACK" or "STOP" flows; content is opaque to TextMagic. |
| alerts_only_not_scan_provider | non_scan_alerting    | list_inbound_sms_poll                          | `GET /api/v2/replies`                                          | utility_only    | phone, message      | Same as callback but via polling; only enabled if Zima cannot host callbacks and needs periodic fetch of replies.                                    | https://www.textmagic.com/docs/api/receive-sms/[1]                                                                                           | Latency tied to polling cadence; still not a security signal source. |
| alerts_only_not_scan_provider | non_scan_alerting    | get_inbound_sms_by_id                          | `GET /api/v2/replies/{id}`                                     | utility_only    | phone, message      | Use for troubleshooting a specific inbound SMS related to alert workflows; never generate security findings from this alone.                         | https://www.textmagic.com/docs/api/receive-sms/[1]                                                                                           | Diagnostic only. |
| alerts_only_not_scan_provider | non_scan_alerting    | delete_inbound_sms                             | `DELETE /api/v2/replies/{id}`                                  | utility_only    | message             | Only for hygiene/cleanup; ensure Zima does not rely on TextMagic as the system of record for audit.                                                  | https://www.textmagic.com/docs/api/receive-sms/[1]                                                                                           | Deletion also removes from TextMagic UI and chats. |
| alerts_only_not_scan_provider | non_scan_alerting    | legacy_https_api_send_and_callbacks (optional) | Legacy HTTPS `send`, `message_status`, `receive`, callbacks    | utility_only or out_of_scope | phone, message | Only if legacy customers require v1; treat identically to v2 equivalents. Prefer v2 for new integrations.                                            | http://apitextmagic.voog.com[4], http://apitextmagic.voog.com/https-api/receiving-delivery-notifications-and-incoming-sms-messages-via-callback-urls[5]                  | Recommended to phase out; schema differs and is less convenient than v2 JSON. |

Key conclusion: TextMagic should **not** be registered as a signal‑producing provider in Zima; it is an alert transport / notification utility only.

***

## C. Signal Contract Table

TextMagic does not produce any intrinsic security findings. All of its outputs describe transport status (e.g. delivered, failed) or raw message content without any risk classification. Based on the Zima severity calibration guide and provider role `alerts_only_not_scan_provider`, no standalone security signals should be emitted for this provider.

The table below is intentionally empty to reflect that design.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|-----------------|-------------|----------|----------|-------------------------|------------------|------------|--------------|-------------------|-----------------|-------------------|------------------|-----------------|--------------|-------|

Rationale:
- Delivery status (`status` in {`d`,`f`,`j`,`u`}) is purely transport‑level and does not indicate any compromise, attack, or exposure.[3]
- Inbound SMS content (`text`) is user‑generated free text with no semantics defined by TextMagic; without an external classifier, it is not a security signal.[1]
- TextMagic does not expose any threat‑intel fields (e.g. malware indicators, breach flags, PII exposure markers) that could map to Zima’s security categories.[2][3][1]

***

## D. Severity Rules

Because there are **no signal contracts** for TextMagic, there are no Zima security severities to assign.

If in the future Zima chooses to emit **operational** or **SRE‑style** signals (separate from security) around alert delivery reliability, the following guidelines could apply, but they should live in an observability/ops module, not a security module:

- High proportion of `status = 'f'`/`'j'` for SMS alerts over a window could warrant an internal **medium/high operational severity** (alerts failing to reach users), not a security severity.[3]
- Long unavailability of inbound callbacks (no callbacks despite expected traffic) might warrant an **operational incident** about misconfiguration.[5][1]

These are outside the current Zima security signal registry scope but may be useful for internal reliability monitoring.

***

## E. Confidence Guidance

Even though TextMagic is not signal‑producing for security, confidence guidance still matters for any future use of its data in derived workflows.

### Source reliability

- TextMagic operates as an SMS gateway; delivery statuses are derived from mobile operator receipts and internal gateway state, making them high‑reliability indicators of **transport success/failure**, not security posture.[5][3]
- Inbound message metadata (sender, receiver, timestamps) is system‑generated and typically reliable; the `text` content is user‑supplied and unstructured.[1]

### Freshness / staleness

- Delivery callbacks are triggered at the moment a final delivery status is reached; they are fresh event‑driven indicators of message delivery state.[3]
- Inbound callbacks fire immediately when the message reaches TextMagic; polling via `GET /api/v2/replies` introduces staleness proportional to polling interval.[1]

### Corroboration opportunities

- For operational metrics, delivery status can be corroborated against Zima’s own alert logs (e.g. when the alert was queued vs when TextMagic reported delivery).[3]
- Inbound SMS acknowledgements (e.g. user replies) could be cross‑checked against alert IDs embedded in `text` or `referenceId` to confirm correct correlation.[3][1]

### Calibration TODOs

- If Zima later uses delivery failures as part of user‑facing reliability SLAs, empirically measure the proportion of false delivery statuses (e.g. `delivered` but user claims no receipt) and decide thresholds for ops‑only alerts.
- Define clear separation between **operational confidence** ("did the SMS go out?") and **security confidence** ("is this a compromise?") and ensure TextMagic data only feeds the former.

***

## F. Tags

Since TextMagic does not produce security findings, no Zima security tags (e.g. `breach`, `pii_exposure`, `malware`) should be attached.

If Zima adds a separate **transport/alerting** taxonomy, potential non‑security tags could include: `sms_delivery`, `notification_transport`, `inbound_reply`, but these would belong to a different tag namespace than the security tags provided in the prompt.

***

## G. Implementation Notes

### 1. Mapper vs provider client vs correlation layer

- **Provider client**:
  - Implement thin wrappers for `POST /api/v2/messages`, `GET /api/v2/replies`, `GET /api/v2/replies/{id}`, `DELETE /api/v2/replies/{id}` with strong typing for request/response models but no security semantics.[3][1]
  - Implement webhook receivers for **delivery status** and **incoming messages** that validate signatures/headers if TextMagic adds them in the future (currently not documented) and normalize payloads into internal event models.[3][1]

- **Module mapper (alerts_only_not_scan_provider)**:
  - Map Zima internal alert objects into TextMagic `text`/`templateId` + `phones`/`contacts`/`lists` payloads.[3]
  - Persist minimal operational metadata (TextMagic `id`, `type`, `sessionId`, `bulkId`, `messageId`, `scheduleId`, and `referenceId`) alongside Zima alert records for troubleshooting.[3]
  - Do **not** emit Zima security signals in response to TextMagic callbacks.

- **Correlation layer**:
  - Correlate delivery callbacks and inbound replies to Zima alerts via `referenceId` or tokens in `text` (e.g. embedded alert ID).
  - Optionally compute delivery metrics and user response metrics (ACK rate) as internal KPIs.

### 2. Field paths that must survive parsing

- From send response and callbacks:
  - `id`, `type`, `sessionId`, `bulkId`, `messageId`, `scheduleId` for tracking message lifecycle.[3]
  - `status`, `price`, `partsCount`, `messageTime`, `charset`, `sender`, `receiver`, `referenceId`, `country` from delivery callbacks for operational analytics.[3]

- From inbound callbacks / replies:
  - `id`, `sender`, `receiver`, `messageTime`, `text`.[1]

These fields should be kept intact in any internal event/store model so future operations tooling or audits can reconstruct SMS transactions.

### 3. Null / empty / no‑hit behavior

- `sessionId`, `bulkId`, `messageId`, `scheduleId` may be `null` depending on the send pattern (single, session, bulk, or scheduled).[3]
- Legacy callbacks use different field names (`message_id`, `from`, etc.), so mappers must handle both v1 and v2 schemas if both are supported.[4][5]
- Empty `resources` in `GET /api/v2/replies` is not explicitly documented but should be treated as "no inbound messages"; mapper should handle empty arrays without errors.[1]

### 4. Rate limits, billing, premium constraints

- Docs explicitly reference **credits** and the need for sufficient balance but do not publish rate limit or quota details; those must be discovered via account settings or support.[4][3]
- SMS costs (`price`, `credits_cost`) are billing/ops data and should be stored if needed for cost analytics but are unrelated to security signals.[5][3]

### 5. Deduplication keys / identifiers

- Use `id` (message ID) from v2 callbacks and send responses as the primary key for delivery events.[3]
- For inbound messages, use `id` (reply ID) as the natural key; deduplicate on `(id, sender, receiver, messageTime)` if necessary.[1]
- Legacy callbacks rely on `message_id` as identifier.[5]

### 6. Raw evidence for remediation / audit

- Even though these are not security signals, for audit of alert delivery it is useful to retain:
  - Original send payload (excluding PII not strictly needed) and send response IDs.[3]
  - Delivery callback payloads per message.[3]
  - Inbound reply payloads when they represent user ACKs to critical alerts.[1]

Ensure any retention complies with privacy/telecom requirements for SMS logs.

### 7. What belongs **out of scope**

- Do not attempt to interpret message content (`text`) as security evidence without an explicit, separate content‑analysis module.
- Do not map delivery failures to Zima security severities; they indicate alerting reliability issues, not threats.
- Do not use TextMagic account/number health as a security posture signal; it is an infrastructure concern.

***

## H. Provider Summary for Zima

**Strongest provider characteristics**:

- Reliable, documented APIs for sending SMS alerts and receiving delivery and reply callbacks.[2][1][3]
- Clear per‑message identifiers and status enums (`d`, `f`, `j`, `u`) for transport outcomes.[3]

**What TextMagic should *not* be used for**:

- Threat intelligence, compromise detection, credential leak monitoring, or any scanning activity.[2][1][3]
- Deriving user or device risk posture directly from SMS delivery or content.

**API/auth/rate‑limit/licensing cautions**:

- Requires TextMagic account with SMS credit balance; billing is per message/part.[6][3]
- Uses static username/API key header authentication; secure key storage and rotation are required.[2]
- Public docs do not specify hard rate limits; treat them as unknown and design for backoff/retry on 429/5xx responses.

**Zima classification at current stage**:

- Treat TextMagic as a **utility‑only non_scan_alerting provider**.
- Do **not** register any TextMagic‑backed entries in the Zima security signal registry.
- Integration belongs in the alerting/notification subsystem, not in detection or threat‑intel modules.

***

## I. Confidence Guidance Table

| module                         | signal_type_or_use_case        | source_reliability                                                                 | freshness_considerations                                                                                      | corroboration_rules                                                                                                 | calibration_todo |
|--------------------------------|--------------------------------|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|------------------|
| alerts_only_not_scan_provider | SMS send & delivery telemetry  | High for transport status derived from operator and gateway (`status`, `price`, etc.).[3][5]     | Callbacks fire on final status; polling not required; latency is network/operator‑dependent but usually short.[3] | Cross‑check TextMagic `id`/`status` with Zima alert logs and user confirmations when disputes arise.                | Measure false delivery reports vs user feedback; set operational SLAs, not security severities. |
| alerts_only_not_scan_provider | Inbound SMS replies            | High reliability for metadata (`sender`, `receiver`, `messageTime`); `text` is freeform user content.[1] | Callbacks are near‑real‑time; polling via `/replies` adds delay based on schedule and pagination.[1]      | Correlate inbound `id` and `text` tokens/`referenceId` with originating alerts to avoid misattribution.            | Evaluate how often inbound replies are lost or delayed; decide if additional channels are needed for ACKs. |

***

## J. Structured JSON

```json
{
  "provider": "textmagic",
  "provider_category": "phone",
  "provider_role": "non_scan_alerting",
  "module_mappings": [
    {
      "module": "alerts_only_not_scan_provider",
      "provider_role": "non_scan_alerting",
      "provider_method": "send_sms_alert",
      "endpoint_or_artifact": "POST /api/v2/messages",
      "classification": "utility_only",
      "entity_types": ["phone", "account"],
      "gating_logic": "Require valid X-TM-Username/X-TM-Key headers, at least one of contacts/lists/phones, and non-empty text or templateId; ensure account has sufficient SMS credit.",
      "citation_refs": [
        "https://www.textmagic.com/docs/api/start/",
        "https://www.textmagic.com/docs/api/send-sms/"
      ],
      "notes": "Used solely to deliver Zima alerts via SMS; response IDs have no security semantics."
    },
    {
      "module": "alerts_only_not_scan_provider",
      "provider_role": "non_scan_alerting",
      "provider_method": "sms_delivery_status_callback",
      "endpoint_or_artifact": "Delivery status callback webhook",
      "classification": "utility_only",
      "entity_types": ["phone", "message"],
      "gating_logic": "Consume callbacks only for delivery telemetry (status in {d,f,j,u}); never elevate to security signals.",
      "citation_refs": [
        "https://www.textmagic.com/docs/api/send-sms/",
        "http://apitextmagic.voog.com/https-api/receiving-delivery-notifications-and-incoming-sms-messages-via-callback-urls"
      ],
      "notes": "Operational monitoring of alert transport; not a threat indicator."
    },
    {
      "module": "alerts_only_not_scan_provider",
      "provider_role": "non_scan_alerting",
      "provider_method": "inbound_sms_callback",
      "endpoint_or_artifact": "Incoming messages callback webhook",
      "classification": "utility_only",
      "entity_types": ["phone", "message"],
      "gating_logic": "Use only for SMS ACK/response workflows; treat inbound text as user interaction, not as a security event.",
      "citation_refs": [
        "https://www.textmagic.com/docs/api/receive-sms/"
      ],
      "notes": "Can support ACK/STOP flows; content semantics are external to TextMagic."
    },
    {
      "module": "alerts_only_not_scan_provider",
      "provider_role": "non_scan_alerting",
      "provider_method": "list_inbound_sms_poll",
      "endpoint_or_artifact": "GET /api/v2/replies",
      "classification": "utility_only",
      "entity_types": ["phone", "message"],
      "gating_logic": "Enable only when callbacks are not possible; polling interval determines staleness.",
      "citation_refs": [
        "https://www.textmagic.com/docs/api/receive-sms/"
      ],
      "notes": "Provides a fallback to callbacks; still not a security signal source."
    },
    {
      "module": "alerts_only_not_scan_provider",
      "provider_role": "non_scan_alerting",
      "provider_method": "get_inbound_sms_by_id",
      "endpoint_or_artifact": "GET /api/v2/replies/{id}",
      "classification": "utility_only",
      "entity_types": ["phone", "message"],
      "gating_logic": "Use only for diagnostics of specific inbound SMS entries.",
      "citation_refs": [
        "https://www.textmagic.com/docs/api/receive-sms/"
      ],
      "notes": "Intended for troubleshooting, not detection."
    },
    {
      "module": "alerts_only_not_scan_provider",
      "provider_role": "non_scan_alerting",
      "provider_method": "delete_inbound_sms",
      "endpoint_or_artifact": "DELETE /api/v2/replies/{id}",
      "classification": "utility_only",
      "entity_types": ["message"],
      "gating_logic": "Only for cleanup; ensure Zima does not depend on TextMagic as audit system of record.",
      "citation_refs": [
        "https://www.textmagic.com/docs/api/receive-sms/"
      ],
      "notes": "Also removes messages from TextMagic UI and chats."
    },
    {
      "module": "alerts_only_not_scan_provider",
      "provider_role": "non_scan_alerting",
      "provider_method": "legacy_https_api_send_and_callbacks",
      "endpoint_or_artifact": "Legacy HTTPS send/message_status/receive and callbacks",
      "classification": "utility_only",
      "entity_types": ["phone", "message"],
      "gating_logic": "Support only if needed for legacy customers; prefer v2 for all new integrations.",
      "citation_refs": [
        "http://apitextmagic.voog.com",
        "http://apitextmagic.voog.com/https-api/receiving-delivery-notifications-and-incoming-sms-messages-via-callback-urls"
      ],
      "notes": "Legacy format differs (multipart POST, different field names); consider migration plan."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "alerts_only_not_scan_provider",
      "signal_type_or_use_case": "SMS send & delivery telemetry",
      "source_reliability": "High for transport status derived from operator and gateway (status, price, partsCount, etc.).",
      "freshness_considerations": "Callbacks fire on final status; polling not required; latency depends on operator and network conditions.",
      "corroboration_rules": "Cross-check TextMagic ids and status values against Zima alert logs and, where disputed, user confirmations.",
      "calibration_todo": "Measure discrepancy between reported deliveries and user-reported non-receipt; use results for ops SLAs, not security severities."
    },
    {
      "module": "alerts_only_not_scan_provider",
      "signal_type_or_use_case": "Inbound SMS replies",
      "source_reliability": "High for metadata (sender, receiver, messageTime); text is unstructured user input.",
      "freshness_considerations": "Callbacks are near-real-time; polling via /replies introduces delay proportional to polling frequency.",
      "corroboration_rules": "Correlate inbound ids and reply content tokens/referenceId with originating alerts to avoid misattribution.",
      "calibration_todo": "Assess rate of lost, delayed, or malformed replies and decide whether secondary channels are required for critical ACKs."
    }
  ]
}
```
