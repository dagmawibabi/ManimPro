//! Runs the user's own coding agents (Claude Code, Codex, OpenCode) as subprocesses.
//!
//! ManimPro never handles the user's AI credentials: each CLI is the vendor's
//! unmodified program, signed in through the vendor's own flow. We only start
//! it in the project folder, hand it a prompt, and stream its JSON events.

use serde::Serialize;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager};

use crate::bridge::Bridge;
use crate::worker::runtime_paths;

const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Provider {
    Claude,
    Codex,
    OpenCode,
    /// API-key providers. ManimPro runs them through OpenCode, which supports both
    /// natively; the key is passed as an environment variable for that run only.
    OpenRouter,
    Vercel,
}

impl Provider {
    pub fn parse(s: &str) -> Result<Self, String> {
        match s {
            "claude" => Ok(Self::Claude),
            "codex" => Ok(Self::Codex),
            "opencode" => Ok(Self::OpenCode),
            "openrouter" => Ok(Self::OpenRouter),
            "vercel" => Ok(Self::Vercel),
            _ => Err(format!("Unknown provider {s}")),
        }
    }
    fn exe_name(self) -> &'static str {
        match self {
            Self::Claude => "claude",
            Self::Codex => "codex",
            Self::OpenCode | Self::OpenRouter | Self::Vercel => "opencode",
        }
    }
    /// For API-key providers: (id used by OpenCode and models.dev, env var for the key, display name).
    fn keyed(self) -> Option<(&'static str, &'static str, &'static str)> {
        match self {
            Self::OpenRouter => Some(("openrouter", "OPENROUTER_API_KEY", "OpenRouter")),
            Self::Vercel => Some(("vercel", "AI_GATEWAY_API_KEY", "Vercel AI Gateway")),
            _ => None,
        }
    }
}

/// A launchable program: the real executable plus any leading args
/// (for npm shims that point at a .js file, that is `node script.js`).
#[derive(Clone)]
struct Launch {
    program: PathBuf,
    prefix: Vec<String>,
}

impl Launch {
    fn command(&self) -> Command {
        let mut c = Command::new(&self.program);
        c.args(&self.prefix);
        scrub_host_session(&mut c);
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            c.creation_flags(CREATE_NO_WINDOW);
        }
        c
    }
}

/// Finds a CLI on PATH. npm installs `.cmd` shims that would force us through
/// cmd.exe (unsafe for free-text prompts), so we read the shim and launch its
/// target directly.
fn resolve(name: &str) -> Option<Launch> {
    let path = std::env::var_os("PATH")?;
    let mut dirs: Vec<PathBuf> = std::env::split_paths(&path).collect();
    // GUI apps can start with a short PATH; add the usual install spots.
    if let Some(home) = dirs::home_dir() {
        dirs.push(home.join(".local").join("bin"));
        dirs.push(home.join("AppData").join("Roaming").join("npm"));
    }
    for dir in dirs {
        let exe = dir.join(format!("{name}.exe"));
        if exe.is_file() {
            return Some(Launch { program: exe, prefix: vec![] });
        }
        let shim = dir.join(format!("{name}.cmd"));
        if shim.is_file() {
            if let Some(l) = resolve_shim(&shim) {
                return Some(l);
            }
        }
    }
    None
}

fn resolve_shim(shim: &Path) -> Option<Launch> {
    let text = std::fs::read_to_string(shim).ok()?;
    let dir = shim.parent()?;
    // npm shims reference their target as "%dp0%\node_modules\...".
    let start = text.rfind("\"%dp0%\\")?;
    let rest = &text[start + 7..];
    let end = rest.find('"')?;
    let target = dir.join(&rest[..end]);
    if !target.exists() {
        return None;
    }
    let is_exe = target.extension().is_some_and(|e| e.eq_ignore_ascii_case("exe"));
    if is_exe {
        return Some(Launch { program: target, prefix: vec![] });
    }
    let node = dir.join("node.exe");
    let node = if node.is_file() { node } else { resolve("node")?.program };
    Some(Launch { program: node, prefix: vec![target.to_string_lossy().into_owned()] })
}

