//! Project folders, recents, templates and imported media.

use serde::Serialize;
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;
use tauri::{AppHandle, Manager};

pub fn projects_root() -> Result<PathBuf, String> {
    Ok(dirs::document_dir()
        .or_else(dirs::home_dir)
        .ok_or("Could not find your Documents folder.")?
        .join("ManimPro"))
}

fn recent_file(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app.path().app_config_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join("recent.json"))
}

fn read_recent(app: &AppHandle) -> Vec<String> {
    recent_file(app)
        .ok()
        .and_then(|p| fs::read_to_string(p).ok())
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

pub fn touch_recent(app: &AppHandle, dir: &str) {
    let mut list = read_recent(app);
    list.retain(|d| !d.eq_ignore_ascii_case(dir));
    list.insert(0, dir.to_string());
    list.truncate(12);
    if let Ok(p) = recent_file(app) {
        let _ = fs::write(p, serde_json::to_string_pretty(&list).unwrap_or_default());
    }
}

#[derive(Serialize)]
pub struct ProjectSummary {
    name: String,
    dir: String,
    modified: u64,
    scenes: usize,
    clips: usize,
    thumbnail: Option<String>,
}

fn summarize(dir: &Path) -> Option<ProjectSummary> {
    if !dir.is_dir() {
        return None;
    }
    let mut modified = 0u64;
    let mut scenes = 0usize;
    for e in fs::read_dir(dir).ok()?.flatten() {
        let p = e.path();
        if p.extension().is_some_and(|x| x == "py") {
            scenes += fs::read_to_string(&p)
                .map(|s| s.lines().filter(|l| l.starts_with("class ") && l.contains("Scene")).count())
                .unwrap_or(0);
        }
        if let Ok(m) = e.metadata().and_then(|m| m.modified()) {
            modified = modified.max(m.duration_since(UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0));
        }
    }
    let clips = fs::read_to_string(dir.join("project.json"))
        .ok()
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
        .and_then(|v| v.get("clips").and_then(Value::as_array).map(Vec::len))
        .unwrap_or(0);
    let thumb = dir.join(".manimpro").join("thumb.jpg");
    Some(ProjectSummary {
        name: dir.file_name()?.to_string_lossy().into_owned(),
        dir: dir.to_string_lossy().into_owned(),
        modified,
        scenes,
        clips,
        thumbnail: thumb.is_file().then(|| thumb.to_string_lossy().into_owned()),
    })
}

#[derive(Serialize)]
pub struct ProjectLists {
    root: String,
    recent: Vec<ProjectSummary>,
    all: Vec<ProjectSummary>,
}

#[tauri::command]
pub fn list_projects(app: AppHandle) -> Result<ProjectLists, String> {
    let root = projects_root()?;
    fs::create_dir_all(&root).map_err(|e| e.to_string())?;
    let recent: Vec<ProjectSummary> = read_recent(&app).iter().filter_map(|d| summarize(Path::new(d))).collect();
    let mut all: Vec<ProjectSummary> = fs::read_dir(&root)
        .map_err(|e| e.to_string())?
        .flatten()
        .filter_map(|e| summarize(&e.path()))
        .collect();
    all.sort_by(|a, b| b.modified.cmp(&a.modified));
    Ok(ProjectLists { root: root.to_string_lossy().into_owned(), recent, all })
}

fn unique_dir(root: &Path, name: &str) -> PathBuf {
    let clean: String = name
        .chars()
        .map(|c| if "<>:\"/\\|?*".contains(c) || c.is_control() { ' ' } else { c })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    let base = if clean.is_empty() { "Untitled".to_string() } else { clean.chars().take(48).collect() };
    let mut dir = root.join(&base);
    let mut n = 2;
    while dir.exists() {
        dir = root.join(format!("{base} {n}"));
        n += 1;
    }
    dir
}

fn templates_dir(app: &AppHandle) -> PathBuf {
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("templates");
    if cfg!(debug_assertions) && dev.is_dir() {
        return dev;
    }
    app.path().resource_dir().unwrap_or_default().join("templates")
}

/// Creates a project folder, optionally filled from a template.
#[tauri::command]
pub fn create_project(app: AppHandle, name: String, template: Option<String>) -> Result<String, String> {
    let root = projects_root()?;
    let dir = unique_dir(&root, &name);
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let src = templates_dir(&app).join(template.as_deref().unwrap_or("blank"));
    if !src.is_dir() {
        return Err(format!("Template {} is missing.", template.unwrap_or_default()));
    }
    for e in fs::read_dir(&src).map_err(|e| e.to_string())?.flatten() {
        let p = e.path();
        if p.extension().is_some_and(|x| x == "py") {
            fs::copy(&p, dir.join(e.file_name())).map_err(|e| e.to_string())?;
        }
    }
    let path = dir.to_string_lossy().into_owned();
    touch_recent(&app, &path);
    Ok(path)
}

/// Copies an audio or video file into the project's assets folder.
#[tauri::command]
pub fn import_media(project_dir: String, source: String) -> Result<String, String> {
    let src = PathBuf::from(&source);
    let assets = Path::new(&project_dir).join("assets");
    fs::create_dir_all(&assets).map_err(|e| e.to_string())?;
    if src.parent() == Some(assets.as_path()) {
        return Ok(source);
    }
    let name = src.file_name().ok_or("Not a file.")?.to_string_lossy().into_owned();
    let (stem, ext) = match name.rsplit_once('.') {
        Some((s, e)) => (s.to_string(), format!(".{e}")),
        None => (name.clone(), String::new()),
    };
    let mut dest = assets.join(&name);
    let mut n = 2;
    while dest.exists() {
        dest = assets.join(format!("{stem} {n}{ext}"));
        n += 1;
    }
    fs::copy(&src, &dest).map_err(|e| e.to_string())?;
    Ok(dest.to_string_lossy().into_owned())
}

#[tauri::command]
pub fn rename_project(app: AppHandle, dir: String, name: String) -> Result<String, String> {
    let old = PathBuf::from(&dir);
    let parent = old.parent().ok_or("Bad project path.")?;
    let new = unique_dir(parent, &name);
    fs::rename(&old, &new).map_err(|e| e.to_string())?;
    let path = new.to_string_lossy().into_owned();
    let mut list = read_recent(&app);
    for d in list.iter_mut() {
        if d.eq_ignore_ascii_case(&dir) {
            *d = path.clone();
        }
    }
    if let Ok(p) = recent_file(&app) {
        let _ = fs::write(p, serde_json::to_string_pretty(&list).unwrap_or_default());
    }
    Ok(path)
}

// ------------------------------------------------------------ attachments

fn attachments_dir(project_dir: &str) -> Result<PathBuf, String> {
    let dir = Path::new(project_dir).join(".manimpro").join("attachments");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir)
}

