"""ManimPro tools for coding agents (Claude Code, Codex, OpenCode), served over MCP stdio.

The agent CLI starts this script. Every tool call is forwarded to the running
ManimPro app over a localhost socket (MANIMPRO_BRIDGE port + MANIMPRO_TOKEN), so
renders and timeline edits happen in the app the user is looking at.
No third-party packages: the protocol is newline-delimited JSON-RPC 2.0.
"""

from __future__ import annotations

import json
import os
import socket
import sys

# MCP is UTF-8. Windows would otherwise use the console code page and garble
# characters such as "·" or "π" in tool arguments.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8", errors="replace")

PORT = int(os.environ.get("MANIMPRO_BRIDGE", "0"))
TOKEN = os.environ.get("MANIMPRO_TOKEN", "")

TOOLS = [
    {
        "name": "view_scene",
        "description": (
            "Look at a scene: returns still frames from its rendered preview as images, so you can check layout, "
            "overlaps, text that runs off the frame and colors. Renders the scene first if it has no render yet "
            "(or when rerender is true, e.g. after editing it). Give exact times in seconds, or a count of evenly spaced frames."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Scene file name in the project, e.g. scenes.py"},
                "scene": {"type": "string", "description": "Scene class name, e.g. Intro"},
                "times": {"type": "array", "items": {"type": "number"}, "description": "Seconds into the scene, e.g. [1.5, 4]. Up to 8."},
                "count": {"type": "integer", "minimum": 1, "maximum": 8, "description": "Evenly spaced frames when times is not given (default 4)."},
                "rerender": {"type": "boolean", "description": "Render again before looking (default false)."},
            },
            "required": ["file", "scene"],
            "additionalProperties": False,
        },
    },
    {
        "name": "view_timeline",
        "description": (
            "Look at the finished video: returns frames from the timeline (all scenes in play order) as images, "
            "at the given times in seconds on the timeline, or evenly spaced. Use it to check transitions between scenes "
            "and the overall look before you finish."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "times": {"type": "array", "items": {"type": "number"}, "description": "Seconds on the timeline. Up to 8."},
                "count": {"type": "integer", "minimum": 1, "maximum": 8, "description": "Evenly spaced frames when times is not given (default 6)."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_scenes",
        "description": "List the project's scene files and the Scene classes in each, with whether each is rendered and its duration. Also reports whether LaTeX is installed.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "render_scene",
        "description": "Render one Scene class at preview quality and show it in ManimPro. Returns the duration on success, or the Python error with its line number. Save your edits before calling this.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Scene file name in the project, e.g. scenes.py"},
                "scene": {"type": "string", "description": "Scene class name, e.g. Intro"},
            },
            "required": ["file", "scene"],
            "additionalProperties": False,
        },
    },
    {
        "name": "outline_video",
        "description": (
            "Plan a multi-scene video before writing code. Call this first for anything longer than about "
            "15 seconds: list the scenes in play order, one idea per scene (5-20 s each). ManimPro shows the "
            "plan to the user as a storyboard."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Working title of the video"},
                "scenes": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string", "description": "File the Scene class will live in, e.g. scenes.py"},
                            "scene": {"type": "string", "description": "Scene class name, e.g. Intro"},
                            "summary": {"type": "string", "description": "What this scene shows, in one sentence"},
                            "seconds": {"type": "number", "description": "Rough length in seconds"},
                        },
                        "required": ["file", "scene", "summary"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "scenes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "arrange_timeline",
        "description": (
            "Replace the video track with these scenes, in this order, back to back (optional gap in seconds). "
            "Scenes that are not rendered yet are rendered first. Use it after the scenes render cleanly."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {"file": {"type": "string"}, "scene": {"type": "string"}},
                        "required": ["file", "scene"],
                        "additionalProperties": False,
                    },
                },
                "gap": {"type": "number", "minimum": 0, "description": "Seconds of black between scenes (default 0)"},
            },
            "required": ["scenes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_voices",
        "description": "List the ElevenLabs voices available for voiceovers (name, id, category, labels such as accent or gender). Needs the user's ElevenLabs key.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "generate_voiceover",
        "description": (
            "Speak text with ElevenLabs, save it as an MP3 in the project's assets/audio folder and, by default, "
            "place it on the audio track. For narrated videos, generate one voiceover per scene and set `start` to "
            "that scene's start time from get_timeline. Returns the file and its duration."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "What to say. Plain sentences; numbers and symbols spelled the way they should sound."},
                "voice": {"type": "string", "description": "Voice name or id from list_voices (optional; the user's default otherwise)"},
                "name": {"type": "string", "description": "File name without extension, e.g. intro-narration"},
                "start": {"type": "number", "description": "Timeline position in seconds (optional)"},
                "add_to_timeline": {"type": "boolean", "description": "Place it on the audio track (default true)"},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_timeline",
        "description": "Return the video track (scene clips in order, with start/in/out seconds) and the audio track.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "add_to_timeline",
        "description": "Render the scene if needed and place it on the video track. Without `start` it goes at the end.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string"},
                "scene": {"type": "string"},
                "start": {"type": "number", "description": "Timeline position in seconds (optional)"},
            },
            "required": ["file", "scene"],
            "additionalProperties": False,
        },
    },
    {
        "name": "remove_from_timeline",
        "description": "Remove the video clip at the given 0-based index (see get_timeline).",
        "inputSchema": {
            "type": "object",
            "properties": {"index": {"type": "integer", "minimum": 0}},
            "required": ["index"],
            "additionalProperties": False,
        },
    },
    {
        "name": "clear_timeline",
        "description": "Remove every clip from the video track (audio is kept).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

_sock: socket.socket | None = None
_reader = None
_next = 0


def app_call(tool: str, args: dict) -> dict:
    global _sock, _reader, _next
    if not PORT:
        return {"ok": False, "error": "ManimPro is not running (no bridge port)."}
    if _sock is None:
        _sock = socket.create_connection(("127.0.0.1", PORT), timeout=660)
        _reader = _sock.makefile("r", encoding="utf-8")
    _next += 1
    msg = {"token": TOKEN, "id": _next, "tool": tool, "args": args}
    _sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    line = _reader.readline()
    if not line:
        _sock = None
        return {"ok": False, "error": "ManimPro closed the connection."}
    reply = json.loads(line)
    if "error" in reply:
        return {"ok": False, "error": reply["error"]}
    return reply.get("result", {})


MAX_FRAMES = 8
FRAME_WIDTH = 960


def grab_frames(video: str, times: list[float]) -> list[tuple[float, str]]:
    """JPEG frames (base64) from a video at the given times, in time order."""
    import base64
    import io

    import av

    out: list[tuple[float, str]] = []
    with av.open(video) as c:
        s = c.streams.video[0]
        duration = float(c.duration / 1_000_000) if c.duration else 0.0
        for t in sorted(times):
            t = max(0.0, min(t, max(0.0, duration - 0.02)))
            c.seek(int(t / s.time_base), stream=s, backward=True)
            frame = None
            for f in c.decode(s):
                frame = f
                # Seeking lands on the keyframe before t; decode forward to it.
                if f.time is not None and f.time >= t - 0.03:
                    break
            if frame is None:
                continue
            img = frame.to_image()
            if img.width > FRAME_WIDTH:
                img = img.resize((FRAME_WIDTH, round(img.height * FRAME_WIDTH / img.width)))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82)
            out.append((t, base64.b64encode(buf.getvalue()).decode("ascii")))
    return out


