// companion/src/collectors/os.rs
//
// Collects OS-level security state per platform.
// All subprocess calls are read-only — no mutations.

use anyhow::Result;
use serde::Serialize;
use std::process::Command;

#[derive(Debug, Serialize)]
pub struct OsInfo {
    pub platform: String,
    pub os_version: Option<String>,
    pub disk_encryption: Option<bool>,
    pub sip_enabled: Option<bool>,     // macOS only
    pub firewall_active: Option<bool>, // Linux/macOS
    pub raw: serde_json::Value,        // platform-specific extras
}

/// Returns the stable machine identifier used to compute machine_id.
pub fn machine_id() -> Result<String> {
    _machine_id()
}

pub fn collect() -> Result<OsInfo> {
    _collect()
}

// ─── macOS ───────────────────────────────────────────────────────────────────

#[cfg(target_os = "macos")]
fn _machine_id() -> Result<String> {
    let out = Command::new("ioreg")
        .args(["-rd1", "-c", "IOPlatformExpertDevice"])
        .output()?;
    let text = String::from_utf8_lossy(&out.stdout);
    for line in text.lines() {
        if line.contains("IOPlatformUUID") {
            if let Some(uuid) = line.split('"').nth(3) {
                return Ok(uuid.to_string());
            }
        }
    }
    anyhow::bail!("Could not read IOPlatformUUID from ioreg")
}

#[cfg(target_os = "macos")]
fn _collect() -> Result<OsInfo> {
    let os_version = run_cmd("sw_vers", &["-productVersion"]).ok();

    let fde_out = run_cmd("fdesetup", &["status"]).unwrap_or_default();
    let disk_encryption = Some(fde_out.contains("FileVault is On"));

    let sip_out = run_cmd("csrutil", &["status"]).unwrap_or_default();
    let sip_enabled = Some(sip_out.contains("enabled"));

    let fw_out = run_cmd(
        "/usr/libexec/ApplicationFirewall/socketfilterfw",
        &["--getglobalstate"],
    )
    .unwrap_or_default();
    let firewall_active = Some(fw_out.to_lowercase().contains("enabled"));

    Ok(OsInfo {
        platform: "darwin".into(),
        os_version,
        disk_encryption,
        sip_enabled,
        firewall_active,
        raw: serde_json::json!({
            "fde_output": fde_out,
            "sip_output": sip_out,
        }),
    })
}

// ─── Linux ───────────────────────────────────────────────────────────────────

#[cfg(target_os = "linux")]
fn _machine_id() -> Result<String> {
    std::fs::read_to_string("/etc/machine-id")
        .map(|s| s.trim().to_string())
        .map_err(|e| anyhow::anyhow!("Cannot read /etc/machine-id: {e}"))
}

#[cfg(target_os = "linux")]
fn _collect() -> Result<OsInfo> {
    let os_version = std::fs::read_to_string("/etc/os-release")
        .ok()
        .and_then(|s| {
            s.lines().find(|l| l.starts_with("PRETTY_NAME=")).map(|l| {
                l.trim_start_matches("PRETTY_NAME=")
                    .trim_matches('"')
                    .to_string()
            })
        });

    let ufw_out = run_cmd("ufw", &["status"]).unwrap_or_default();
    let firewall_active = Some(ufw_out.contains("Status: active"));

    let lvm_out = run_cmd("lsblk", &["--output", "NAME,TYPE,FSTYPE", "--json"]).unwrap_or_default();

    Ok(OsInfo {
        platform: "linux".into(),
        os_version,
        disk_encryption: None, // requires parsing lsblk for crypto type — Phase 2
        sip_enabled: None,
        firewall_active,
        raw: serde_json::json!({ "lsblk_json": lvm_out }),
    })
}

// ─── Windows ─────────────────────────────────────────────────────────────────

#[cfg(target_os = "windows")]
fn _machine_id() -> Result<String> {
    let out = Command::new("powershell")
        .args([
            "-NoProfile",
            "-Command",
            "(Get-ItemProperty HKLM:\\SOFTWARE\\Microsoft\\Cryptography).MachineGuid",
        ])
        .output()?;
    Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
}

#[cfg(target_os = "windows")]
fn _collect() -> Result<OsInfo> {
    let info_out = run_cmd(
        "powershell",
        &[
            "-NoProfile",
            "-Command",
            "Get-ComputerInfo | ConvertTo-Json",
        ],
    )
    .unwrap_or_default();

    let bitlocker_out = run_cmd(
        "powershell",
        &[
            "-NoProfile",
            "-Command",
            "Get-BitLockerVolume | Select-Object -ExpandProperty ProtectionStatus",
        ],
    )
    .unwrap_or_default();
    let disk_encryption = Some(bitlocker_out.trim() == "On");

    Ok(OsInfo {
        platform: "windows".into(),
        os_version: None,
        disk_encryption,
        sip_enabled: None,
        firewall_active: None,
        raw: serde_json::json!({ "computer_info": info_out }),
    })
}

// ─── Unsupported ─────────────────────────────────────────────────────────────

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
fn _machine_id() -> Result<String> {
    anyhow::bail!("Unsupported platform for machine_id")
}

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
fn _collect() -> Result<OsInfo> {
    Ok(OsInfo {
        platform: std::env::consts::OS.to_string(),
        os_version: None,
        disk_encryption: None,
        sip_enabled: None,
        firewall_active: None,
        raw: serde_json::json!({}),
    })
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

fn run_cmd(program: &str, args: &[&str]) -> Result<String> {
    let out = Command::new(program).args(args).output()?;
    Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
}
