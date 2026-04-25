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
    restrict_owner_only(&path)?;
    Ok(())
}

#[cfg(unix)]
fn restrict_owner_only(path: &std::path::Path) -> Result<()> {
    use std::os::unix::fs::PermissionsExt;
    let perms = std::fs::Permissions::from_mode(0o600);
    std::fs::set_permissions(path, perms)
        .with_context(|| format!("Cannot tighten permissions on {}", path.display()))?;
    Ok(())
}

#[cfg(not(unix))]
fn restrict_owner_only(_path: &std::path::Path) -> Result<()> {
    // On Windows the file inherits the user-profile ACL, which is owner-only by default.
    Ok(())
}

pub fn load() -> Result<CompanionConfig> {
    let path = config_path()?;
    let contents = std::fs::read_to_string(&path)
        .with_context(|| format!("Cannot read config from: {}", path.display()))?;
    toml::from_str(&contents).context("Failed to parse companion config")
}
