// companion/src/collectors/browser.rs
//
// Reads browser profile directories on the host machine and returns a list of
// installed extensions per browser. Mirrors the logic in the Python
// browser_extension_detector provider — reads manifest.json from each extension dir.

use anyhow::Result;
use serde::Serialize;
use std::path::{Path, PathBuf};

// Browser-extension manifests are tiny JSON files. Reject anything larger than
// this — defends against accidental (or hostile) huge files filling memory.
const MAX_MANIFEST_BYTES: u64 = 256 * 1024;

#[derive(Debug, Serialize)]
pub struct Extension {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct BrowserProfile {
    pub browser: String,
    pub profile_path: String,
    pub extensions: Vec<Extension>,
}

pub fn collect() -> Result<Vec<BrowserProfile>> {
    let mut profiles: Vec<BrowserProfile> = Vec::new();

    for (browser_name, base_paths) in browser_base_paths() {
        for base in base_paths {
            if !base.exists() {
                continue;
            }
            // Each subdirectory of the base is a profile (Default, Profile 1, …)
            let Ok(entries) = std::fs::read_dir(&base) else {
                continue;
            };
            for entry in entries.flatten() {
                let profile_dir = entry.path();
                let ext_dir = profile_dir.join("Extensions");
                if !ext_dir.is_dir() {
                    continue;
                }
                let extensions = read_extensions(&ext_dir);
                if !extensions.is_empty() {
                    profiles.push(BrowserProfile {
                        browser: browser_name.clone(),
                        profile_path: profile_dir.display().to_string(),
                        extensions,
                    });
                }
            }
        }
    }

    Ok(profiles)
}

fn read_extensions(ext_dir: &Path) -> Vec<Extension> {
    let mut exts = Vec::new();
    let Ok(ids) = std::fs::read_dir(ext_dir) else {
        return exts;
    };
    for id_entry in ids.flatten() {
        let id = id_entry.file_name().to_string_lossy().to_string();
        // Each id dir contains version subdirectories
        let Ok(versions) = std::fs::read_dir(id_entry.path()) else {
            continue;
        };
        for ver_entry in versions.flatten() {
            let manifest_path = ver_entry.path().join("manifest.json");
            if !manifest_path.is_file() {
                continue;
            }
            let metadata = match std::fs::metadata(&manifest_path) {
                Ok(m) => m,
                Err(_) => continue,
            };
            if metadata.len() > MAX_MANIFEST_BYTES {
                tracing::warn!(
                    "Skipping oversized manifest at {}: {} bytes",
                    manifest_path.display(),
                    metadata.len()
                );
                continue;
            }
            if let Ok(data) = std::fs::read_to_string(&manifest_path) {
                if let Ok(manifest) = serde_json::from_str::<serde_json::Value>(&data) {
                    let name = manifest
                        .get("name")
                        .and_then(|v| v.as_str())
                        .unwrap_or(&id)
                        .to_string();
                    let version = manifest
                        .get("version")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown")
                        .to_string();
                    let description = manifest
                        .get("description")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string());
                    exts.push(Extension {
                        id: id.clone(),
                        name,
                        version,
                        description,
                    });
                    break; // only read the first version dir
                }
            }
        }
    }
    exts
}

/// Returns (browser_name, [candidate profile base directories]) per platform.
fn browser_base_paths() -> Vec<(String, Vec<PathBuf>)> {
    let home = dirs::home_dir().unwrap_or_default();

    #[cfg(target_os = "macos")]
    {
        let lib = home.join("Library/Application Support");
        vec![
            ("chrome".into(), vec![lib.join("Google/Chrome")]),
            (
                "brave".into(),
                vec![lib.join("BraveSoftware/Brave-Browser")],
            ),
            ("edge".into(), vec![lib.join("Microsoft Edge")]),
        ]
    }

    #[cfg(target_os = "linux")]
    {
        let config = home.join(".config");
        vec![
            ("chrome".into(), vec![config.join("google-chrome")]),
            (
                "brave".into(),
                vec![config.join("BraveSoftware/Brave-Browser")],
            ),
            ("edge".into(), vec![config.join("microsoft-edge")]),
        ]
    }

    #[cfg(target_os = "windows")]
    {
        let appdata = dirs::data_dir().unwrap_or_default();
        vec![
            (
                "chrome".into(),
                vec![appdata.join("Google/Chrome/User Data")],
            ),
            (
                "brave".into(),
                vec![appdata.join("BraveSoftware/Brave-Browser/User Data")],
            ),
            (
                "edge".into(),
                vec![appdata.join("Microsoft/Edge/User Data")],
            ),
        ]
    }

    #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
    {
        vec![]
    }
}