def spaced(duration: float, n: int) -> list[float]:
    n = max(1, min(MAX_FRAMES, n))
    return [duration * (i + 0.5) / n for i in range(n)]


def view_frames(name: str, args: dict) -> list[dict]:
    """Runs view_scene / view_timeline: the app says which videos to look at, we extract the frames."""
    times = [float(t) for t in (args.get("times") or [])][:MAX_FRAMES]
    if name == "view_scene":
        info = app_call("view_scene", {k: args[k] for k in ("file", "scene", "rerender") if k in args})
        if info.get("ok") is False:
            return [{"type": "text", "text": json.dumps(info, indent=1)}]
        picks = times or spaced(info["duration"], int(args.get("count") or 4))
        shots = [(t, info["video"], t) for t in picks]
        head = f"{args['scene']}: {info['duration']:.1f}s, {info.get('resolution', '')}"
    else:
        info = app_call("view_timeline", {})
        if info.get("ok") is False:
            return [{"type": "text", "text": json.dumps(info, indent=1)}]
        picks = times or spaced(info["duration"], int(args.get("count") or 6))
        shots = []
        for t in picks:
            seg = next((s for s in info["segments"] if s["start"] <= t < s["end"]), None)
            if seg:
                shots.append((t, seg["video"], seg["in"] + (t - seg["start"])))
        head = f"Timeline: {info['duration']:.1f}s"
    content: list[dict] = [{"type": "text", "text": head}]
    by_video: dict[str, list[tuple[float, float]]] = {}
    for label_t, video, local_t in shots:
        by_video.setdefault(video, []).append((label_t, local_t))
    frames: list[tuple[float, str]] = []
    for video, pairs in by_video.items():
        grabbed = grab_frames(video, [lt for _, lt in pairs])
        # grab_frames sorts by local time; pair them back up in the same order.
        for (label_t, _), (_, data) in zip(sorted(pairs, key=lambda p: p[1]), grabbed):
            frames.append((label_t, data))
    for label_t, data in sorted(frames):
        content.append({"type": "text", "text": f"t = {label_t:.2f}s"})
        content.append({"type": "image", "data": data, "mimeType": "image/jpeg"})
    if len(content) == 1:
        content.append({"type": "text", "text": "Nothing to show at those times (the timeline is empty there)."})
    return content


def respond(req_id, result=None, error=None) -> None:
    msg = {"jsonrpc": "2.0", "id": req_id}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(msg: dict) -> None:
    method = msg.get("method")
    req_id = msg.get("id")
    if req_id is None:  # notification
        return
    if method == "initialize":
        version = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
        respond(req_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "manimpro", "version": "0.2.0"},
            "instructions": "Tools for the ManimPro video editor: render scenes and arrange the timeline.",
        })
    elif method == "ping":
        respond(req_id, {})
    elif method == "tools/list":
        respond(req_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name not in {t["name"] for t in TOOLS}:
            respond(req_id, error={"code": -32602, "message": f"Unknown tool {name}"})
            return
        if name in ("view_scene", "view_timeline"):
            try:
                content = view_frames(name, params.get("arguments") or {})
                respond(req_id, {"content": content, "isError": not any(c["type"] == "image" for c in content)})
            except Exception as exc:  # noqa: BLE001 - report, don't crash the agent's connection
                respond(req_id, {"content": [{"type": "text", "text": f"Could not get frames: {exc}"}], "isError": True})
            return
        try:
            result = app_call(name, params.get("arguments") or {})
        except OSError as exc:
            result = {"ok": False, "error": f"Could not reach ManimPro: {exc}"}
        failed = result.get("ok") is False
        respond(req_id, {
            "content": [{"type": "text", "text": json.dumps(result, indent=1)}],
            "isError": failed,
        })
    else:
        respond(req_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main() -> None:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            handle(json.loads(raw))
        except Exception as exc:  # noqa: BLE001 - never crash the agent's MCP connection
            sys.stderr.write(f"manimpro mcp: {exc}\n")


if __name__ == "__main__":
    main()
