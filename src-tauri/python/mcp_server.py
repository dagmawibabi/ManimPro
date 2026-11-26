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
# Started by another app (Claude Desktop, Cursor, Claude Code...) instead of by ManimPro:
# the running app publishes its address in a file when "Let other apps use ManimPro" is on.
SHARE_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "dev.manimpro.app", "bridge.json")
EXTERNAL = not PORT
LOCAL_FILES = os.environ.get("MANIMPRO_LOCAL_FILES") == "1"


def _load_share() -> None:
    global PORT, TOKEN
    try:
        with open(SHARE_FILE, encoding="utf-8") as f:
            info = json.load(f)
        PORT, TOKEN = int(info["port"]), str(info["token"])
    except (OSError, ValueError, KeyError):
        PORT, TOKEN = 0, ""


if EXTERNAL:
    _load_share()

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
        "name": "remove_audio",
        "description": "Remove the audio clip (music or voiceover) at the given 0-based index from the timeline (see get_timeline's audio list). The audio file stays in the project.",
        "inputSchema": {
            "type": "object",
            "properties": {"index": {"type": "integer", "minimum": 0}},
            "required": ["index"],
            "additionalProperties": False,
        },
    },
    {
        "name": "clear_audio",
        "description": "Remove every clip from the audio track (the files stay in the project).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "set_clip_speed",
        "description": (
            "Change how fast a video clip plays: 2 is twice as fast (half as long on the timeline), 0.5 is half speed. "
            "Clips after it move to make room. Use get_timeline for indexes; 1 resets to normal."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "minimum": 0},
                "speed": {"type": "number", "minimum": 0.25, "maximum": 4},
            },
            "required": ["index", "speed"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_captions",
        "description": "List the captions on the timeline (index, start, end, text).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "generate_captions",
        "description": "Make captions from the narration: voiceovers on the audio track and self.voiceover(...) lines inside scenes. Replaces captions made this way before; hand-written ones stay.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "set_captions",
        "description": "Replace all captions with this list (seconds on the timeline). Use [] to remove them all. Keep each to one or two short lines.",
        "inputSchema": {
            "type": "object",
            "properties": {"captions": {"type": "array", "items": {"type": "object", "properties": {
                "start": {"type": "number"}, "end": {"type": "number"}, "text": {"type": "string"}}, "required": ["start", "end", "text"]}}},
            "required": ["captions"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_transition",
        "description": "Set how a video clip comes in from the one before it: 'fade' (through black), 'crossfade' (clips must touch) or 'none'. Index from get_timeline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "minimum": 0},
                "kind": {"type": "string", "enum": ["none", "fade", "crossfade"]},
                "duration": {"type": "number", "minimum": 0.1, "maximum": 3, "description": "Seconds (default 0.6)"},
            },
            "required": ["index", "kind"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_frame_shape",
        "description": "Change the project's frame shape (16:9, 9:16 for Shorts/Reels, 1:1, 4:5, 4:3, 21:9). Scenes are re-rendered. Lay scenes out for the new shape afterwards.",
        "inputSchema": {
            "type": "object",
            "properties": {"aspect": {"type": "string", "enum": ["16:9", "9:16", "1:1", "4:5", "4:3", "21:9"]}},
            "required": ["aspect"],
            "additionalProperties": False,
        },
    },
    {
        "name": "export_video",
        "description": (
            "Export the timeline (or one scene) to a file. Renders every scene again at the chosen quality, so it can take a few minutes. "
            "Returns the file path. Only export when the user asks for it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["mp4", "webm", "mov", "gif", "png"], "description": "Default mp4"},
                "resolution": {"type": "string", "enum": ["draft", "high", "1440p", "4k"], "description": "720p, 1080p, 1440p or 4K (default high)"},
                "captions": {"type": "string", "enum": ["off", "srt", "burn"], "description": "Subtitle file, burned in, or none (default srt when there are captions)"},
                "transparent": {"type": "boolean", "description": "Transparent background (mov or webm only)"},
                "file": {"type": "string", "description": "Export just this scene: its file name..."},
                "scene": {"type": "string", "description": "...and Scene class"},
                "output": {"type": "string", "description": "Where to save (default: the project folder)"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_music",
        "description": "The built-in music library: original tracks, free for any use (CC0), with mood, tempo and length.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "add_music",
        "description": "Put a music library track on the audio track (copied into the project).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Track id from list_music"},
                "start": {"type": "number", "description": "Seconds on the timeline (default 0)"},
                "volume": {"type": "number", "minimum": 0, "maximum": 2, "description": "1 is normal; about 0.3 sits well under narration"},
            },
            "required": ["id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_media_to_timeline",
        "description": "Put the user's own photo or video on the video track. Path is absolute, or relative to the project. Photos last `seconds` (default 4).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "number", "description": "Seconds on the timeline (default: the end)"},
                "seconds": {"type": "number", "minimum": 0.5, "description": "How long a photo stays up"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_python_packages",
        "description": "Extra Python packages installed for scenes (Settings > Python packages), and whether ManimGL is installed.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "install_python_package",
        "description": "Ask the user to install a package from PyPI for scenes (e.g. networkx, manim-slides). The user sees a confirmation and can say no. Don't use pip or shell commands yourself.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Package name, optionally with a version"},
                           "reason": {"type": "string", "description": "One sentence on why the scene needs it"}},
            "required": ["name", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "export_project_zip",
        "description": "Save the whole project (code, assets, timeline) as a .zip next to the project folder, for sharing or backup. Renders are left out unless include_renders is true.",
        "inputSchema": {
            "type": "object",
            "properties": {"include_renders": {"type": "boolean"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "save_as_template",
        "description": "Save this project as one of the user's own templates, so new projects can start from it (home page > Your templates).",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "manim_docs",
        "description": (
            "Look up Manim Community's own documentation for a class, function or constant (offline, matches the installed version): "
            "signature and docstring. Use it before guessing an argument name. Accepts partial names like 'axes plot' or 'Transform'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
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
    if EXTERNAL and _sock is None:
        _load_share()  # ManimPro may have restarted on a new port
    if not PORT:
        if EXTERNAL:
            return {"ok": False, "error": "ManimPro isn't open, or 'Let other apps use ManimPro' is off in its Settings > Assistant. Open ManimPro with a project, then try again."}
        return {"ok": False, "error": "ManimPro is not running (no bridge port)."}
    if _sock is None:
        try:
            _sock = socket.create_connection(("127.0.0.1", PORT), timeout=660)
        except OSError:
            return {"ok": False, "error": "Could not reach ManimPro. Make sure it is open with a project."}
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


_manim_index = None


def manim_docs(args: dict) -> list[dict]:
    """Signature and docstring of the best matches for a query, from the installed Manim."""
    global _manim_index
    import inspect
    import re

    if _manim_index is None:
        import manim

        _manim_index = {}
        for name in dir(manim):
            if name.startswith("_"):
                continue
            obj = getattr(manim, name)
            _manim_index[name] = obj
            if inspect.isclass(obj):
                # Inherited methods too (Axes.plot lives on CoordinateSystem).
                for meth in dir(obj):
                    if meth.startswith("_"):
                        continue
                    fn = getattr(obj, meth, None)
                    if callable(fn):
                        _manim_index.setdefault(f"{name}.{meth}", fn)
    words = [w for w in re.split(r"[\s.]+", str(args.get("query", "")).lower()) if w]
    if not words:
        return [{"type": "text", "text": "Give a name to look up, e.g. Axes.plot or Transform."}]

    def score(key: str) -> int:
        k = key.lower()
        if k == ".".join(words) or k == words[-1]:
            return 100
        hits = sum(w in k for w in words)
        return hits * 10 - len(k) // 10 if hits == len(words) else 0

    best = sorted((k for k in _manim_index if score(k) > 0), key=score, reverse=True)[:4]
    if not best:
        return [{"type": "text", "text": f"Nothing in Manim matches {args.get('query')!r}."}]
    out = []
    for key in best:
        obj = _manim_index[key]
        try:
            sig = str(inspect.signature(obj.__init__ if inspect.isclass(obj) else obj))
        except (TypeError, ValueError):
            sig = ""
        doc = inspect.getdoc(obj) or "(no description)"
        out.append(f"## {key}{sig}\n{doc[:2500]}")
    return [{"type": "text", "text": "\n\n".join(out)}]


LOCAL_TOOLS = [
    {
        "name": "read_local_file",
        "description": (
            "Read a file anywhere on this computer by absolute path (notes, data, code, images). Text comes back as text "
            "(up to max_chars); images come back as a picture you can see. Use import_into_project to copy a file a scene needs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path, e.g. C:/Users/me/Documents/notes.md"},
                "max_chars": {"type": "integer", "minimum": 1000, "maximum": 400000},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_local_folder",
        "description": "List the files and folders in a folder on this computer (absolute path), with sizes.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "import_into_project",
        "description": "Copy a file from elsewhere on this computer into the project (e.g. an image or CSV a scene should use). Returns its new path in the project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path of the file to copy"},
                "folder": {"type": "string", "description": "Project subfolder to copy into (optional, default the project root)"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
]
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


def read_local_file(args: dict) -> list[dict]:
    import base64
    import io

    path = os.path.expandvars(os.path.expanduser(str(args.get("path", ""))))
    if not os.path.isabs(path) or not os.path.isfile(path):
        return [{"type": "text", "text": f"No file at {path} (give an absolute path)."}]
    if path.lower().endswith(IMAGE_EXT):
        from PIL import Image

        img = Image.open(path)
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        return [{"type": "text", "text": f"{path} ({img.width}x{img.height})"},
                {"type": "image", "data": base64.b64encode(buf.getvalue()).decode("ascii"), "mimeType": "image/jpeg"}]
    limit = int(args.get("max_chars") or 100000)
    with open(path, "rb") as f:
        raw = f.read(limit * 4 + 1)
    if b"\x00" in raw[:4096]:
        return [{"type": "text", "text": f"{path} looks like a binary file ({os.path.getsize(path):,} bytes); it can't be shown as text."}]
    text = raw.decode("utf-8", errors="replace")
    more = len(text) > limit or os.path.getsize(path) > len(raw)
    return [{"type": "text", "text": text[:limit] + (f"\n\n[... cut at {limit:,} characters]" if more else "")}]


def list_local_folder(args: dict) -> list[dict]:
    path = os.path.expandvars(os.path.expanduser(str(args.get("path", ""))))
    if not os.path.isabs(path) or not os.path.isdir(path):
        return [{"type": "text", "text": f"No folder at {path} (give an absolute path)."}]
    rows = []
    with os.scandir(path) as it:
        for e in sorted(it, key=lambda e: (not e.is_dir(), e.name.lower()))[:500]:
            try:
                rows.append(f"{e.name}/" if e.is_dir() else f"{e.name}  ({e.stat().st_size:,} bytes)")
            except OSError:
                continue
    return [{"type": "text", "text": f"{path}\n" + ("\n".join(rows) or "(empty)")}]


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
            "instructions": "Tools for the ManimPro video editor (the project open in the app): list and render scenes, look at frames, arrange the timeline, voiceovers, captions-ready narration. Scene files live in the project folder; get it from list_scenes.",
        })
    elif method == "ping":
        respond(req_id, {})
    elif method == "tools/list":
        respond(req_id, {"tools": TOOLS + (LOCAL_TOOLS if LOCAL_FILES else [])})
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name == "manim_docs":
            try:
                respond(req_id, {"content": manim_docs(params.get("arguments") or {}), "isError": False})
            except Exception as exc:  # noqa: BLE001
                respond(req_id, {"content": [{"type": "text", "text": f"Lookup failed: {exc}"}], "isError": True})
            return
        if LOCAL_FILES and name in ("read_local_file", "list_local_folder"):
            try:
                content = (read_local_file if name == "read_local_file" else list_local_folder)(params.get("arguments") or {})
                respond(req_id, {"content": content, "isError": False})
            except Exception as exc:  # noqa: BLE001
                respond(req_id, {"content": [{"type": "text", "text": f"Could not read it: {exc}"}], "isError": True})
            return
        if name not in {t["name"] for t in TOOLS + (LOCAL_TOOLS if LOCAL_FILES else [])}:
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
