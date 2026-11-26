//! ElevenLabs text-to-speech: voiceovers for the audio track.
//!
//! The API key lives in Windows Credential Manager (see catalog.rs). Requests go
//! through curl.exe; the key is passed in a config read from stdin, so it never
//! appears on a command line or in the process list.

use serde::Serialize;
use serde_json::{json, Value};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

const API: &str = "https://api.elevenlabs.io";

fn key() -> Result<String, String> {
    crate::catalog::api_key("elevenlabs").ok_or_else(|| "Add your ElevenLabs API key in Settings, under Accounts.".to_string())
}

/// Runs one request. Returns (HTTP status, response body).
fn request(method: &str, url: &str, body: Option<&Value>, out: Option<&Path>) -> Result<(u16, Vec<u8>), String> {
    let key = key()?;
    let mut c = Command::new("curl.exe");
    c.args(["-sS", "--max-time", "180", "-X", method, "-K", "-", "-w", "\n%{http_code}"]);
    if let Some(path) = out {
        c.arg("-o").arg(path);
    }
    c.arg(url).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x0800_0000);
    }
    let mut child = c.spawn().map_err(|e| format!("Could not reach ElevenLabs: {e}"))?;
    {
        // curl config syntax: one option per line, values in double quotes.
        let mut cfg = format!("header = \"xi-api-key: {}\"\nheader = \"Accept: application/json, audio/mpeg\"\n", key.replace('"', ""));
        if let Some(b) = body {
            cfg.push_str("header = \"Content-Type: application/json\"\n");
            let data = b.to_string().replace('\\', "\\\\").replace('"', "\\\"");
            cfg.push_str(&format!("data = \"{data}\"\n"));
        }
        let mut stdin = child.stdin.take().ok_or("no stdin")?;
        stdin.write_all(cfg.as_bytes()).map_err(|e| e.to_string())?;
    }
    let output = child.wait_with_output().map_err(|e| e.to_string())?;
    if !output.status.success() {
        return Err(format!("Could not reach ElevenLabs: {}", String::from_utf8_lossy(&output.stderr).trim()));
    }
    let mut stdout = output.stdout;
    let split = stdout.iter().rposition(|&b| b == b'\n').unwrap_or(0);
    let code: u16 = String::from_utf8_lossy(&stdout[split..]).trim().parse().unwrap_or(0);
    stdout.truncate(split);
    Ok((code, stdout))
}

fn api_error(code: u16, body: &[u8]) -> String {
    let v: Value = serde_json::from_slice(body).unwrap_or(Value::Null);
    let detail = v
        .pointer("/detail/message")
        .or_else(|| v.pointer("/detail/0/msg"))
        .or_else(|| v.get("detail"))
        .and_then(|d| d.as_str().map(str::to_string).or_else(|| Some(d.to_string())))
        .filter(|s| s != "null");
    match code {
        401 => "ElevenLabs rejected the API key. Check it in Settings, under Accounts.".into(),
        402 | 429 => detail.unwrap_or_else(|| "ElevenLabs quota or rate limit reached.".into()),
        _ => format!("ElevenLabs error {code}: {}", detail.unwrap_or_else(|| "no details".into())),
    }
}

#[derive(Serialize)]
pub struct VoiceAccount {
    tier: String,
    used: u64,
    limit: u64,
}

/// Plan and characters used, or None when no key is saved.
#[tauri::command]
pub async fn voice_account() -> Result<Option<VoiceAccount>, String> {
    if key().is_err() {
        return Ok(None);
    }
    tauri::async_runtime::spawn_blocking(|| {
        let (code, body) = request("GET", &format!("{API}/v1/user"), None, None)?;
        if code != 200 {
            return Err(api_error(code, &body));
        }
        let v: Value = serde_json::from_slice(&body).map_err(|e| e.to_string())?;
        let s = v.get("subscription").cloned().unwrap_or(Value::Null);
        Ok(Some(VoiceAccount {
            tier: s.get("tier").and_then(Value::as_str).unwrap_or("unknown").to_string(),
            used: s.get("character_count").and_then(Value::as_u64).unwrap_or(0),
            limit: s.get("character_limit").and_then(Value::as_u64).unwrap_or(0),
        }))
    })
    .await
    .map_err(|e| e.to_string())?
}

