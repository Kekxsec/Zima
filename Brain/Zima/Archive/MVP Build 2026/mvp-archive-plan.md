---
tags: [zima, mvp, archive, docs]
created: 2026-04-01
---

← [[MVP Master|Stage Progress]]

# MVP Archive Plan

## Purpose

The `MVP Build` folder should be archived only after the MVP is complete in the sense defined by Stage 08:

- the hardening checklist is closed
- the launch gate is passed
- the docs are no longer active build instructions

Until then, these files remain working project documents.

## Archive Trigger

Archive the MVP docs only when all of the following are true:

1. Stage 08 is marked complete.
2. The launch-hardening items have been verified, not just partially implemented.
3. The current system of record for ongoing development is Stage 09 or later.
4. `MVP Master.md` is updated one final time to mark the MVP complete.
5. Any unresolved launch blockers have a new home outside the MVP folder.

## What To Archive

Archive these files together as one historical set:

- `stage-00-environment-and-tooling.md`
- `stage-00-index.md`
- `stage-00b-railway-deployment.md`
- `stage-01-scaffold.md`
- `stage-01b-audit-threat-validation.md`
- `stage-02-otp-auth.md`
- `stage-02b-testing-foundation.md`
- `stage-03-signal-pipeline.md`
- `stage-04-provider-and-module.md`
- `stage-05-correlation-scoring-remediation.md`
- `stage-06-jobs-api-orchestration.md`
- `stage-06b-breach-alerts-and-stale-scans.md`
- `stage-07-gdpr-and-billing.md`
- `stage-08-pre-launch-hardening.md`
- `MVP Master.md`
- `MVP Next Steps.md`
- `MVP - Road to Launch.md`
- `launch-execution-guide.md`
- `pre-stage-06-signal-registry-handoff.md`

Keep these review/transition files alongside the archive:

- `mvp-completion-review-2026-04-01.md`
- `mvp-archive-plan.md`

## Suggested Archive Structure

When the time comes, move the historical files under something like:

```text
Brain/Zima/Archive/MVP Build 2026/
```

or:

```text
Brain/Zima/MVP Archive/
```

Use one archive location consistently. Do not split the stage files across multiple destinations.

## Before Archiving

Do these first:

1. Add a final status note to `MVP Master.md` saying the MVP is complete and archived.
2. Create or update the current planning file for the next active stage.
3. Replace links in active notes that still point to MVP stage files.
4. Preserve one top-level index note that points from current planning docs to the historical archive.

## After Archiving

The active planning surface should become:

- `stage-09-execution-policy-and-security-hardening.md`
- any later stage files
- current launch or operations notes

The archive should be treated as:

- historical implementation record
- reference material
- not the live source of priorities

## Current Status

Do not archive yet.

Reason:

- Stages 6 and 7 are implemented, but Stage 8 is still open.
- The MVP codebase is ahead of the docs, but the MVP launch gate has not been fully verified.
