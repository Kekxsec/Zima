// companion/src/snapshot.rs
use anyhow::Result;
use chrono::SecondsFormat;
use serde_json::json;

use crate::client::CompanionClient;
use crate::collectors::{browser, os};

pub async fn collect_and_send(client: &CompanionClient) -> Result<()> {
    let browsers = browser::collect()?;
    let os_info = os::collect()?;

    let raw = json!({
        "browsers": browsers,
        "os": os_info,
        "collected_at": chrono::Utc::now().to_rfc3339_opts(SecondsFormat::Millis, true),
    });

    client.post_snapshot(raw).await?;
    tracing::info!("Snapshot posted successfully");
    Ok(())
}
