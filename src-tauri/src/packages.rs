//! Extra Python packages for scenes (Settings > Python packages), installed with
//! pip into their own folder. See python/pkgtool.py.

use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;
use tauri::{AppHandle, Manager};

pub fn packages_dir(app: &AppHandle) -> Option<PathBuf> {
    Some(app.path().app_local_data_dir().ok()?.join("python-packages"))
}

/// ManimGL lives in its own folder: its versions of NumPy, Pillow and ManimPango differ from Manim's.
pub fn manimgl_dir(app: &AppHandle) -> Option<PathBuf> {
    Some(app.path().app_local_data_dir().ok()?.join("manimgl"))
}

async fn run(app: AppHandle, args: Vec<String>) -> Result<Value, String> {
    let dir = packages_dir(&app).ok_or("No app data folder.")?;
    run_in(app, dir, args).await
}

async fn run_in(app: AppHandle, dir: PathBuf, args: Vec<String>) -> Result<Value, String> {
    let paths = crate::worker::runtime_paths(&app);
    let tool = paths.script.with_file_name("pkgtool.py");
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

/// Folder with the plugin starter scenes (next to the worker script).
#[tauri::command]
pub fn plugin_starters_dir(app: AppHandle) -> String {
    crate::worker::runtime_paths(&app).script.with_file_name("plugin_starters").to_string_lossy().into_owned()
}

#[tauri::command]
pub async fn manimgl_status(app: AppHandle) -> Result<Value, String> {
    let dir = manimgl_dir(&app).ok_or("No app data folder.")?;
    if !dir.join("manimlib").is_dir() {
        return Ok(serde_json::json!({ "installed": false }));
    }
    let list = run_in(app, dir, vec!["list".into()]).await?;
    let version = list
        .get("packages")
        .and_then(Value::as_array)
        .and_then(|a| a.iter().find(|p| p.get("name").and_then(Value::as_str).is_some_and(|n| n.eq_ignore_ascii_case("manimgl"))))
        .and_then(|p| p.get("version").cloned());
    Ok(serde_json::json!({ "installed": true, "version": version }))
}

#[tauri::command]
pub async fn manimgl_install(app: AppHandle) -> Result<Value, String> {
    let dir = manimgl_dir(&app).ok_or("No app data folder.")?;
    // From GitHub (3Blue1Brown's current video code needs it), with setuptools < 81 for pkg_resources.
    run_in(app, dir, vec!["install-manimgl".into()]).await
}

#[tauri::command]
pub fn manimgl_remove(app: AppHandle) -> Result<(), String> {
    let dir = manimgl_dir(&app).ok_or("No app data folder.")?;
    if dir.exists() {
        std::fs::remove_dir_all(&dir).map_err(|e| e.to_string())?;
    }
    Ok(())
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
