// companion/src/auth.rs
use anyhow::{Context, Result};

const SERVICE: &str = "zima-companion";
const ACCOUNT: &str = "companion-token";

pub fn store_token(token: &str) -> Result<()> {
    let entry = keyring::Entry::new(SERVICE, ACCOUNT)
        .context("Failed to create keychain entry")?;
    entry.set_password(token)
        .context("Failed to store companion token in keychain")?;
    Ok(())
}

pub fn load_token() -> Result<String> {
    let entry = keyring::Entry::new(SERVICE, ACCOUNT)
        .context("Failed to create keychain entry")?;
    entry.get_password()
        .context("No companion token found in keychain — run 'zima-companion setup' first")
}

pub fn delete_token() -> Result<()> {
    let entry = keyring::Entry::new(SERVICE, ACCOUNT)
        .context("Failed to create keychain entry")?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()), // already gone
        Err(e) => Err(anyhow::anyhow!("Failed to delete token: {e}")),
    }
}
