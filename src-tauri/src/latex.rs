//! One-click LaTeX (TinyTeX) for MathTex / Tex.
//!
//! Downloads the official TinyTeX-1 bundle (a 7-Zip self-extractor), extracts it
//! into the app's local data folder (no admin, no system PATH changes), then
//! installs the extra packages Manim needs with tlmgr.

use serde::Serialize;
use serde_json::json;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{AppHandle, Emitter, Manager};

const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const BUNDLE_URL: &str = "https://github.com/rstudio/tinytex-releases/releases/download/daily/TinyTeX-1-windows.exe";
/// Packages Manim Community uses on top of a minimal TeX Live.
const PACKAGES: &[&str] = &[
    "amsmath", "babel-english", "cbfonts-fd", "cm-super", "count1to", "doublestroke", "dvisvgm", "everysel",
    "fontspec", "frcursive", "fundus-calligra", "gnu-freefont", "jknapltx", "latex-bin", "mathastext",
    "microtype", "multitoc", "physics", "preview", "prelim2e", "ragged2e", "relsize", "rsfs", "setspace",
    "standalone", "tipa", "wasy", "wasysym", "xcolor", "xetex", "xkeyval",
];

static INSTALLING: AtomicBool = AtomicBool::new(false);

fn install_root(app: &AppHandle) -> PathBuf {
    app.path().app_local_data_dir().unwrap_or_else(|_| std::env::temp_dir()).join("TinyTeX")
}

/// LaTeX shipped inside the app (scripts/setup-latex.ps1 puts it in runtime/TinyTeX).
fn bundled_root(app: &AppHandle) -> PathBuf {
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("runtime").join("TinyTeX");
    if cfg!(debug_assertions) && dev.is_dir() {
        return dev;
    }
    app.path().resource_dir().unwrap_or_default().join("runtime").join("TinyTeX")
}

/// The bin folder holding latex.exe and dvisvgm.exe: the bundled copy first,
/// then one the user installed later from inside the app.
pub fn tex_bin(app: &AppHandle) -> Option<PathBuf> {
    [bundled_root(app), install_root(app)].into_iter().find_map(|root| {
        ["windows", "win32", "win64"]
            .iter()
            .map(|d| root.join("bin").join(d))
            .find(|d| d.join("latex.exe").is_file() || d.join("pdflatex.exe").is_file())
    })
}

pub fn has_dvisvgm(bin: &Path) -> bool {
    bin.join("dvisvgm.exe").is_file()
}

#[derive(Serialize)]
pub struct LatexStatus {
    installed: bool,
    complete: bool,
    installing: bool,
    path: Option<String>,
}

#[tauri::command]
pub fn latex_status(app: AppHandle) -> LatexStatus {
    let bin = tex_bin(&app);
    LatexStatus {
        installed: bin.is_some(),
        complete: bin.as_deref().is_some_and(has_dvisvgm),
        installing: INSTALLING.load(Ordering::SeqCst),
        path: bin.map(|b| b.to_string_lossy().into_owned()),
    }
}

fn hidden(program: impl AsRef<std::ffi::OsStr>) -> Command {
    let mut c = Command::new(program);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(CREATE_NO_WINDOW);
    }
    c
}

fn progress(app: &AppHandle, stage: &str, detail: &str, fraction: Option<f64>) {
    let _ = app.emit("latex-progress", json!({ "stage": stage, "detail": detail, "fraction": fraction }));
}

fn run_logged(app: &AppHandle, stage: &str, mut cmd: Command) -> Result<(), String> {
    let mut child = cmd
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("{stage}: {e}"))?;
    let err = child.stderr.take().map(|e| {
        std::thread::spawn(move || BufReader::new(e).lines().map_while(Result::ok).collect::<Vec<_>>())
    });
    if let Some(out) = child.stdout.take() {
        for line in BufReader::new(out).lines().map_while(Result::ok) {
            let line = line.trim();
            if !line.is_empty() {
                progress(app, stage, line, None);
            }
        }
    }
    let status = child.wait().map_err(|e| e.to_string())?;
    if status.success() {
        Ok(())
    } else {
        let tail = err.and_then(|h| h.join().ok()).unwrap_or_default();
        Err(format!("{stage} failed:\n{}", tail.iter().rev().take(12).rev().cloned().collect::<Vec<_>>().join("\n")))
    }
}

/// Installs TinyTeX + Manim's packages. Emits `latex-progress` events; returns when done.
#[tauri::command]
pub async fn latex_install(app: AppHandle) -> Result<(), String> {
    if INSTALLING.swap(true, Ordering::SeqCst) {
        return Err("LaTeX is already being installed.".into());
    }
    let result = tauri::async_runtime::spawn_blocking({
        let app = app.clone();
        move || install_blocking(&app)
    })
    .await
    .map_err(|e| e.to_string())
    .and_then(|r| r);
    INSTALLING.store(false, Ordering::SeqCst);
    // The render worker reads PATH at start: restart it so it sees LaTeX.
    if result.is_ok() {
        let w = app.state::<crate::worker::Worker>();
        w.stop();
        let _ = w.start(&app);
    }
    result
}

fn install_blocking(app: &AppHandle) -> Result<(), String> {
    let root = install_root(app);
    let parent = root.parent().ok_or("bad install folder")?.to_path_buf();
    std::fs::create_dir_all(&parent).map_err(|e| e.to_string())?;

    if tex_bin(app).is_none() {
        let bundle = parent.join("TinyTeX-1-windows.exe");
        if !bundle.is_file() {
            progress(app, "Downloading TinyTeX", "about 74 MB", None);
            let mut dl = hidden("curl.exe");
            dl.args(["-L", "--fail", "--retry", "5", "-C", "-", "-o"]).arg(&bundle).arg(BUNDLE_URL);
            run_logged(app, "Downloading TinyTeX", dl)?;
        }
        progress(app, "Unpacking", "", None);
        let mut unpack = hidden(&bundle);
        unpack.arg("-y").arg(format!("-o{}", parent.display()));
        run_logged(app, "Unpacking TinyTeX", unpack)?;
        let _ = std::fs::remove_file(&bundle);
    }
    let bin = tex_bin(app).ok_or("TinyTeX unpacked, but latex.exe was not found.")?;

    let tlmgr = bin.join("tlmgr.bat");
    let total = PACKAGES.len() as f64;
    // Install in small batches so progress moves and one bad package is easy to spot.
    for (i, chunk) in PACKAGES.chunks(6).enumerate() {
        let done = (i * 6) as f64;
        progress(app, "Installing LaTeX packages", &chunk.join(", "), Some(done / total));
        let mut c = hidden("cmd.exe");
        c.arg("/C").arg(&tlmgr).arg("install").args(chunk);
        c.env("PATH", prepend_path(&bin));
        run_logged(app, "Installing LaTeX packages", c)?;
    }
    progress(app, "Finishing", "", Some(1.0));
    if !has_dvisvgm(&bin) {
        return Err("LaTeX installed, but dvisvgm is missing; Manim needs it to draw formulas.".into());
    }
    Ok(())
}

pub fn prepend_path(dir: &Path) -> std::ffi::OsString {
    let mut parts = vec![dir.to_path_buf()];
    if let Some(p) = std::env::var_os("PATH") {
        parts.extend(std::env::split_paths(&p));
    }
    std::env::join_paths(parts).unwrap_or_default()
}
