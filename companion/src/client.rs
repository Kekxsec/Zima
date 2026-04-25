// companion/src/client.rs
use std::time::Duration;

use anyhow::{Context, Result};
use reqwest::header::{AUTHORIZATION, CONTENT_TYPE};

use crate::models::{CompanionStatusResponse, RegisterRequest, RegisterResponse, SnapshotRequest};

const REQUEST_TIMEOUT: Duration = Duration::from_secs(30);
const CONNECT_TIMEOUT: Duration = Duration::from_secs(10);
// Reject server responses larger than this — defends against memory exhaustion.
const MAX_RESPONSE_BYTES: usize = 1024 * 1024;

pub struct CompanionClient {
    base_url: String,
    token: Option<String>,
    http: reqwest::Client,
}

impl CompanionClient {
    pub fn new(base_url: String, token: Option<String>) -> Result<Self> {
        let http = reqwest::Client::builder()
            .use_rustls_tls()
            .timeout(REQUEST_TIMEOUT)
            .connect_timeout(CONNECT_TIMEOUT)
            .build()
            .context("Failed to build HTTP client")?;
        Ok(Self {
            base_url,
            token,
            http,
        })
    }

    fn bearer(&self) -> String {
        format!("Bearer {}", self.token.as_deref().unwrap_or_default())
    }

    async fn read_bounded_json<T: serde::de::DeserializeOwned>(
        resp: reqwest::Response,
        ctx: &'static str,
    ) -> Result<T> {
        let bytes = resp
            .bytes()
            .await
            .with_context(|| format!("{ctx}: response body read failed"))?;
        if bytes.len() > MAX_RESPONSE_BYTES {
            anyhow::bail!(
                "{ctx}: response body {} bytes exceeds {MAX_RESPONSE_BYTES} byte cap",
                bytes.len()
            );
        }
        serde_json::from_slice(&bytes).with_context(|| format!("{ctx}: JSON parse failed"))
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

        Self::read_bounded_json(resp, "register response").await
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

        Self::read_bounded_json(resp, "status response").await
    }
}