#[derive(Serialize)]
pub struct Voice {
    id: String,
    name: String,
    category: String,
    description: String,
    labels: Vec<String>,
    preview_url: Option<String>,
}

/// The voices this account can use (premade, cloned, library voices added to it).
#[tauri::command]
pub async fn voice_list() -> Result<Vec<Voice>, String> {
    tauri::async_runtime::spawn_blocking(|| {
        let mut voices = Vec::new();
        let mut token: Option<String> = None;
        for _ in 0..5 {
            let mut url = format!("{API}/v2/voices?page_size=100&sort=name&sort_direction=asc");
            if let Some(t) = &token {
                url.push_str(&format!("&next_page_token={t}"));
            }
            let (code, body) = request("GET", &url, None, None)?;
            if code != 200 {
                return Err(api_error(code, &body));
            }
            let v: Value = serde_json::from_slice(&body).map_err(|e| e.to_string())?;
            for item in v.get("voices").and_then(Value::as_array).cloned().unwrap_or_default() {
                let s = |k: &str| item.get(k).and_then(Value::as_str).unwrap_or("").to_string();
                let labels = item
                    .get("labels")
                    .and_then(Value::as_object)
                    .map(|m| m.values().filter_map(Value::as_str).map(str::to_string).collect())
                    .unwrap_or_default();
                voices.push(Voice {
                    id: s("voice_id"),
                    name: s("name"),
                    category: s("category"),
                    description: s("description"),
                    labels,
                    preview_url: item.get("preview_url").and_then(Value::as_str).map(str::to_string),
                });
            }
            token = v.get("next_page_token").and_then(Value::as_str).map(str::to_string);
            if !v.get("has_more").and_then(Value::as_bool).unwrap_or(false) || token.is_none() {
                break;
            }
        }
        Ok(voices)
    })
    .await
    .map_err(|e| e.to_string())?
}

fn unique(dir: &Path, stem: &str) -> PathBuf {
    let clean: String = stem
        .chars()
        .map(|c| if c.is_alphanumeric() || c == ' ' || c == '-' || c == '_' { c } else { ' ' })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    let base: String = if clean.is_empty() { "voiceover".into() } else { clean.chars().take(40).collect() };
    let mut p = dir.join(format!("{base}.mp3"));
    let mut n = 2;
    while p.exists() {
        p = dir.join(format!("{base} {n}.mp3"));
        n += 1;
    }
    p
}

/// Generates speech and saves it as an MP3 in <project>/assets/audio. Returns the path.
#[tauri::command]
pub async fn voice_generate(
    project_dir: String,
    text: String,
    voice_id: String,
    model_id: Option<String>,
    name: Option<String>,
    speed: Option<f64>,
    stability: Option<f64>,
) -> Result<String, String> {
    let text = text.trim().to_string();
    if text.is_empty() {
        return Err("Write the text to speak first.".into());
    }
    tauri::async_runtime::spawn_blocking(move || {
        let dir = Path::new(&project_dir).join("assets").join("audio");
        std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
        let stem = name.filter(|n| !n.trim().is_empty()).unwrap_or_else(|| text.chars().take(32).collect());
        let path = unique(&dir, &stem);
        let tmp = path.with_extension("part");
        let body = json!({
            "text": text,
            "model_id": model_id.unwrap_or_else(|| "eleven_multilingual_v2".into()),
            "voice_settings": {
                "stability": stability.unwrap_or(0.5),
                "similarity_boost": 0.75,
                "speed": speed.unwrap_or(1.0),
            },
        });
        let url = format!("{API}/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128");
        let (code, _) = request("POST", &url, Some(&body), Some(&tmp))?;
        if code != 200 {
            let err = std::fs::read(&tmp).unwrap_or_default();
            let _ = std::fs::remove_file(&tmp);
            return Err(api_error(code, &err));
        }
        std::fs::rename(&tmp, &path).map_err(|e| e.to_string())?;
        Ok(path.to_string_lossy().into_owned())
    })
    .await
    .map_err(|e| e.to_string())?
}