/// If ManimPro itself was started from inside a Claude Code session (e.g. a dev
/// build launched by an agent), that session's variables leak into our children and
/// make the user's CLI think it is a nested, host-authenticated session. Drop them.
fn scrub_host_session(c: &mut Command) {
    let nested = std::env::var_os("CLAUDECODE").is_some();
    for (key, _) in std::env::vars_os() {
        let k = key.to_string_lossy().to_ascii_uppercase();
        let host_var = k == "CLAUDECODE"
            || k.starts_with("CLAUDE_CODE_")
            || k.starts_with("CLAUDE_AGENT_SDK_")
            || k == "CLAUDE_PID"
            || k == "CLAUDE_EFFORT"
            || k == "CLAUDE_PREVIEW_CLASSIFIER_FLOOR";
        if host_var || (nested && k == "ANTHROPIC_BASE_URL") {
            c.env_remove(&key);
        }
    }
}

fn output(launch: &Launch, args: &[&str]) -> Option<(bool, String)> {
    let out = launch.command().args(args).stdin(Stdio::null()).output().ok()?;
    let mut text = String::from_utf8_lossy(&out.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&out.stderr));
    Some((out.status.success(), text))
}

fn strip_ansi(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut chars = s.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '\u{1b}' {
            if chars.peek() == Some(&'[') {
                chars.next();
                for n in chars.by_ref() {
                    if n.is_ascii_alphabetic() {
                        break;
                    }
                }
            }
        } else {
            out.push(c);
        }
    }
    out
}

#[derive(Serialize)]
pub struct AgentStatus {
    installed: bool,
    version: Option<String>,
    signed_in: bool,
    account: Option<String>,
    install_hint: &'static str,
}

#[tauri::command]
pub async fn agent_status(provider: String) -> Result<AgentStatus, String> {
    let p = Provider::parse(&provider)?;
    tauri::async_runtime::spawn_blocking(move || status_blocking(p))
        .await
        .map_err(|e| e.to_string())
}

fn status_blocking(p: Provider) -> AgentStatus {
    let install_hint = match p {
        Provider::Claude => "Install Claude Code from claude.com/code, then sign in.",
        Provider::Codex => "Install Codex with: npm i -g @openai/codex",
        Provider::OpenCode => "Install OpenCode with: npm i -g opencode-ai",
        Provider::OpenRouter | Provider::Vercel => {
            "ManimPro reaches this provider through OpenCode. Install it with: npm i -g opencode-ai"
        }
    };
    let Some(launch) = resolve(p.exe_name()) else {
        return AgentStatus { installed: false, version: None, signed_in: false, account: None, install_hint };
    };
    let version = output(&launch, &["--version"]).map(|(_, v)| v.lines().next().unwrap_or("").trim().to_string());
    if let Some((id, _, _)) = p.keyed() {
        let hint = crate::catalog::api_key_hint(id.to_string());
        return AgentStatus {
            installed: true,
            version,
            signed_in: hint.is_some(),
            account: hint.map(|h| format!("API key {h}")),
            install_hint,
        };
    }
    let (signed_in, account) = match p {
        Provider::Claude => match output(&launch, &["auth", "status"]) {
            Some((_, text)) => {
                let v: Value = serde_json::from_str(text.trim()).unwrap_or(Value::Null);
                let ok = v.get("loggedIn").and_then(Value::as_bool).unwrap_or(false);
                let field = |k: &str| v.get(k).and_then(Value::as_str).filter(|s| !s.is_empty()).map(str::to_string);
                let who = field("email").or_else(|| field("subscriptionType").map(|t| format!("Claude {t}"))).or_else(|| {
                    field("authMethod").map(|m| match m.as_str() {
                        "api_key" | "apiKey" => "API key".to_string(),
                        _ => "Claude account".to_string(),
                    })
                });
                (ok, who)
            }
            None => (false, None),
        },
        Provider::Codex => match output(&launch, &["login", "status"]) {
            Some((ok, text)) => (ok, Some(strip_ansi(text.trim()))),
            None => (false, None),
        },
        Provider::OpenCode | Provider::OpenRouter | Provider::Vercel => match output(&launch, &["auth", "list"]) {
            Some((_, text)) => {
                let clean = strip_ansi(&text);
                let count = clean
                    .lines()
                    .find_map(|l| l.trim_start_matches(['└', ' ']).strip_suffix(" credentials").map(str::trim).map(str::to_string))
                    .and_then(|n| n.parse::<u32>().ok())
                    .unwrap_or(0);
                // OpenCode also ships free models that need no sign-in.
                (true, Some(if count > 0 { format!("{count} provider(s) connected") } else { "Free models".into() }))
            }
            None => (false, None),
        },
    };
    AgentStatus { installed: true, version, signed_in, account, install_hint }
}

