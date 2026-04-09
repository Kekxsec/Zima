# Zima Companion — Building & Releasing

## Prerequisites

- Rust stable toolchain (`rustup toolchain install stable`)
- Cross-compilation targets installed (see below)
- On Linux: `gcc-mingw-w64-x86-64` for Windows cross-compilation

## Install targets

```bash
rustup target add aarch64-apple-darwin        # macOS Apple Silicon
rustup target add x86_64-apple-darwin         # macOS Intel
rustup target add x86_64-unknown-linux-gnu    # Linux x86_64
rustup target add x86_64-pc-windows-gnu       # Windows x86_64
```

## Local builds (from `companion/`)

```bash
# macOS universal binary (arm64 + x86_64 merged via lipo)
make build-mac

# Individual targets
make build-mac-arm
make build-mac-x86
make build-linux
make build-windows

# All targets
make build-all

# Output lands in companion/dist/
```

## Development workflow

```bash
cd companion
cargo build              # debug build
cargo test               # run tests
cargo fmt --check        # check formatting
cargo clippy -- -D warnings  # lint (warnings are errors)
```

## Creating a release

1. Ensure all tests pass: `make test && make lint`
2. Bump version in `companion/Cargo.toml`
3. Commit: `git commit -m "chore(companion): bump to vX.Y.Z"`
4. Tag: `git tag companion-vX.Y.Z`
5. Push tag: `git push origin companion-vX.Y.Z`

GitHub Actions (`companion-release.yml`) will:
- Build all four targets in parallel
- Sign macOS binaries if `APPLE_SIGNING_CERT` secret is set
- Create a GitHub Release with all binaries attached

## CI

The `companion-ci.yml` workflow runs on every push or PR that touches `companion/**`:
- `cargo fmt --check`
- `cargo clippy -- -D warnings`
- `cargo test`
- `cargo build`

## macOS Codesigning

To enable codesigning, set these GitHub repository secrets:

| Secret | Description |
|--------|-------------|
| `APPLE_SIGNING_CERT` | Base64-encoded `.p12` certificate |
| `APPLE_CERT_PASSWORD` | Password for the `.p12` |
| `APPLE_SIGNING_IDENTITY` | Developer ID string, e.g. `Developer ID Application: Acme Corp (TEAMID)` |

If these secrets are not set, the codesign step is skipped and the binaries are unsigned (fine for internal/beta use).

## Binary sizes (release profile)

The `Cargo.toml` release profile uses:
- `opt-level = "z"` (optimise for size)
- `lto = true` (link-time optimisation)
- `strip = true` (strip debug symbols)

Expected output sizes: ~3–6 MB depending on platform.

## Directory structure

```
companion/
├── Cargo.toml
├── Cargo.lock
├── rust-toolchain.toml      # pins stable channel + all targets
├── Makefile                 # local build shortcuts
├── .cargo/
│   └── config.toml          # cross-linker config for linux-gnu + windows-gnu
├── baselines/               # browser baseline rule sets (JSON)
│   ├── chrome-v1.json
│   ├── brave-v1.json
│   └── firefox-v1.json
└── src/
    ├── main.rs              # CLI entry point (clap subcommands)
    ├── config.rs            # ~/.zima/companion.toml read/write
    ├── auth.rs              # OS keychain token storage (keyring)
    ├── models.rs            # Serde request/response types
    ├── client.rs            # HTTP client (reqwest + rustls)
    ├── snapshot.rs          # collect_and_send() orchestration
    └── collectors/
        ├── mod.rs
        ├── browser.rs       # walk browser profile dirs, parse manifest.json
        └── os.rs            # platform-gated OS info collection
```
