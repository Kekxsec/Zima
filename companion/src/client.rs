// companion/src/client.rs
use anyhow::{Context, Result};
use reqwest::header::{AUTHORIZATION, CONTENT_TYPE};

use crate::models::{
    CompanionStatusResponse, RegisterRequest, RegisterResponse, SnapshotRequest,
};

pub struct CompanionClient {
    base_url: String,
    token: Option<String>,
    http: reqwest::Client,
}

impl CompanionClient {
    pub fn new(base_url: String, token: Option<String>) -> Self {
        Self {
            base_url,
            token,
            http: reqwest::Client::builder()
                .use_rustls_tls()
                .build()
                .expect("Failed to build HTTP client"),
        }
    }

    fn bearer(&self) -> String {
        format!(
            "Bearer {}",
            self.token.as_deref().unwrap_or_default()
        )
    }

    pub async fn register(&self, payload: RegisterRequest) -> Result<RegisterResponse> {
        let url = format!("{}/api/v1/companion/register", self.base_url);
        let resp = self
            .http
            .post(&url)
            .header(CONTENT_TYPE, "application/json")
            .json(&payload)
            .send()
            .await
            .context("POST /companion/register request failed")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            anyhow::bail!("Register failed ({status}): {body}");
        }

        resp.json::<RegisterResponse>()
            .await
            .context("Failed to parse register response")
    }

    pub async fn post_snapshot(&self, raw: serde_json::Value) -> Result<()> {
        let url = format!("{}/api/v1/companion/snapshot", self.base_url);
        let resp = self
            .http
            .post(&url)
            .header(AUTHORIZATION, self.bearer())
            .header(CONTENT_TYPE, "application/json")
            .json(&SnapshotRequest { raw_snapshot: raw })
            .send()
            .await
            .context("POST /companion/snapshot request failed")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            anyhow::bail!("Snapshot rejected ({status}): {body}");
        }

        Ok(())
    }

    pub async fn get_status(&self) -> Result<CompanionStatusResponse> {
        let url = format!("{}/api/v1/companion/status", self.base_url);
        let resp = self
            .http
            .get(&url)
            .header(AUTHORIZATION, self.bearer())
            .send()
            .await
            .context("GET /companion/status request failed")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            anyhow::bail!("Status check failed ({status}): {body}");
        }

        resp.json::<CompanionStatusResponse>()
            .await
            .context("Failed to parse status response")
    }
}
