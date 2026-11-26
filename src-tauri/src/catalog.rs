//! Model details from models.dev, and API keys kept in Windows Credential Manager.

use serde_json::{json, Map, Value};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::{Duration, SystemTime};
use tauri::{AppHandle, Manager};

const CATALOG_URL: &str = "https://models.dev/api.json";
const MAX_AGE: Duration = Duration::from_secs(24 * 3600);
const KEYRING_SERVICE: &str = "ManimPro";

fn cache_file(app: &AppHandle) -> PathBuf {
    app.path().app_cache_dir().unwrap_or_else(|_| std::env::temp_dir()).join("models-dev.json")
}

fn download(to: &PathBuf) -> bool {
    if let Some(dir) = to.parent() {
        let _ = std::fs::create_dir_all(dir);
    }
    let tmp = to.with_extension("part");
    let mut c = Command::new("curl.exe");
    c.args(["-sL", "--fail", "--max-time", "60", "-o"]).arg(&tmp).arg(CATALOG_URL).stdin(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x0800_0000);
    }
    let ok = c.status().map(|s| s.success()).unwrap_or(false);
    ok && std::fs::rename(&tmp, to).is_ok()
}

/// Keeps only what the model pickers show, so the UI gets ~10% of the full file.
fn slim(full: &Value) -> Value {
    let mut out = Map::new();
    let Some(providers) = full.as_object() else { return Value::Object(out) };
    for (pid, p) in providers {
        let mut models = Map::new();
        if let Some(ms) = p.get("models").and_then(Value::as_object) {
            for (mid, m) in ms {
                models.insert(
                    mid.clone(),
                    json!({
                        "name": m.get("name"),
                        "family": m.get("family"),
                        "context": m.pointer("/limit/context"),
                        "output": m.pointer("/limit/output"),
                        "input_cost": m.pointer("/cost/input"),
                        "output_cost": m.pointer("/cost/output"),
                        "reasoning": m.get("reasoning"),
                        "tool_call": m.get("tool_call"),
                        "attachment": m.get("attachment"),
                        "open_weights": m.get("open_weights"),
                        "release_date": m.get("release_date"),
                    }),
                );
            }
        }
        out.insert(pid.clone(), json!({ "name": p.get("name"), "env": p.get("env"), "models": models }));
    }
    Value::Object(out)
}

/// The models.dev catalog: refreshed at most once a day, cached on disk for offline use.
#[tauri::command]
pub async fn models_catalog(app: AppHandle, refresh: Option<bool>) -> Result<Value, String> {
    let path = cache_file(&app);
    tauri::async_runtime::spawn_blocking(move || {
        let stale = std::fs::metadata(&path)
            .and_then(|m| m.modified())
            .map(|t| SystemTime::now().duration_since(t).unwrap_or_default() > MAX_AGE)
            .unwrap_or(true);
        if stale || refresh.unwrap_or(false) {
            download(&path);
        }
        let text = std::fs::read_to_string(&path).map_err(|_| "Model details are not available offline yet.".to_string())?;
        let full: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
        Ok(slim(&full))
    })
    .await
    .map_err(|e| e.to_string())?
}

// ------------------------------------------------------------------ keys

fn entry(provider: &str) -> Result<keyring::Entry, String> {
    keyring::Entry::new(KEYRING_SERVICE, &format!("{provider}-api-key")).map_err(|e| e.to_string())
}

pub fn api_key(provider: &str) -> Option<String> {
    entry(provider).ok()?.get_password().ok().filter(|k| !k.trim().is_empty())
}

#[tauri::command]
pub fn set_api_key(provider: String, key: String) -> Result<(), String> {
    let key = key.trim();
    if key.is_empty() {
        return Err("Paste a key first.".into());
    }
    entry(&provider)?.set_password(key).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn clear_api_key(provider: String) -> Result<(), String> {
    match entry(&provider)?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(e.to_string()),
    }
}

/// "••••1234" for a saved key, or null. The key itself never goes to the UI.
#[tauri::command]
pub fn api_key_hint(provider: String) -> Option<String> {
    api_key(&provider).map(|k| {
        let tail: String = k.chars().rev().take(4).collect::<Vec<_>>().into_iter().rev().collect();
        format!("••••{tail}")
    })
}
