//! Project folders, recents, templates and imported media.

use serde::Serialize;
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;
use tauri::{AppHandle, Manager};

fn default_root() -> Result<PathBuf, String> {
    Ok(dirs::document_dir()
        .or_else(dirs::home_dir)
        .ok_or("Could not find your Documents folder.")?
        .join("ManimPro"))
}

/// Where the user chose to keep projects (Settings), stored outside localStorage so
/// the Rust side can read it without the UI.
fn root_setting_file() -> Option<PathBuf> {
    Some(dirs::config_dir()?.join("dev.manimpro.app").join("projects-root.txt"))
}

pub fn projects_root() -> Result<PathBuf, String> {
    if let Some(chosen) = root_setting_file()
        .and_then(|f| fs::read_to_string(f).ok())
        .map(|s| PathBuf::from(s.trim()))
        .filter(|p| !p.as_os_str().is_empty() && p.is_dir())
    {
        return Ok(chosen);
    }
    default_root()
}

#[derive(Serialize)]
pub struct RootInfo {
    path: String,
    default: String,
    /// A folder outside OneDrive the UI can suggest.
    local: String,
    onedrive: bool,
}

fn in_onedrive(p: &Path) -> bool {
    let s = p.to_string_lossy().to_lowercase();
    s.contains("\\onedrive") || std::env::var("OneDrive").is_ok_and(|o| !o.is_empty() && s.starts_with(&o.to_lowercase()))
}

#[tauri::command]
pub fn get_projects_root() -> Result<RootInfo, String> {
    let path = projects_root()?;
    let local = dirs::home_dir().ok_or("No home folder.")?.join("ManimPro");
    Ok(RootInfo {
        onedrive: in_onedrive(&path),
        path: path.to_string_lossy().into_owned(),
        default: default_root()?.to_string_lossy().into_owned(),
        local: local.to_string_lossy().into_owned(),
    })
}

