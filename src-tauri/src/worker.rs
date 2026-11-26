//! Supervises the Python render worker and speaks its JSON-lines protocol.

use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Emitter, Manager};
use tokio::sync::oneshot;

/// id -> (worker generation that owns it, reply channel)
type Pending = Arc<Mutex<HashMap<u64, (u64, oneshot::Sender<Result<Value, Value>>)>>>;

struct Running {
    child: Child,
    stdin: ChildStdin,
    generation: u64,
}

pub struct Worker {
    running: Mutex<Option<Running>>,
    pending: Pending,
    next_id: AtomicU64,
    generation: AtomicU64,
}

pub struct RuntimePaths {
    pub python: PathBuf,
    pub script: PathBuf,
}

/// In dev builds the runtime lives next to the sources (copying ~300 MB of
/// Python into target/ on every build would be painful). Release builds read
/// it from the installed resources folder.
pub fn runtime_paths(app: &AppHandle) -> RuntimePaths {
    let dev_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let dev = RuntimePaths {
        python: dev_root.join("runtime").join("python").join("python.exe"),
        script: dev_root.join("python").join("worker.py"),
    };
    if cfg!(debug_assertions) && dev.python.exists() {
        return dev;
    }
    let res = app.path().resource_dir().unwrap_or_default();
    RuntimePaths {
        python: res.join("runtime").join("python").join("python.exe"),
        script: res.join("worker").join("worker.py"),
    }
}

impl Worker {
    pub fn new() -> Self {
        Self {
            running: Mutex::new(None),
            pending: Arc::new(Mutex::new(HashMap::new())),
            next_id: AtomicU64::new(1),
            generation: AtomicU64::new(0),
        }
    }

    pub fn start(&self, app: &AppHandle) -> Result<(), String> {
        let mut guard = self.running.lock().unwrap();
        if guard.is_some() {
            return Ok(());
        }
        let paths = runtime_paths(app);
        if !paths.python.exists() {
            return Err(format!(
                "The Manim runtime is missing ({}). Run `pnpm setup:runtime` or reinstall ManimPro.",
                paths.python.display()
            ));
        }

        let mut cmd = Command::new(&paths.python);
        cmd.arg("-u")
            .arg(&paths.script)
            .env("PYTHONUTF8", "1")
            .env("PYTHONNOUSERSITE", "1")
            .env("PYTHONIOENCODING", "utf-8")
            .env_remove("PYTHONPATH")
            .env_remove("PYTHONHOME")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        if let Some(bin) = crate::latex::tex_bin(app) {
            cmd.env("PATH", crate::latex::prepend_path(&bin));
        }
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        }

        let mut child = cmd.spawn().map_err(|e| format!("Could not start the render worker: {e}"))?;
        let stdin = child.stdin.take().ok_or("worker stdin unavailable")?;
        let stdout = child.stdout.take().ok_or("worker stdout unavailable")?;
        let stderr = child.stderr.take().ok_or("worker stderr unavailable")?;
        let generation = self.generation.fetch_add(1, Ordering::SeqCst) + 1;

        // Protocol reader
        let pending = self.pending.clone();
        let app_out = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                let Ok(msg) = serde_json::from_str::<Value>(&line) else { continue };
                if let Some(id) = msg.get("id").and_then(Value::as_u64) {
                    if let Some((_, tx)) = pending.lock().unwrap().remove(&id) {
                        let _ = match msg.get("error") {
                            Some(err) => tx.send(Err(err.clone())),
                            None => tx.send(Ok(msg.get("result").cloned().unwrap_or(Value::Null))),
                        };
                    }
                } else if msg.get("event").is_some() {
                    let _ = app_out.emit("worker-event", msg);
                }
            }
            // Process ended: fail what this generation still owed.
            let mut map = pending.lock().unwrap();
            let orphaned: Vec<u64> = map.iter().filter(|(_, (g, _))| *g == generation).map(|(id, _)| *id).collect();
            for id in orphaned {
                if let Some((_, tx)) = map.remove(&id) {
                    let _ = tx.send(Err(json!({ "message": "The render worker stopped.", "cancelled": true })));
                }
            }
            drop(map);
            let worker = app_out.state::<Worker>();
            worker.forget(generation);
            let _ = app_out.emit("worker-event", json!({ "event": "exit" }));
        });

        // Log reader
        let app_err = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                let _ = app_err.emit("worker-log", line);
            }
        });

        *guard = Some(Running { child, stdin, generation });
        Ok(())
    }

    fn forget(&self, generation: u64) {
        let mut guard = self.running.lock().unwrap();
        if guard.as_ref().is_some_and(|r| r.generation == generation) {
            *guard = None;
        }
    }

    pub fn stop(&self) {
        if let Some(mut r) = self.running.lock().unwrap().take() {
            let _ = r.child.kill();
            let _ = r.child.wait();
        }
    }

    pub async fn call(&self, app: &AppHandle, method: &str, params: Value) -> Result<Value, Value> {
        self.start(app).map_err(|e| json!({ "message": e }))?;
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        let (tx, rx) = oneshot::channel();
        let line = json!({ "id": id, "method": method, "params": params }).to_string();
        {
            let mut guard = self.running.lock().unwrap();
            let Some(r) = guard.as_mut() else {
                return Err(json!({ "message": "The render worker is not running." }));
            };
            self.pending.lock().unwrap().insert(id, (r.generation, tx));
            if let Err(e) = writeln!(r.stdin, "{line}").and_then(|_| r.stdin.flush()) {
                self.pending.lock().unwrap().remove(&id);
                return Err(json!({ "message": format!("Could not reach the render worker: {e}") }));
            }
        }
        let _ = app.emit("worker-event", json!({ "event": "job", "job": id, "method": method }));
        rx.await.unwrap_or_else(|_| Err(json!({ "message": "The render worker stopped.", "cancelled": true })))
    }
}
