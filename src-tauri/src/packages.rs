//! Extra Python packages for scenes (Settings > Python packages), installed with
//! pip into their own folder. See python/pkgtool.py.

use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;
use tauri::{AppHandle, Manager};

pub fn packages_dir(app: &AppHandle) -> Option<PathBuf> {
    Some(app.path().app_local_data_dir().ok()?.join("python-packages"))
}

async fn run(app: AppHandle, args: Vec<String>) -> Result<Value, String> {
    let paths = crate::worker::runtime_paths(&app);
    let tool = paths.script.with_file_name("pkgtool.py");
    let dir = packages_dir(&app).ok_or("No app data folder.")?;
    tauri::async_runtime::spawn_blocking(move || {
        let mut c = Command::new(&paths.python);
        c.arg("-I").arg(&tool).arg(&dir).args(&args).env("PYTHONUTF8", "1");
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            c.creation_flags(0x0800_0000);
        }
        let out = c.output().map_err(|e| format!("Could not run Python: {e}"))?;
        let text = String::from_utf8_lossy(&out.stdout);
        let line = text.lines().rev().find(|l| l.trim_start().starts_with('{')).unwrap_or("");
        serde_json::from_str(line).map_err(|_| {
            format!("Python packages tool failed. {}", String::from_utf8_lossy(&out.stderr).trim())
        })
    })
    .await
    .map_err(|e| e.to_string())?
}

/// The built-in music library (src-tauri/music in dev, the resources folder when installed),
/// with each track's absolute path filled in.
#[tauri::command]
pub fn music_library(app: AppHandle) -> Result<Value, String> {
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("music");
    let dir = if cfg!(debug_assertions) && dev.is_dir() {
        dev
    } else {
        app.path().resource_dir().map_err(|e| e.to_string())?.join("music")
    };
    let text = std::fs::read_to_string(dir.join("library.json")).map_err(|_| "The music library is missing.".to_string())?;
    let mut lib: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
    if let Some(tracks) = lib.get_mut("tracks").and_then(Value::as_array_mut) {
        for t in tracks {
            if let Some(file) = t.get("file").and_then(Value::as_str).map(str::to_string) {
                t["path"] = Value::String(dir.join(file).to_string_lossy().into_owned());
            }
        }
    }
    Ok(lib)
}

#[tauri::command]
pub async fn packages_list(app: AppHandle) -> Result<Value, String> {
    run(app, vec!["list".into()]).await
}

#[tauri::command]
pub async fn packages_install(app: AppHandle, spec: String) -> Result<Value, String> {
    // Never let a "package name" turn into a pip option.
    if spec.trim().starts_with('-') {
        return Err("Enter a package name.".into());
    }
    run(app, vec!["install".into(), spec.trim().to_string()]).await
}

#[tauri::command]
pub async fn packages_remove(app: AppHandle, name: String) -> Result<Value, String> {
    if name.trim().starts_with('-') {
        return Err("Enter a package name.".into());
    }
    run(app, vec!["remove".into(), name.trim().to_string()]).await
}