#[tauri::command]
pub async fn agent_models(provider: String) -> Result<Vec<String>, String> {
    let p = Provider::parse(&provider)?;
    match p {
        // Claude Code takes model aliases that always point at the latest of each family.
        Provider::Claude => Ok(vec!["opus".into(), "sonnet".into(), "haiku".into()]),
        // Codex picks the model that fits the user's plan by default; API-key providers
        // list their models from the models.dev catalog in the UI.
        Provider::Codex | Provider::OpenRouter | Provider::Vercel => Ok(vec![]),
        Provider::OpenCode => tauri::async_runtime::spawn_blocking(move || {
            let launch = resolve("opencode").ok_or("OpenCode is not installed.")?;
            let (_, text) = output(&launch, &["models"]).ok_or("Could not list OpenCode models.")?;
            Ok(strip_ansi(&text)
                .lines()
                .map(str::trim)
                .filter(|l| l.contains('/') && !l.contains(' '))
                .map(str::to_string)
                .collect())
        })
        .await
        .map_err(|e| e.to_string())?,
    }
}

/// Opens a console window running the vendor's own sign-in command.
#[tauri::command]
pub fn agent_login(provider: String) -> Result<(), String> {
    let p = Provider::parse(&provider)?;
    if p.keyed().is_some() {
        return Err("Add your API key in Settings, under Assistant.".into());
    }
    let launch = resolve(p.exe_name()).ok_or("This assistant is not installed yet.")?;
    let args: &[&str] = match p {
        Provider::Claude => &["auth", "login"],
        Provider::Codex => &["login"],
        _ => &["auth", "login"],
    };
    let mut c = Command::new(&launch.program);
    c.args(&launch.prefix).args(args);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x0000_0010); // CREATE_NEW_CONSOLE: the user signs in there
    }
    c.spawn().map_err(|e| format!("Could not open the sign-in window: {e}"))?;
    Ok(())
}

// ------------------------------------------------------------------ runs

pub struct Agents {
    /// run id -> process id, so Stop can kill the process tree.
    runs: Mutex<HashMap<u64, u32>>,
    next: AtomicU64,
}

impl Agents {
    pub fn new() -> Self {
        Self { runs: Mutex::new(HashMap::new()), next: AtomicU64::new(1) }
    }
}

const SYSTEM_PROMPT: &str = "You are working inside ManimPro, a desktop video editor built on Manim Community Edition (v0.22). \
The current folder is a ManimPro project: each .py file holds one or more Scene classes, and project.json holds the timeline (do not edit project.json or anything in .manimpro by hand). \
Write idiomatic Manim CE code (`from manim import *`). Prefer Text over Tex unless the user wants math; MathTex/Tex work only when LaTeX is installed (the render_scene tool tells you if it is missing). \
After changing a scene, call the manimpro render_scene tool to check it renders; read any error and fix it. \
Break longer videos into several Scene classes, one idea each (5-20 seconds): for anything over about 15 seconds, first call outline_video with the plan, then write each scene, render each one, and finally call arrange_timeline with the scenes in play order. \
Prefer splitting scenes across a few files grouped by section (e.g. intro.py, part1.py) when a video has many scenes. \
When the user asks for narration or a voiceover, arrange the scenes first, then call generate_voiceover once per scene with that scene's start time from get_timeline (list_voices shows the voices). \
Files the user attaches are listed at the end of their message; read them (images too) before you start. \
Do not install packages, create virtual environments or run shell commands. Keep replies short: say what you changed.";