/// Sets (or with None, resets) the folder new projects are created in.
#[tauri::command]
pub fn set_projects_root(path: Option<String>) -> Result<RootInfo, String> {
    let file = root_setting_file().ok_or("No settings folder.")?;
    match path {
        Some(p) => {
            let dir = PathBuf::from(p.trim());
            fs::create_dir_all(&dir).map_err(|e| format!("Could not use that folder: {e}"))?;
            if let Some(parent) = file.parent() {
                fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            }
            fs::write(&file, dir.to_string_lossy().as_bytes()).map_err(|e| e.to_string())?;
        }
        None => {
            let _ = fs::remove_file(&file);
        }
    }
    get_projects_root()
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

fn write_recent(app: &AppHandle, list: &[String]) {
    if let Ok(p) = recent_file(app) {
        let _ = fs::write(p, serde_json::to_string_pretty(list).unwrap_or_default());
    }
}

/// Takes a project off the Recent list (the folder stays).
#[tauri::command]
pub fn forget_recent(app: AppHandle, dir: String) {
    let mut list = read_recent(&app);
    list.retain(|d| !d.eq_ignore_ascii_case(&dir));
    write_recent(&app, &list);
}

/// Moves a project folder to the Recycle Bin. Only folders that are ManimPro
/// projects (under the projects folder, or on the Recent list) qualify.
#[tauri::command]
pub fn delete_project(app: AppHandle, dir: String) -> Result<(), String> {
    let path = PathBuf::from(&dir);
    let root = projects_root()?;
    let canon = |p: &Path| fs::canonicalize(p).map_err(|e| e.to_string());
    let target = canon(&path)?;
    let under_root = canon(&root).map(|r| target.starts_with(&r) && target != r).unwrap_or(false);
    let known = read_recent(&app).iter().any(|d| d.eq_ignore_ascii_case(&dir));
    if !(under_root || known) || target.parent().is_none() || !target.is_dir() {
        return Err("Only ManimPro project folders can be deleted here.".into());
    }
    crate::recycle(&path)?;
    forget_recent(app, dir);
    Ok(())
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
    /** A rendered video to preview on hover: the first clip's scene, else the latest render. */
    preview: Option<String>,
}

fn preview_video(project: &Value) -> Option<String> {
    let renders = project.get("renders")?.as_object()?;
    let video = |key: &str| {
        renders
            .get(key)
            .and_then(|r| r.get("video"))
            .and_then(Value::as_str)
            .filter(|v| Path::new(v).is_file())
            .map(str::to_string)
    };
    let mut clips: Vec<&Value> = project.get("clips").and_then(Value::as_array).map(|c| c.iter().collect()).unwrap_or_default();
    clips.sort_by(|a, b| {
        let s = |c: &Value| c.get("start").and_then(Value::as_f64).unwrap_or(0.0);
        s(a).partial_cmp(&s(b)).unwrap_or(std::cmp::Ordering::Equal)
    });
    for c in clips {
        if let (Some(f), Some(s)) = (c.get("file").and_then(Value::as_str), c.get("scene").and_then(Value::as_str)) {
            if let Some(v) = video(&format!("{f}::{s}")) {
                return Some(v);
            }
        }
    }
    let mut latest: Vec<(&String, f64)> = renders
        .iter()
        .map(|(k, r)| (k, r.get("version").and_then(Value::as_f64).unwrap_or(0.0)))
        .collect();
    latest.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    latest.into_iter().find_map(|(k, _)| video(k))
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
    let project = fs::read_to_string(dir.join("project.json"))
        .ok()
        .and_then(|s| serde_json::from_str::<Value>(&s).ok());
    let clips = project
        .as_ref()
        .and_then(|v| v.get("clips").and_then(Value::as_array).map(Vec::len))
        .unwrap_or(0);
    let preview = project.as_ref().and_then(preview_video);
    let thumb = dir.join(".manimpro").join("thumb.jpg");
    Some(ProjectSummary {
        name: dir.file_name()?.to_string_lossy().into_owned(),
        dir: dir.to_string_lossy().into_owned(),
        modified,
        scenes,
        clips,
        thumbnail: thumb.is_file().then(|| thumb.to_string_lossy().into_owned()),
        preview,
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
    // One of the user's own templates: copy everything it holds.
    if let Some(slug) = template.as_deref().and_then(|t| t.strip_prefix("user:")) {
        let src = user_templates_dir()?.join(slug);
        if !src.is_dir() {
            return Err("That template no longer exists.".into());
        }
        copy_tree(&src, &dir, &|rel| rel != "template.json" && rel != "thumb.jpg")?;
        let path = dir.to_string_lossy().into_owned();
        touch_recent(&app, &path);
        return Ok(path);
    }
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

pub fn unique_file(dir: &Path, name: &str) -> PathBuf {
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


// ------------------------------------------------------------ the user's own templates

fn user_templates_dir() -> Result<PathBuf, String> {
    Ok(dirs::config_dir().ok_or("No settings folder.")?.join("dev.manimpro.app").join("templates"))
}

/// Copies a folder tree, skipping renders, caches and anything `keep` rejects (relative, forward slashes).
fn copy_tree(src: &Path, dest: &Path, keep: &dyn Fn(&str) -> bool) -> Result<(), String> {
    fn walk(root: &Path, dir: &Path, dest: &Path, keep: &dyn Fn(&str) -> bool) -> Result<(), String> {
        for e in fs::read_dir(dir).map_err(|e| e.to_string())?.flatten() {
            let p = e.path();
            let rel = p.strip_prefix(root).unwrap_or(&p).to_string_lossy().replace('\\', "/");
            let name = e.file_name().to_string_lossy().to_lowercase();
            if p.is_dir() {
                if [".manimpro", "__pycache__", "media", ".git", "node_modules"].contains(&name.as_str()) {
                    continue;
                }
                walk(root, &p, dest, keep)?;
            } else if keep(&rel) {
                let out = dest.join(&rel);
                if let Some(parent) = out.parent() {
                    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
                }
                fs::copy(&p, &out).map_err(|e| e.to_string())?;
            }
        }
        Ok(())
    }
    walk(src, src, dest, keep)
}

#[derive(Serialize)]
pub struct UserTemplate {
    id: String,
    title: String,
    description: String,
    thumbnail: Option<String>,
    scenes: Vec<String>,
    created: u64,
}

/// Saves a project (code, data, assets, timeline) as a template. Returns its id ("user:slug").
#[tauri::command]
pub fn save_user_template(project: String, name: String, description: Option<String>) -> Result<String, String> {
    let src = PathBuf::from(&project);
    let slug: String = name
        .trim()
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c.to_ascii_lowercase() } else { '-' })
        .collect::<String>()
        .split('-')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("-");
    if slug.is_empty() {
        return Err("Give the template a name.".into());
    }
    let dest = user_templates_dir()?.join(&slug);
    if dest.exists() {
        fs::remove_dir_all(&dest).map_err(|e| e.to_string())?;
    }
    fs::create_dir_all(&dest).map_err(|e| e.to_string())?;
    copy_tree(&src, &dest, &|_| true)?;
    let thumb = src.join(".manimpro").join("thumb.jpg");
    if thumb.is_file() {
        let _ = fs::copy(&thumb, dest.join("thumb.jpg"));
    }
    let now = std::time::SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0);
    let meta = serde_json::json!({ "title": name.trim(), "description": description.unwrap_or_default(), "created": now });
    fs::write(dest.join("template.json"), meta.to_string()).map_err(|e| e.to_string())?;
    Ok(format!("user:{slug}"))
}

#[tauri::command]
pub fn list_user_templates() -> Result<Vec<UserTemplate>, String> {
    let dir = user_templates_dir()?;
    let mut out = Vec::new();
    let Ok(entries) = fs::read_dir(&dir) else { return Ok(out) };
    for e in entries.flatten() {
        let p = e.path();
        let Ok(meta) = fs::read_to_string(p.join("template.json")) else { continue };
        let meta: Value = serde_json::from_str(&meta).unwrap_or_default();
        let mut scenes = Vec::new();
        for f in fs::read_dir(&p).into_iter().flatten().flatten() {
            if f.path().extension().is_some_and(|x| x == "py") {
                for line in fs::read_to_string(f.path()).unwrap_or_default().lines() {
                    if let Some(rest) = line.strip_prefix("class ") {
                        if rest.contains("Scene") || rest.contains("Slide") {
                            scenes.push(rest.split(['(', ':']).next().unwrap_or("").trim().to_string());
                        }
                    }
                }
            }
        }
        let thumb = p.join("thumb.jpg");
        out.push(UserTemplate {
            id: format!("user:{}", e.file_name().to_string_lossy()),
            title: meta.get("title").and_then(Value::as_str).unwrap_or("Template").to_string(),
            description: meta.get("description").and_then(Value::as_str).unwrap_or("").to_string(),
            thumbnail: thumb.is_file().then(|| thumb.to_string_lossy().into_owned()),
            scenes,
            created: meta.get("created").and_then(Value::as_u64).unwrap_or(0),
        });
    }
    out.sort_by(|a, b| b.created.cmp(&a.created));
    Ok(out)
}

#[tauri::command]
pub fn delete_user_template(id: String) -> Result<(), String> {
    let slug = id.strip_prefix("user:").ok_or("Not one of your templates.")?;
    if slug.contains(['/', '\\', '.']) {
        return Err("Bad template id.".into());
    }
    let dir = user_templates_dir()?.join(slug);
    if dir.exists() {
        fs::remove_dir_all(dir).map_err(|e| e.to_string())?;
    }
    Ok(())
}
