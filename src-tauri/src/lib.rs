mod agents;
mod bridge;
mod catalog;
mod latex;
mod projects;
mod voice;
mod worker;

use serde::Serialize;
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Manager, State};
use worker::Worker;

const SAMPLE_SCENE: &str = include_str!("../python/sample_scene.py");

#[derive(Serialize)]
struct ProjectInfo {
    dir: String,
    media_dir: String,
    /// Scene files, in subfolders too.
    files: Vec<String>,
    /// Every folder the user made (empty ones included), for the file tree.
    folders: Vec<String>,
    /// Audio files under assets/.
    audio: Vec<String>,
    timeline: Option<Value>,
}

const AUDIO_EXT: &[&str] = &["mp3", "wav", "m4a", "aac", "ogg", "flac", "opus"];

/// Folders ManimPro manages itself; they never show in the file tree.
fn hidden_dir(name: &str) -> bool {
    name.starts_with('.') || name == "__pycache__" || name == "assets" || name == "media" || name == "node_modules"
}

fn walk(dir: &Path, depth: usize, files: &mut Vec<String>, folders: &mut Vec<String>) {
    if depth > 6 {
        return;
    }
    let Ok(entries) = fs::read_dir(dir) else { return };
    for e in entries.flatten() {
        let p = e.path();
        let name = e.file_name().to_string_lossy().into_owned();
        if p.is_dir() {
            if !hidden_dir(&name) {
                folders.push(p.to_string_lossy().into_owned());
                walk(&p, depth + 1, files, folders);
            }
        } else if p.extension().is_some_and(|x| x == "py") {
            files.push(p.to_string_lossy().into_owned());
        }
    }
}

fn walk_audio(dir: &Path, depth: usize, out: &mut Vec<String>) {
    let Ok(entries) = fs::read_dir(dir) else { return };
    for e in entries.flatten() {
        let p = e.path();
        if p.is_dir() && depth < 4 {
            walk_audio(&p, depth + 1, out);
        } else if p
            .extension()
            .and_then(|x| x.to_str())
            .is_some_and(|x| AUDIO_EXT.contains(&x.to_ascii_lowercase().as_str()))
        {
            out.push(p.to_string_lossy().into_owned());
        }
    }
}

fn scan_project(dir: &Path) -> Result<ProjectInfo, String> {
    if !dir.is_dir() {
        return Err(format!("{} is not a folder.", dir.display()));
    }
    let (mut files, mut folders, mut audio) = (Vec::new(), Vec::new(), Vec::new());
    walk(dir, 0, &mut files, &mut folders);
    walk_audio(&dir.join("assets"), 0, &mut audio);
    files.sort_by_key(|f| f.to_lowercase());
    folders.sort_by_key(|f| f.to_lowercase());
    audio.sort_by_key(|f| f.to_lowercase());
    let timeline = fs::read_to_string(dir.join("project.json"))
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok());
    Ok(ProjectInfo {
        dir: dir.to_string_lossy().into_owned(),
        media_dir: dir.join(".manimpro").join("media").to_string_lossy().into_owned(),
        files,
        folders,
        audio,
        timeline,
    })
}

fn inside(project: &Path, path: &Path) -> Result<(), String> {
    let p = path.canonicalize().map_err(|e| e.to_string())?;
    let root = project.canonicalize().map_err(|e| e.to_string())?;
    if p.starts_with(&root) && p != root {
        Ok(())
    } else {
        Err("That is outside the project.".into())
    }
}

fn clean_name(name: &str) -> Result<String, String> {
    let n = name.trim();
    if n.is_empty() || n.contains(['/', '\\', ':', '*', '?', '"', '<', '>', '|']) || n == "." || n == ".." {
        return Err("Use a name without / \\ : * ? \" < > |".into());
    }
    Ok(n.to_string())
}

#[tauri::command]
fn create_folder(project: String, parent: String, name: String) -> Result<String, String> {
    let parent = PathBuf::from(&parent);
    if parent != Path::new(&project) {
        inside(Path::new(&project), &parent)?;
    }
    let path = parent.join(clean_name(&name)?);
    if path.exists() {
        return Err("A file or folder with that name already exists.".into());
    }
    fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    Ok(path.to_string_lossy().into_owned())
}

/// Renames a file or folder in place; returns the new path.
#[tauri::command]
fn rename_path(project: String, path: String, name: String) -> Result<String, String> {
    let from = PathBuf::from(&path);
    inside(Path::new(&project), &from)?;
    let mut name = clean_name(&name)?;
    if from.is_file() && Path::new(&name).extension().is_none() {
        if let Some(ext) = from.extension() {
            name = format!("{name}.{}", ext.to_string_lossy());
        }
    }
    let to = from.with_file_name(name);
    if to.exists() {
        return Err("A file or folder with that name already exists.".into());
    }
    fs::rename(&from, &to).map_err(|e| e.to_string())?;
    Ok(to.to_string_lossy().into_owned())
}

