// companion/src/snapshot.rs
use anyhow::Result;
use serde_json::json;

use crate::client::CompanionClient;
use crate::collectors::{browser, os};

pub async fn collect_and_send(client: &CompanionClient) -> Result<()> {
    let browsers = browser::collect()?;
    let os_info = os::collect()?;

    let raw = json!({
        "browsers": browsers,
        "os": os_info,
        "collected_at": chrono_now_iso(),
    });

    client.post_snapshot(raw).await?;
    tracing::info!("Snapshot posted successfully");
    Ok(())
}

fn chrono_now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Simple ISO-8601 UTC without pulling in chrono — backend accepts any string
    format!("{}Z", secs)
}
