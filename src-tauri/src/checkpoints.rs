//! Checkpoints: a copy of a project's own files taken before an assistant runs,
//! so its edits can be listed and undone.
//!
//! Stored in <project>/.manimpro/checkpoints/<id>/ as `files/` plus `manifest.json`.
//! Renders, audio and other big files are left out (they are rebuilt or kept as they are).

use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

const MAX_FILE: u64 = 5 * 1024 * 1024;
const KEEP: usize = 30;

fn store(project: &Path) -> PathBuf {
    project.join(".manimpro").join("checkpoints")
}

fn skipped_dir(name: &str) -> bool {
    let n = name.to_ascii_lowercase();
    name.starts_with('.') || ["__pycache__", "media", "node_modules", "venv", "env", "build", "dist"].contains(&n.as_str())
}

/// The project's own files (relative paths with forward slashes), small enough to snapshot.
fn tracked(project: &Path) -> Vec<String> {
    fn walk(root: &Path, dir: &Path, depth: usize, out: &mut Vec<String>) {
        if depth > 6 || out.len() > 3000 {
            return;
        }
        let Ok(entries) = fs::read_dir(dir) else { return };
        for e in entries.flatten() {
            let p = e.path();
            let name = e.file_name().to_string_lossy().into_owned();
            if p.is_dir() {
                // Generated voiceovers and music live in assets/audio: big, and kept on undo.
                if !skipped_dir(&name) && !(depth == 1 && name.eq_ignore_ascii_case("audio") && dir.ends_with("assets")) {
                    walk(root, &p, depth + 1, out);
                }
            } else if e.metadata().map(|m| m.len() <= MAX_FILE).unwrap_or(false) {
                if let Ok(rel) = p.strip_prefix(root) {
                    out.push(rel.to_string_lossy().replace('\\', "/"));
                }
            }
        }
    }
    let mut out = Vec::new();
    walk(project, project, 0, &mut out);
    out.sort();
    out
}

#[derive(Serialize, serde::Deserialize)]
struct Manifest {
    created: u64,
    files: Vec<String>,
}

#[derive(Serialize)]
pub struct Change {
    path: String,
    /// "added" | "modified" | "deleted"
    status: &'static str,
}

fn read_manifest(dir: &Path) -> Result<Manifest, String> {
    let text = fs::read_to_string(dir.join("manifest.json")).map_err(|_| "That checkpoint no longer exists.".to_string())?;
    serde_json::from_str(&text).map_err(|e| e.to_string())
}

fn valid_id(id: &str) -> Result<(), String> {
    if id.is_empty() || !id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-') {
        return Err("Bad checkpoint id.".into());
    }
    Ok(())
}

#[tauri::command]
pub fn checkpoint_create(project: String) -> Result<String, String> {
    let root = PathBuf::from(&project);
    let now = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0);
    let id = format!("cp-{now}");
    let dir = store(&root).join(&id);
    let files = tracked(&root);
    for rel in &files {
        let dest = dir.join("files").join(rel);
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        fs::copy(root.join(rel), &dest).map_err(|e| format!("Could not save {rel}: {e}"))?;
    }
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let manifest = Manifest { created: now, files };
    fs::write(dir.join("manifest.json"), serde_json::to_string(&manifest).unwrap_or_default()).map_err(|e| e.to_string())?;

    // Keep the newest few.
    if let Ok(entries) = fs::read_dir(store(&root)) {
        let mut all: Vec<PathBuf> = entries.flatten().map(|e| e.path()).filter(|p| p.is_dir()).collect();
        all.sort();
        let extra = all.len().saturating_sub(KEEP);
        for old in all.into_iter().take(extra) {
            let _ = fs::remove_dir_all(old);
        }
    }
    Ok(id)
}

