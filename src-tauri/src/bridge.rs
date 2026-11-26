//! Lets an agent's MCP tools act on the running app.
//!
//! mcp_server.py (started by the agent CLI) connects to a localhost socket and
//! sends {"token", "id", "tool", "args"} lines. We forward each call to the UI as
//! a `bridge-call` event; the UI does the work (render, edit timeline) and
//! answers with the `bridge_reply` command. Only processes we launched know the
//! random token, so other local programs cannot drive the app.

use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager};

type Waiters = Arc<Mutex<HashMap<u64, mpsc::Sender<Value>>>>;

pub struct Bridge {
    port: Mutex<u16>,
    token: String,
    waiters: Waiters,
    next: AtomicU64,
}

impl Bridge {
    pub fn new() -> Self {
        // RandomState is keyed from the OS random source; four independent keys give 256 bits.
        use std::hash::{BuildHasher, Hasher};
        let token: String = (0..4)
            .map(|i| {
                let mut h = std::collections::hash_map::RandomState::new().build_hasher();
                h.write_u64(i);
                format!("{:016x}", h.finish())
            })
            .collect();
        Self {
            port: Mutex::new(0),
            token,
            waiters: Arc::new(Mutex::new(HashMap::new())),
            next: AtomicU64::new(1),
        }
    }

    pub fn address(&self) -> (u16, String) {
        (*self.port.lock().unwrap(), self.token.clone())
    }

    pub fn start(app: &AppHandle) -> std::io::Result<()> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let bridge = app.state::<Bridge>();
        *bridge.port.lock().unwrap() = listener.local_addr()?.port();
        let app = app.clone();
        std::thread::spawn(move || {
            for stream in listener.incoming().flatten() {
                let app = app.clone();
                std::thread::spawn(move || {
                    let _ = serve(&app, stream);
                });
            }
        });
        Ok(())
    }
}

fn serve(app: &AppHandle, stream: TcpStream) -> std::io::Result<()> {
    let mut writer = stream.try_clone()?;
    let bridge = app.state::<Bridge>();
    for line in BufReader::new(stream).lines() {
        let line = line?;
        let Ok(msg) = serde_json::from_str::<Value>(&line) else { continue };
        let reply_id = msg.get("id").cloned().unwrap_or(Value::Null);
        if msg.get("token").and_then(Value::as_str) != Some(bridge.token.as_str()) {
            writeln!(writer, "{}", json!({ "id": reply_id, "error": "unauthorized" }))?;
            continue;
        }
        let call = bridge.next.fetch_add(1, Ordering::SeqCst);
        let (tx, rx) = mpsc::channel();
        bridge.waiters.lock().unwrap().insert(call, tx);
        let _ = app.emit(
            "bridge-call",
            json!({ "call": call, "tool": msg.get("tool"), "args": msg.get("args").cloned().unwrap_or(json!({})) }),
        );
        // Renders can take a while; give up after 10 minutes.
        let result = rx
            .recv_timeout(Duration::from_secs(600))
            .unwrap_or_else(|_| json!({ "ok": false, "error": "ManimPro did not answer in time." }));
        bridge.waiters.lock().unwrap().remove(&call);
        writeln!(writer, "{}", json!({ "id": reply_id, "result": result }))?;
        writer.flush()?;
    }
    Ok(())
}

#[tauri::command]
pub fn bridge_reply(bridge: tauri::State<'_, Bridge>, call: u64, result: Value) {
    if let Some(tx) = bridge.waiters.lock().unwrap().remove(&call) {
        let _ = tx.send(result);
    }
}
