// companion/src/models.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize)]
pub struct RegisterRequest {
    pub setup_token: String,
    pub user_id: String,
    pub machine_id: String,
    pub platform: String,
    pub version: String,
}

#[derive(Debug, Deserialize)]
pub struct RegisterResponse {
    pub companion_token: String,
}

#[derive(Debug, Serialize)]
pub struct SnapshotRequest {
    pub raw_snapshot: serde_json::Value,
}

#[derive(Debug, Deserialize)]
pub struct CompanionStatusResponse {
    pub connected: bool,
    pub last_seen_at: Option<String>,
    pub platform: Option<String>,
    pub version: Option<String>,
    pub extension_count: u32,
}