fn diff(root: &Path, dir: &Path, manifest: &Manifest) -> Vec<Change> {
    let now = tracked(root);
    let mut out = Vec::new();
    for rel in &manifest.files {
        let cur = root.join(rel);
        if !cur.exists() {
            out.push(Change { path: rel.clone(), status: "deleted" });
        } else if fs::read(&cur).ok() != fs::read(dir.join("files").join(rel)).ok() {
            out.push(Change { path: rel.clone(), status: "modified" });
        }
    }
    for rel in now {
        if !manifest.files.contains(&rel) {
            out.push(Change { path: rel, status: "added" });
        }
    }
    out
}

/// What changed in the project since the checkpoint (project.json, the timeline, included).
#[tauri::command]
pub fn checkpoint_changes(project: String, id: String) -> Result<Vec<Change>, String> {
    valid_id(&id)?;
    let root = PathBuf::from(&project);
    let dir = store(&root).join(&id);
    let m = read_manifest(&dir)?;
    Ok(diff(&root, &dir, &m))
}

/// Puts the project's files back as they were. Files created since are moved into the
/// checkpoint's `removed/` folder rather than deleted.
#[tauri::command]
pub fn checkpoint_restore(project: String, id: String) -> Result<Vec<Change>, String> {
    valid_id(&id)?;
    let root = PathBuf::from(&project);
    let dir = store(&root).join(&id);
    let m = read_manifest(&dir)?;
    let changes = diff(&root, &dir, &m);
    for c in &changes {
        let cur = root.join(&c.path);
        match c.status {
            "added" => {
                let keep = dir.join("removed").join(&c.path);
                if let Some(parent) = keep.parent() {
                    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
                }
                fs::rename(&cur, &keep).or_else(|_| fs::copy(&cur, &keep).and_then(|_| fs::remove_file(&cur)))
                    .map_err(|e| format!("Could not move {}: {e}", c.path))?;
            }
            _ => {
                if let Some(parent) = cur.parent() {
                    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
                }
                fs::copy(dir.join("files").join(&c.path), &cur).map_err(|e| format!("Could not restore {}: {e}", c.path))?;
            }
        }
    }
    Ok(changes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_diff_restore() {
        let root = std::env::temp_dir().join(format!("mp-cp-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("data")).unwrap();
        fs::create_dir_all(root.join("assets").join("audio")).unwrap();
        fs::write(root.join("scenes.py"), "a").unwrap();
        fs::write(root.join("old.py"), "keep me").unwrap();
        fs::write(root.join("data").join("x.csv"), "1,2").unwrap();
        fs::write(root.join("assets").join("audio").join("v.mp3"), "audio").unwrap();
        let p = root.to_string_lossy().into_owned();

        let id = checkpoint_create(p.clone()).unwrap();
        fs::write(root.join("scenes.py"), "b").unwrap();
        fs::remove_file(root.join("old.py")).unwrap();
        fs::write(root.join("new.py"), "c").unwrap();
        fs::write(root.join("assets").join("audio").join("v2.mp3"), "more").unwrap();

        let mut ch: Vec<(String, &str)> = checkpoint_changes(p.clone(), id.clone()).unwrap().into_iter().map(|c| (c.path, c.status)).collect();
        ch.sort();
        assert_eq!(ch, vec![("new.py".into(), "added"), ("old.py".into(), "deleted"), ("scenes.py".into(), "modified")]);

        checkpoint_restore(p.clone(), id.clone()).unwrap();
        assert_eq!(fs::read_to_string(root.join("scenes.py")).unwrap(), "a");
        assert_eq!(fs::read_to_string(root.join("old.py")).unwrap(), "keep me");
        assert!(!root.join("new.py").exists());
        assert!(store(&root).join(&id).join("removed").join("new.py").exists());
        assert!(root.join("assets").join("audio").join("v2.mp3").exists(), "audio is left alone");
        assert!(checkpoint_changes(p, id).unwrap().is_empty());
        let _ = fs::remove_dir_all(&root);
    }
}
