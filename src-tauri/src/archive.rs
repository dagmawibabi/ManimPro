//! Projects as .zip files: export one to share or back it up, import one someone sent you.

use serde::Serialize;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use zip::write::SimpleFileOptions;

#[derive(Serialize)]
pub struct ZipInfo {
    path: String,
    files: usize,
    bytes: u64,
}

/// Walks the project, skipping what can be rebuilt: renders (unless asked for), checkpoints,
/// caches and editor junk.
fn collect(root: &Path, include_renders: bool) -> Vec<PathBuf> {
    fn walk(root: &Path, dir: &Path, include_renders: bool, out: &mut Vec<PathBuf>) {
        let Ok(entries) = fs::read_dir(dir) else { return };
        for e in entries.flatten() {
            let p = e.path();
            let name = e.file_name().to_string_lossy().to_lowercase();
            let rel = p.strip_prefix(root).unwrap_or(&p).to_string_lossy().replace('\\', "/").to_lowercase();
            if p.is_dir() {
                let skip = name == "__pycache__"
                    || name == ".git"
                    || name == "node_modules"
                    || rel == ".manimpro/checkpoints"
                    || (rel == ".manimpro/media" && !include_renders)
                    || (rel == "media" && !include_renders); // the manim command line's own output
                if !skip {
                    walk(root, &p, include_renders, out);
                }
            } else {
                out.push(p);
            }
        }
    }
    let mut out = Vec::new();
    walk(root, root, include_renders, &mut out);
    out
}

#[tauri::command]
pub async fn export_project_zip(project: String, dest: String, include_renders: Option<bool>) -> Result<ZipInfo, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let root = PathBuf::from(&project);
        let name = root.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_else(|| "project".into());
        let files = collect(&root, include_renders.unwrap_or(false));
        let tmp = PathBuf::from(format!("{dest}.part"));
        let mut zip = zip::ZipWriter::new(File::create(&tmp).map_err(|e| format!("Could not create the file: {e}"))?);
        let opts = SimpleFileOptions::default().compression_method(zip::CompressionMethod::Deflated).large_file(true);
        let mut bytes = 0u64;
        for f in &files {
            let rel = f.strip_prefix(&root).unwrap_or(f).to_string_lossy().replace('\\', "/");
            // Everything sits inside a folder named after the project, so unzipping stays tidy.
            zip.start_file(format!("{name}/{rel}"), opts).map_err(|e| e.to_string())?;
            let mut src = File::open(f).map_err(|e| format!("Could not read {rel}: {e}"))?;
            bytes += io::copy(&mut src, &mut zip).map_err(|e| e.to_string())?;
        }
        zip.finish().map_err(|e| e.to_string())?.flush().map_err(|e| e.to_string())?;
        fs::rename(&tmp, &dest).map_err(|e| e.to_string())?;
        Ok(ZipInfo { path: dest, files: files.len(), bytes })
    })
    .await
    .map_err(|e| e.to_string())?
}

/// Unpacks a project .zip into the projects folder (a new folder, never over an existing one).
#[tauri::command]
pub async fn import_project_zip(zip_path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let file = File::open(&zip_path).map_err(|e| format!("Could not open the .zip: {e}"))?;
        let mut archive = zip::ZipArchive::new(file).map_err(|e| format!("That isn't a readable .zip file: {e}"))?;
        // One top-level folder in the archive (our own exports): use its contents.
        let mut tops = std::collections::BTreeSet::new();
        for i in 0..archive.len() {
            if let Some(p) = archive.by_index(i).ok().and_then(|f| f.enclosed_name()) {
                if let Some(first) = p.components().next() {
                    tops.insert(first.as_os_str().to_string_lossy().into_owned());
                }
            }
        }
        let strip = if tops.len() == 1 { tops.iter().next().cloned() } else { None };
        let stem = Path::new(&zip_path).file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_else(|| "Imported project".into());
        let base = strip.clone().unwrap_or(stem);
        let root = crate::projects::projects_root()?;
        fs::create_dir_all(&root).map_err(|e| e.to_string())?;
        let mut dest = root.join(&base);
        let mut n = 2;
        while dest.exists() {
            dest = root.join(format!("{base} {n}"));
            n += 1;
        }
        let mut has_py = false;
        for i in 0..archive.len() {
            let mut f = archive.by_index(i).map_err(|e| e.to_string())?;
            // enclosed_name refuses paths that would escape the folder ("../", absolute paths).
            let Some(rel) = f.enclosed_name() else { continue };
            let rel = match &strip {
                Some(s) => match rel.strip_prefix(s) {
                    Ok(r) => r.to_path_buf(),
                    Err(_) => continue,
                },
                None => rel,
            };
            if rel.as_os_str().is_empty() {
                continue;
            }
            let out = dest.join(&rel);
            if f.is_dir() {
                fs::create_dir_all(&out).map_err(|e| e.to_string())?;
                continue;
            }
            has_py |= rel.extension().is_some_and(|x| x == "py");
            if let Some(parent) = out.parent() {
                fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            }
            let mut w = File::create(&out).map_err(|e| e.to_string())?;
            io::copy(&mut f, &mut w).map_err(|e| e.to_string())?;
        }
        if !has_py {
            let _ = fs::remove_dir_all(&dest);
            return Err("That .zip has no Python scene files, so it doesn't look like a ManimPro or Manim project.".into());
        }
        Ok(dest.to_string_lossy().into_owned())
    })
    .await
    .map_err(|e| e.to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip() {
        let base = std::env::temp_dir().join(format!("mp-zip-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&base);
        let proj = base.join("My video");
        fs::create_dir_all(proj.join(".manimpro").join("media")).unwrap();
        fs::create_dir_all(proj.join("data")).unwrap();
        fs::write(proj.join("scenes.py"), "from manim import *").unwrap();
        fs::write(proj.join("data").join("x.csv"), "1,2").unwrap();
        fs::write(proj.join(".manimpro").join("media").join("big.mp4"), "renders").unwrap();
        let dest = base.join("out.zip");
        let info = tauri::async_runtime::block_on(export_project_zip(proj.to_string_lossy().into(), dest.to_string_lossy().into(), None)).unwrap();
        assert_eq!(info.files, 2, "renders are left out by default");
        let mut a = zip::ZipArchive::new(File::open(&dest).unwrap()).unwrap();
        let names: Vec<String> = (0..a.len()).map(|i| a.by_index(i).unwrap().name().to_string()).collect();
        assert!(names.contains(&"My video/scenes.py".to_string()), "{names:?}");
        assert!(names.contains(&"My video/data/x.csv".to_string()));
        let _ = fs::remove_dir_all(&base);
    }
}