#[tauri::command]
pub fn agent_run(
    app: AppHandle,
    agents: tauri::State<'_, Agents>,
    bridge: tauri::State<'_, Bridge>,
    provider: String,
    model: Option<String>,
    prompt: String,
    project_dir: String,
    session: Option<String>,
    instructions: Option<String>,
    files: Option<Vec<String>>,
) -> Result<u64, String> {
    let files = files.unwrap_or_default();
    let is_image = |f: &String| {
        let l = f.to_ascii_lowercase();
        [".png", ".jpg", ".jpeg", ".gif", ".webp"].iter().any(|e| l.ends_with(e))
    };
    let system = match instructions.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
        Some(extra) => format!("{SYSTEM_PROMPT}\n\nThe user's standing instructions:\n{extra}"),
        None => SYSTEM_PROMPT.to_string(),
    };
    let p = Provider::parse(&provider)?;
    let launch = resolve(p.exe_name()).ok_or("This assistant is not installed.")?;
    let rt = runtime_paths(&app);
    let python = rt.python.to_string_lossy().replace('\\', "/");
    let server = rt.script.with_file_name("mcp_server.py").to_string_lossy().replace('\\', "/");
    let (port, token) = bridge.address();
    let model = model.filter(|m| !m.trim().is_empty());

    let mut cmd = launch.command();
    // Some CLIs (OpenCode) trust an inherited PWD over the real working directory.
    cmd.current_dir(&project_dir).env("PWD", &project_dir);
    let mut stdin_text: Option<String> = None;

    match p {
        Provider::Claude => {
            let config = json!({ "mcpServers": { "manimpro": {
                "command": python, "args": [server],
                "env": { "MANIMPRO_BRIDGE": port.to_string(), "MANIMPRO_TOKEN": token }
            }}});
            let cfg_path = std::env::temp_dir().join(format!("manimpro-mcp-{port}.json"));
            std::fs::write(&cfg_path, config.to_string()).map_err(|e| e.to_string())?;
            cmd.args(["-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages"])
                .args(["--permission-mode", "acceptEdits"])
                .arg("--mcp-config")
                .arg(&cfg_path)
                .arg("--strict-mcp-config")
                .args(["--allowedTools", "Read,Edit,Write,Glob,Grep,mcp__manimpro"])
                .args(["--disallowedTools", "Bash,WebFetch,WebSearch"])
                .arg("--append-system-prompt")
                .arg(&system);
            if let Some(m) = &model {
                cmd.args(["--model", m]);
            }
            if let Some(s) = &session {
                cmd.args(["--resume", s]);
            }
            stdin_text = Some(prompt);
        }
        Provider::Codex => {
            cmd.args(["-a", "never", "exec"]);
            if let Some(s) = &session {
                cmd.args(["resume", s]);
            }
            cmd.args(["--json", "--skip-git-repo-check", "--sandbox", "workspace-write"])
                .arg("-C")
                .arg(&project_dir)
                .args(["-c", &format!("mcp_servers.manimpro.command=\"{python}\"")])
                .args(["-c", &format!("mcp_servers.manimpro.args=[\"{server}\"]")])
                .args([
                    "-c",
                    &format!("mcp_servers.manimpro.env={{MANIMPRO_BRIDGE=\"{port}\",MANIMPRO_TOKEN=\"{token}\"}}"),
                ]);
            if let Some(m) = &model {
                cmd.args(["-m", m]);
            }
            for f in files.iter().filter(|f| is_image(f)) {
                cmd.arg("-i").arg(f);
            }
            cmd.arg("-");
            stdin_text = Some(if session.is_some() { prompt } else { format!("{system}\n\nTask: {prompt}") });
        }
        Provider::OpenCode | Provider::OpenRouter | Provider::Vercel => {
            if let Some((id, env, name)) = p.keyed() {
                let key = crate::catalog::api_key(id).ok_or(format!("Add your {name} API key in Settings first."))?;
                cmd.env(env, key);
                if model.as_deref().is_none_or(|m| !m.starts_with(&format!("{id}/"))) {
                    return Err(format!("Choose a {name} model first."));
                }
            }
            let config = json!({
                "mcp": { "manimpro": {
                    "type": "local", "command": [python, server],
                    "environment": { "MANIMPRO_BRIDGE": port.to_string(), "MANIMPRO_TOKEN": token }
                }},
                "permission": { "edit": "allow", "bash": "deny", "webfetch": "deny" }
            });
            cmd.env("OPENCODE_CONFIG_CONTENT", config.to_string());
            cmd.args(["run", "--format", "json", "--dir"]).arg(&project_dir);
            if let Some(m) = &model {
                cmd.args(["-m", m]);
            }
            if let Some(s) = &session {
                cmd.args(["-s", s]);
            }
            for f in &files {
                cmd.arg("-f").arg(f);
            }
            let text = if session.is_some() { prompt } else { format!("{system}\n\nTask: {prompt}") };
            cmd.arg(text);
        }
    }

    cmd.stdin(if stdin_text.is_some() { Stdio::piped() } else { Stdio::null() })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = cmd.spawn().map_err(|e| format!("Could not start {}: {e}", p.exe_name()))?;
    let pid = child.id();
    if let (Some(text), Some(mut stdin)) = (stdin_text, child.stdin.take()) {
        std::thread::spawn(move || {
            let _ = stdin.write_all(text.as_bytes());
        });
    }
    let stdout = child.stdout.take().ok_or("no stdout")?;
    let stderr = child.stderr.take().ok_or("no stderr")?;
    let id = agents.next.fetch_add(1, Ordering::SeqCst);
    agents.runs.lock().unwrap().insert(id, pid);

    let app_err = app.clone();
    std::thread::spawn(move || {
        for line in BufReader::new(stderr).lines().map_while(Result::ok) {
            let _ = app_err.emit("agent-log", json!({ "run": id, "line": strip_ansi(&line) }));
        }
    });
    let app_out = app.clone();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            let payload = match serde_json::from_str::<Value>(line) {
                Ok(v) => json!({ "run": id, "event": v }),
                Err(_) => json!({ "run": id, "text": strip_ansi(line) }),
            };
            let _ = app_out.emit("agent-event", payload);
        }
        let code = child.wait().ok().and_then(|s| s.code());
        app_out.state::<Agents>().runs.lock().unwrap().remove(&id);
        let _ = app_out.emit("agent-event", json!({ "run": id, "done": true, "code": code }));
    });
    Ok(id)
}

#[tauri::command]
pub fn agent_cancel(agents: tauri::State<'_, Agents>, run: u64) -> Result<(), String> {
    let pid = agents.runs.lock().unwrap().get(&run).copied();
    if let Some(pid) = pid {
        // Kill the whole tree: agents start their own helpers (MCP server, node).
        let mut kill = Command::new("taskkill");
        kill.args(["/PID", &pid.to_string(), "/T", "/F"]);
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            kill.creation_flags(CREATE_NO_WINDOW);
        }
        let _ = kill.status();
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore = "probes the CLIs installed on this machine"]
    fn status_probe() {
        for p in [Provider::Claude, Provider::OpenCode, Provider::Codex] {
            let s = status_blocking(p);
            let launch = resolve(p.exe_name()).map(|l| l.program.display().to_string());
            println!("{}: installed={} signed_in={} account={:?} launch={:?}", p.exe_name(), s.installed, s.signed_in, s.account, launch);
        }
    }
}