fn unique_file(dir: &Path, name: &str) -> PathBuf {
    let safe: String = name
        .chars()
        .map(|c| if r#"<>:"/\|?*"#.contains(c) || c.is_control() { '_' } else { c })
        .collect();
    let safe = if safe.trim().is_empty() { "attachment".to_string() } else { safe };
    let (stem, ext) = match safe.rsplit_once('.') {
        Some((s, e)) => (s.to_string(), format!(".{e}")),
        None => (safe.clone(), String::new()),
    };
    let mut p = dir.join(&safe);
    let mut n = 2;
    while p.exists() {
        p = dir.join(format!("{stem} {n}{ext}"));
        n += 1;
    }
    p
}

/// Copies a file the user attached into the project, where assistants can read it.
#[tauri::command]
pub fn save_attachment(project_dir: String, source: String) -> Result<String, String> {
    let src = PathBuf::from(&source);
    let meta = fs::metadata(&src).map_err(|e| e.to_string())?;
    if meta.len() > 25 * 1024 * 1024 {
        return Err("Attachments can be up to 25 MB.".into());
    }
    let name = src.file_name().ok_or("Not a file.")?.to_string_lossy().into_owned();
    let dest = unique_file(&attachments_dir(&project_dir)?, &name);
    fs::copy(&src, &dest).map_err(|e| e.to_string())?;
    Ok(dest.to_string_lossy().into_owned())
}

/// Saves pasted or dropped data (base64) as an attachment file.
#[tauri::command]
pub fn save_attachment_data(project_dir: String, name: String, data: String) -> Result<String, String> {
    use base64::Engine;
    let bytes = base64::engine::general_purpose::STANDARD.decode(data.trim()).map_err(|e| e.to_string())?;
    if bytes.len() > 25 * 1024 * 1024 {
        return Err("Attachments can be up to 25 MB.".into());
    }
    let dest = unique_file(&attachments_dir(&project_dir)?, &name);
    fs::write(&dest, bytes).map_err(|e| e.to_string())?;
    Ok(dest.to_string_lossy().into_owned())
}
