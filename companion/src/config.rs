// companion/src/config.rs
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
pub struct CompanionConfig {
    pub backend_url: String,
    pub user_id: String,
}

fn config_path() -> Result<PathBuf> {
    let home = dirs::home_dir().context("Cannot determine home directory")?;
    Ok(home.join(".zima").join("companion.toml"))
}

pub fn save(cfg: &CompanionConfig) -> Result<()> {
    let path = config_path()?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("Cannot create config dir: {}", parent.display()))?;
    }
    let contents = toml::to_string(cfg).context("Failed to serialise config")?;
    std::fs::write(&path, contents)
        .with_context(|| format!("Cannot write config to: {}", path.display()))?;
    Ok(())
}

pub fn load() -> Result<CompanionConfig> {
    let path = config_path()?;
    let contents = std::fs::read_to_string(&path)
        .with_context(|| format!("Cannot read config from: {}", path.display()))?;
    toml::from_str(&contents).context("Failed to parse companion config")
}
