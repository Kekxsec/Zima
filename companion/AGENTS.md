# Companion Agent Guide

Read [../.claude/AGENTS.md](/Users/max/Zima/.claude/AGENTS.md) first. Companion architecture notes live in `Brain/Companion/`.

## Scope

- `companion/src/`
- `companion/baselines/`
- `companion/Makefile`

## Run And Test

```bash
cd companion
cargo build
cargo test
cargo fmt --check
cargo clippy -- -D warnings
```

## Companion Invariants

- Visibility-only in Phase 1. No direct remediation changes on the host.
- No direct database writes. All backend communication is HTTP API only.
- Keep browser baseline JSON files versioned and in sync with collector expectations.
