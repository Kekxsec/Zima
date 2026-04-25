// companion/src/main.rs
use anyhow::Result;
use clap::{Parser, Subcommand};
use tracing_subscriber::EnvFilter;

mod auth;
mod client;
mod collectors;
mod config;
mod models;
mod snapshot;

#[derive(Parser)]
#[command(
    name = "zima-companion",
    version,
    about = "Zima companion daemon — collects browser and device state"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Register this machine with the Zima backend using a setup token
    Setup {
        /// One-time setup token from the Zima web dashboard
        #[arg(long)]
        token: String,

        /// Zima backend URL (e.g. https://app.zima.io)
        #[arg(long)]
        backend: String,

        /// Your Zima user UUID (shown on the setup page)
        #[arg(long)]
        user_id: String,
    },

    /// Start the companion daemon (collect and post snapshots every 5 minutes)
    Run {
        /// Interval between snapshots in seconds (default: 300)
        #[arg(long, default_value = "300")]
        interval: u64,
    },

    /// Collect and post a single snapshot immediately
    Snapshot,

    /// Show the current connection status
    Status,

    /// Remove stored credentials from the OS keychain
    Reset,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Setup {
            token,
            backend,
            user_id,
        } => {
            setup(token, backend, user_id).await?;
        }
        Commands::Run { interval } => {
            run_daemon(interval).await?;
        }
        Commands::Snapshot => {
            post_snapshot().await?;
        }
        Commands::Status => {
            show_status().await?;
        }
        Commands::Reset => {
            reset().await?;
        }
    }

    Ok(())
}

async fn setup(token: String, backend: String, user_id: String) -> Result<()> {
    use sha2::{Digest, Sha256};

    let machine_id_raw = collectors::os::machine_id()?;
    let machine_id = hex::encode(Sha256::digest(machine_id_raw.as_bytes()));

    let platform = std::env::consts::OS.to_string();
    let version = env!("CARGO_PKG_VERSION").to_string();

    let c = client::CompanionClient::new(backend.clone(), None)?;
    let resp = c
        .register(models::RegisterRequest {
            setup_token: token,
            user_id: user_id.clone(),
            machine_id,
            platform,
            version,
        })
        .await?;

    auth::store_token(&resp.companion_token)?;

    let cfg = config::CompanionConfig {
        backend_url: backend,
        user_id,
    };
    config::save(&cfg)?;

    println!("Companion registered successfully.");
    Ok(())
}

async fn run_daemon(interval_secs: u64) -> Result<()> {
    use std::time::Duration;
    use tokio::time;

    println!("Starting Zima companion daemon (interval: {interval_secs}s)");

    let mut ticker = time::interval(Duration::from_secs(interval_secs));
    loop {
        ticker.tick().await;
        if let Err(e) = post_snapshot().await {
            tracing::error!("Snapshot failed: {e:#}");
        }
    }
}

async fn post_snapshot() -> Result<()> {
    let cfg = config::load()?;
    let token = auth::load_token()?;
    let c = client::CompanionClient::new(cfg.backend_url, Some(token))?;
    snapshot::collect_and_send(&c).await
}

async fn show_status() -> Result<()> {
    let cfg = config::load()?;
    let token = auth::load_token()?;
    let c = client::CompanionClient::new(cfg.backend_url, Some(token))?;
    let s = c.get_status().await?;
    println!("Connected:       {}", s.connected);
    println!(
        "Last seen:       {}",
        s.last_seen_at.unwrap_or_else(|| "never".into())
    );
    println!(
        "Platform:        {}",
        s.platform.unwrap_or_else(|| "unknown".into())
    );
    println!(
        "Version:         {}",
        s.version.unwrap_or_else(|| "unknown".into())
    );
    println!("Extension count: {}", s.extension_count);
    Ok(())
}

async fn reset() -> Result<()> {
    auth::delete_token()?;
    println!("Companion credentials removed from keychain.");
    Ok(())
}