/// Moves a file or folder into another folder of the project; returns the new path.
#[tauri::command]
fn move_path(project: String, path: String, into: String) -> Result<String, String> {
    let from = PathBuf::from(&path);
    let into = PathBuf::from(&into);
    inside(Path::new(&project), &from)?;
    if into != Path::new(&project) {
        inside(Path::new(&project), &into)?;
    }
    if into.starts_with(&from) {
        return Err("A folder can't be moved into itself.".into());
    }
    let to = into.join(from.file_name().ok_or("Bad path.")?);
    if to == from {
        return Ok(path);
    }
    if to.exists() {
        return Err("Something with that name is already there.".into());
    }
    fs::rename(&from, &to).map_err(|e| e.to_string())?;
    Ok(to.to_string_lossy().into_owned())
}

/// Sends a file or folder to the Recycle Bin, so it can be restored.
#[tauri::command]
fn trash_path(project: String, path: String) -> Result<(), String> {
    let p = PathBuf::from(&path);
    inside(Path::new(&project), &p)?;
    let kind = if p.is_dir() { "DeleteDirectory" } else { "DeleteFile" };
    let script = format!(
        "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::{kind}($env:MP_TRASH, 'OnlyErrorDialogs', 'SendToRecycleBin')"
    );
    let mut c = std::process::Command::new("powershell.exe");
    // The path travels in an environment variable, never inside the script text.
    c.args(["-NoProfile", "-NonInteractive", "-Command", &script]).env("MP_TRASH", &p);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x0800_0000);
    }
    let out = c.output().map_err(|e| e.to_string())?;
    if out.status.success() && !p.exists() {
        Ok(())
    } else {
        Err(format!("Could not move it to the Recycle Bin. {}", String::from_utf8_lossy(&out.stderr).trim()))
    }
}

/// Opens (creating if needed) a project folder. Without a path, uses
/// Documents/ManimPro/My first video.
#[tauri::command]
fn open_project(app: AppHandle, path: Option<String>) -> Result<ProjectInfo, String> {
    let dir = match path {
        Some(p) => PathBuf::from(p),
        None => projects::projects_root()?.join("My first video"),
    };
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let has_py = fs::read_dir(&dir)
        .map_err(|e| e.to_string())?
        .filter_map(Result::ok)
        .any(|e| e.path().extension().is_some_and(|x| x == "py"));
    if !has_py {
        fs::write(dir.join("scenes.py"), SAMPLE_SCENE).map_err(|e| e.to_string())?;
    }
    projects::touch_recent(&app, &dir.to_string_lossy());
    scan_project(&dir)
}

#[tauri::command]
fn read_text(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_text(path: String, contents: String) -> Result<(), String> {
    if let Some(parent) = Path::new(&path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    fs::write(path, contents).map_err(|e| e.to_string())
}

#[tauri::command]
fn create_scene_file(dir: String, name: String) -> Result<String, String> {
    let stem: String = name
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '_' { c } else { '_' })
        .collect();
    let stem = if stem.is_empty() { "scene".to_string() } else { stem.to_lowercase() };
    let path = Path::new(&dir).join(format!("{stem}.py"));
    if path.exists() {
        return Err(format!("{stem}.py already exists."));
    }
    let class = stem
        .split('_')
        .filter(|s| !s.is_empty())
        .map(|s| s[..1].to_uppercase() + &s[1..])
        .collect::<String>();
    let body = format!(
        "from manim import *\n\n\nclass {class}(Scene):\n    def construct(self):\n        title = Text(\"{class}\")\n        self.play(Write(title))\n        self.wait()\n"
    );
    fs::write(&path, body).map_err(|e| e.to_string())?;
    Ok(path.to_string_lossy().into_owned())
}

#[tauri::command]
async fn worker_call(
    app: AppHandle,
    worker: State<'_, Worker>,
    method: String,
    params: Value,
) -> Result<Value, Value> {
    worker.call(&app, &method, params).await
}

/// Cancels whatever is rendering by restarting the worker.
#[tauri::command]
fn worker_restart(app: AppHandle, worker: State<'_, Worker>) -> Result<(), String> {
    worker.stop();
    worker.start(&app)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(Worker::new())
        .manage(agents::Agents::new())
        .manage(bridge::Bridge::new())
        .setup(|app| {
            bridge::Bridge::start(app.handle())?;
            // Warm up manim in the background so the first preview is fast.
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let _ = handle.state::<Worker>().start(&handle);
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                window.app_handle().state::<Worker>().stop();
            }
        })
        .invoke_handler(tauri::generate_handler![
            open_project,
            read_text,
            write_text,
            create_scene_file,
            create_folder,
            rename_path,
            move_path,
            trash_path,
            worker_call,
            worker_restart,
            projects::list_projects,
            projects::create_project,
            projects::import_media,
            projects::save_attachment,
            projects::save_attachment_data,
            projects::rename_project,
            agents::agent_status,
            agents::agent_models,
            agents::agent_login,
            agents::agent_run,
            agents::agent_cancel,
            bridge::bridge_reply,
            latex::latex_status,
            latex::latex_install,
            catalog::models_catalog,
            catalog::set_api_key,
            catalog::clear_api_key,
            catalog::api_key_hint,
            voice::voice_account,
            voice::voice_list,
            voice::voice_generate
        ])
        .run(tauri::generate_context!())
        .expect("error while running ManimPro");
}
