"""ManimPro render worker.

A long-lived process that keeps manim imported so previews start instantly.
Protocol: one JSON object per line.
  stdin  <- {"id": 1, "method": "render", "params": {...}}
  stdout -> {"id": 1, "result": {...}} | {"id": 1, "error": {...}}
  stdout -> {"event": "progress", ...}   (unsolicited)
Everything manim, rich or ffmpeg print goes to stderr, which the app shows as a log.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import queue
import shutil
import subprocess
import tempfile
import sys
import threading
import traceback
from pathlib import Path

# --- Keep stdout clean for the protocol --------------------------------------
_proto = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
os.dup2(2, 1)
sys.stdout = sys.stderr
_send_lock = threading.Lock()


def send(obj: dict) -> None:
    line = json.dumps(obj, default=str)
    with _send_lock:
        _proto.write(line + "\n")
        _proto.flush()


def event(kind: str, **data) -> None:
    send({"event": kind, **data})


# --- Manim setup -------------------------------------------------------------
import manim  # noqa: E402
# Extra packages the user added in Settings go LAST, so ManimPro's own manim and numpy win.
_extra = os.environ.get("MANIMPRO_PACKAGES")
if _extra and os.path.isdir(_extra) and _extra not in sys.path:
    sys.path.append(_extra)

from manim import Scene, config, tempconfig  # noqa: E402

QUALITY = {
    "fast": "low_quality",  # 360p @12, see FAST below
    "preview": "low_quality",  # 854x480 @15
    "draft": "medium_quality",  # 1280x720 @30
    "high": "high_quality",  # 1920x1080 @60
    "1440p": "production_quality",  # 2560x1440 @60
    "4k": "fourk_quality",  # 3840x2160 @60
}
QUALITY_HEIGHT = {
    "low_quality": 480,
    "medium_quality": 720,
    "high_quality": 1080,
    "production_quality": 1440,
    "fourk_quality": 2160,
}

_current_job: dict = {"id": None}
_orig_play = Scene.play


def _play_with_progress(self, *args, **kwargs):
    result = _orig_play(self, *args, **kwargs)
    n = getattr(self, "_mp_animations", 0) + 1
    self._mp_animations = n
    t = getattr(getattr(self, "renderer", None), "time", None)
    event("progress", job=_current_job["id"], animations=n, time=t)
    return result


Scene.play = _play_with_progress


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        found = shutil.which("ffmpeg")
        if not found:
            raise RuntimeError("FFmpeg is missing from the runtime.")
        return found


def probe(path: str) -> dict:
    import av

    with av.open(path) as c:
        s = c.streams.video[0]
        duration = float(c.duration / 1_000_000) if c.duration else float(s.duration * s.time_base)
        return {
            "duration": duration,
            "width": s.codec_context.width,
            "height": s.codec_context.height,
            "fps": float(s.average_rate or 0),
        }


# --- Methods -----------------------------------------------------------------
def m_ping(_params: dict) -> dict:
    return {
        "manim": manim.__version__,
        "python": sys.version.split()[0],
        "latex": shutil.which("latex") is not None,
        "ffmpeg": ffmpeg_exe(),
    }


def m_list_scenes(params: dict) -> dict:
    path = params["path"]
    source = params.get("source")
    if source is None:
        source = Path(path).read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        return {"scenes": [], "error": {"message": e.msg, "line": e.lineno}}

    def base_name(b: ast.expr) -> str:
        if isinstance(b, ast.Name):
            return b.id
        if isinstance(b, ast.Attribute):
            return b.attr
        return ""

    scene_classes: set[str] = set()
    scenes = []
    # Two passes so subclasses of user-defined scenes are found too.
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    for _ in range(2):
        for node in classes:
            bases = [base_name(b) for b in node.bases]
            if any(b.endswith("Scene") or b in scene_classes for b in bases):
                scene_classes.add(node.name)
    for node in classes:
        if node.name in scene_classes:
            scenes.append({"name": node.name, "line": node.lineno})
    return {"scenes": scenes}


class _InFolder:
    """Runs a block with the scene's folder as the working directory, so relative
    paths in user code (ImageMobject("logo.png"), SVGMobject("icons/x.svg"),
    open("data.csv")) resolve the way they do with the manim command line."""

    def __init__(self, path: str):
        self.folder = str(Path(path).parent)

    def __enter__(self):
        self.before = os.getcwd()
        try:
            os.chdir(self.folder)
        except OSError:
            pass
        return self

    def __exit__(self, *exc):
        try:
            os.chdir(self.before)
        except OSError:
            pass
        return False


def _folder_cfg(path: str) -> str | None:
    """A manim.cfg next to the scene file (or in a parent folder, up to three levels)."""
    p = Path(path).parent
    for _ in range(4):
        cfg = p / "manim.cfg"
        if cfg.is_file():
            return str(cfg)
        if p.parent == p:
            break
        p = p.parent
    return None


def _load_module(path: str):
    folder = str(Path(path).parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    name = f"_mp_{Path(path).stem}_{os.urandom(4).hex()}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _user_error(exc: BaseException, path: str) -> dict:
    line = None
    target = os.path.normcase(os.path.abspath(path))
    for frame in traceback.extract_tb(exc.__traceback__):
        if os.path.normcase(os.path.abspath(frame.filename)) == target:
            line = frame.lineno
    if isinstance(exc, SyntaxError) and exc.lineno:
        line = exc.lineno
    message = f"{type(exc).__name__}: {exc}"
    # Tex/MathTex shell out to `latex`; without it Windows only says "file not found".
    frames = traceback.extract_tb(exc.__traceback__)
    if isinstance(exc, (FileNotFoundError, OSError)) and any("tex_file_writing" in f.filename for f in frames):
        message = (
            "LaTeX is not installed. This scene uses Tex or MathTex, which need LaTeX. "
            "Install it from ManimPro (Install LaTeX), or use Text instead."
        )
    return {
        "message": message,
        "latex_missing": message.startswith("LaTeX is not installed"),
        "line": line,
        "traceback": "".join(traceback.format_exception(exc)),
    }


def m_render(params: dict, job_id) -> dict:
    path = params["path"]
    scene_name = params["scene"]
    quality = QUALITY.get(params.get("quality", "preview"), "low_quality")
    still = bool(params.get("still", False))
    media_dir = params["mediaDir"]

    with _InFolder(path):
        module = _load_module(path)
    cls = getattr(module, scene_name, None)
    if cls is None:
        raise RuntimeError(f"Scene {scene_name} was not found in {Path(path).name}.")

    overrides = {
        "quality": quality,
        "media_dir": media_dir,
        "input_file": path,
        "progress_bar": "none",
        "verbosity": "WARNING",
        "preview": False,
        "write_to_movie": not still,
        "save_last_frame": still,
        "disable_caching": bool(params.get("noCache", False)),
    }
    # Frame shape: the short side keeps the quality's height in pixels and
    # 8 scene units, so 16:9 stays exactly Manim's default frame.
    aspect = params.get("aspect")
    if aspect:
        aw, ah = float(aspect[0]), float(aspect[1])
        short = 360 if params.get("quality") == "fast" else QUALITY_HEIGHT.get(quality, 480)
        even = lambda v: int(round(v / 2)) * 2
        ratio = aw / ah
        if aw >= ah:
            overrides["pixel_height"] = short
            overrides["pixel_width"] = even(short * ratio)
        else:
            overrides["pixel_width"] = short
            overrides["pixel_height"] = even(short / ratio)
        wide = 8.0 * 16 / 9
        if params.get("fit", True) and ratio < 16 / 9:
            # Fit: the whole 16:9 layout stays visible; the extra room is above and below.
            overrides["frame_width"] = wide
            overrides["frame_height"] = wide / ratio
        elif aw >= ah:
            overrides["frame_height"] = 8.0
            overrides["frame_width"] = 8.0 * ratio
        else:
            # Fill: the short side is 8 units, so a 16:9 layout is cut at the sides.
            overrides["frame_width"] = 8.0
            overrides["frame_height"] = 8.0 / ratio
    if params.get("quality") == "fast":
        overrides["frame_rate"] = 12
    # A scene that sets self.camera.background_color itself still wins.
    if params.get("background"):
        overrides["background_color"] = params["background"]
    _current_job["id"] = job_id
    cfg = _folder_cfg(path)
    with _InFolder(path), tempconfig(overrides):
        if cfg:
            # The project's own manim.cfg (colors, frame rate, tex template...) first,
            # then ManimPro's settings for where and how big to render.
            try:
                config.digest_file(cfg)
            except Exception as e:  # noqa: BLE001 - a broken cfg should not stop the render
                print(f"Ignoring {cfg}: {e}", file=sys.stderr)
            config.update({k: v for k, v in overrides.items() if k != "quality"})
            config.quality = overrides["quality"]
            for k in ("pixel_width", "pixel_height", "frame_width", "frame_height"):
                if k in overrides:
                    config[k] = overrides[k]
        scene = cls()
        scene.render()
        writer = scene.renderer.file_writer
        if still:
            image = str(writer.image_file_path)
            return {"image": image, "width": config.pixel_width, "height": config.pixel_height}
        video = str(writer.movie_file_path)
    info = probe(video)
    # A project thumbnail (home page) and a per-scene one (project panel).
    result = {"video": video, **info}
    for key in ("thumb", "sceneThumb"):
        if params.get(key):
            try:
                save_thumbnail(video, params[key], info["duration"] * 0.6)
                if key == "sceneThumb":
                    result["thumb"] = params[key]
                    strip = params[key].replace(".jpg", "-strip.jpg")
                    result["stripFrames"] = save_strip(video, strip, info["duration"])
                    result["strip"] = strip
            except Exception as exc:  # noqa: BLE001 - a thumbnail is never worth failing a render
                print(f"thumbnail skipped: {exc}", file=sys.stderr)
    return result


def save_thumbnail(video: str, out: str, at: float) -> None:
    import av

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with av.open(video) as c:
        s = c.streams.video[0]
        c.seek(int(at / s.time_base), stream=s, any_frame=False, backward=True)
        for frame in c.decode(s):
            # Seeking lands on the keyframe before `at`; decode forward to the wanted frame.
            if frame.time is not None and frame.time < at - 0.05:
                continue
            img = frame.to_image()
            img.thumbnail((640, 360))
            img.save(out, quality=82)
            return


STRIP_FRAMES = 12
STRIP_W, STRIP_H = 160, 90


def _tile(img):
    from PIL import ImageOps

    return ImageOps.pad(img, (STRIP_W, STRIP_H), color=(0, 0, 0))


def save_strip(video: str, out: str, duration: float) -> int:
    """Evenly spaced frames side by side in one image, for timeline clip previews."""
    import av
    from PIL import Image

    targets = [duration * (i + 0.5) / STRIP_FRAMES for i in range(STRIP_FRAMES)]
    sheet = Image.new("RGB", (STRIP_W * STRIP_FRAMES, STRIP_H))
    slot = 0
    last = None
    with av.open(video) as c:
        for frame in c.decode(c.streams.video[0]):
            last = frame
            while slot < STRIP_FRAMES and frame.time is not None and frame.time >= targets[slot]:
                sheet.paste(_tile(frame.to_image()), (slot * STRIP_W, 0))
                slot += 1
            if slot >= STRIP_FRAMES:
                break
    # Very short clips can end before the last targets: repeat the final frame.
    while last is not None and slot < STRIP_FRAMES:
        sheet.paste(_tile(last.to_image()), (slot * STRIP_W, 0))
        slot += 1
    sheet.save(out, quality=78)
    return STRIP_FRAMES


def m_audio_info(params: dict) -> dict:
    """Duration plus a peak envelope for drawing the waveform."""
    import av
    import numpy as np

    path = params["path"]
    buckets = int(params.get("buckets", 1200))
    with av.open(path) as c:
        s = c.streams.audio[0]
        duration = float(c.duration / 1_000_000) if c.duration else float(s.duration * s.time_base)
        rate = s.rate or 44100
        total = max(1, int(duration * rate))
        per = max(1, total // buckets)
        peaks = np.zeros(buckets, dtype=np.float32)
        pos = 0
        for frame in c.decode(s):
            data = frame.to_ndarray()
            if data.ndim > 1:
                data = np.abs(data).max(axis=0) if frame.format.is_planar else np.abs(data.reshape(-1, len(frame.layout.channels))).max(axis=1)
            else:
                data = np.abs(data)
            if data.dtype.kind in "iu":
                data = data.astype(np.float32) / float(np.iinfo(data.dtype).max)
            n = len(data)
            idx = np.minimum((np.arange(pos, pos + n) // per), buckets - 1)
            np.maximum.at(peaks, idx, data.astype(np.float32))
            pos += n
    top = float(peaks.max()) or 1.0
    return {"duration": duration, "peaks": [round(float(p) / top, 3) for p in peaks]}


def m_export(params: dict, job_id) -> dict:
    """Put the timeline together into one video (or GIF / image sequence).

    clips: [{path, start, in, out, transition?: {kind: "fade"|"crossfade", duration}}]
    audio: [{path, start, in, out, volume}]
    captions: [{start, end, text}]  burnCaptions: bool  srt: bool
    format: mp4 | webm | mov | gif | png
    """
    clips = sorted(params["clips"], key=lambda c: c["start"])
    out = params["output"]
    fmt = params.get("format", "mp4")
    w, h, fps = int(params["width"]), int(params["height"]), int(params["fps"])
    if not clips:
        raise RuntimeError("The timeline is empty. Add a scene before exporting.")

    def length(c):
        return c["out"] - c["in"]

    total = max([float(params.get("total") or 0)] + [c["start"] + length(c) for c in clips])
    args = [ffmpeg_exe(), "-y", "-hide_banner", "-nostdin"]
    # A black canvas the length of the timeline; every clip is laid over it at its start time,
    # so gaps stay black and transitions can overlap neighbouring clips.
    args += ["-f", "lavfi", "-t", f"{total:.4f}", "-i", f"color=c=black:s={w}x{h}:r={fps}"]
    filters = ["[0:v]format=yuva420p[base]"]
    below = "[base]"
    idx = 1
    for i, c in enumerate(clips):
        prev = clips[i - 1] if i else None
        nxt = clips[i + 1] if i + 1 < len(clips) else None
        L = length(c)
        args += ["-i", c["path"]]
        chain = (
            f"[{idx}:v]trim=start={c['in']:.4f}:end={c['out']:.4f},setpts=PTS-STARTPTS,"
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},format=yuva420p"
        )
        tr = c.get("transition") or {}
        d = min(float(tr.get("duration") or 0), L)
        if tr.get("kind") == "fade" and d > 0:
            chain += f",fade=t=in:st=0:d={d / 2:.4f}"
        elif tr.get("kind") == "crossfade" and d > 0 and prev and abs(prev["start"] + length(prev) - c["start"]) < 0.05:
            # Dissolve in over the previous clip (whose last frame is held underneath).
            chain += f",fade=t=in:st=0:d={d:.4f}:alpha=1"
        ntr = (nxt or {}).get("transition") or {}
        nd = min(float(ntr.get("duration") or 0), length(nxt)) if nxt else 0
        if ntr.get("kind") == "fade" and nd > 0:
            chain += f",fade=t=out:st={max(0.0, L - nd / 2):.4f}:d={nd / 2:.4f}"
        elif ntr.get("kind") == "crossfade" and nd > 0 and abs(c["start"] + L - nxt["start"]) < 0.05:
            chain += f",tpad=stop_mode=clone:stop_duration={nd:.4f}"
        chain += f",setpts=PTS+{c['start']:.4f}/TB[v{idx}]"
        filters.append(chain)
        filters.append(f"{below}[v{idx}]overlay=eof_action=pass:format=auto[o{idx}]")
        below = f"[o{idx}]"
        idx += 1

    # Captions: an .srt beside the video, and optionally burned into the picture.
    captions = [c for c in params.get("captions") or [] if c.get("text", "").strip() and c["end"] > c["start"]]
    srt_text = _srt(captions)
    work = tempfile.mkdtemp(prefix="manimpro-export-")
    finish = f"{below}format=yuv420p"
    if captions and params.get("burnCaptions"):
        Path(work, "captions.srt").write_text(srt_text, encoding="utf-8")
        size = max(14, round(h / 22))
        style = (f"FontName=Arial,FontSize={size},PrimaryColour=&H00FFFFFF,BackColour=&H99000000,"
                 f"BorderStyle=3,Outline=6,Shadow=0,MarginV={round(h / 18)}")
        # libass sizes fonts against a 288-line canvas unless told the real size.
        finish += f",subtitles=captions.srt:original_size={w}x{h}:force_style='{style}'"
    if fmt == "gif":
        gw = min(w, 720)
        finish += (f",fps={min(fps, 15)},scale={gw}:-2:flags=lanczos,split[g1][g2];"
                   f"[g1]palettegen=stats_mode=diff[pal];[g2][pal]paletteuse=dither=bayer:bayer_scale=4")
    graph = ";".join(filters) + ";" + finish + "[out]"

    audio_fmt = fmt in ("mp4", "webm", "mov")
    audio = [a for a in params.get("audio", []) if a["start"] < total] if audio_fmt else []
    amix = []
    for a in audio:
        args.extend(["-i", a["path"]])
        delay = int(round(a["start"] * 1000))
        graph += (
            f";[{idx}:a]atrim=start={a['in']:.4f}:end={a['out']:.4f},asetpts=PTS-STARTPTS,"
            f"volume={float(a.get('volume', 1.0)):.3f},aresample=48000,aformat=channel_layouts=stereo,"
            f"adelay=delays={delay}:all=1[a{idx}]"
        )
        amix.append(f"[a{idx}]")
        idx += 1
    maps = ["-map", "[out]"]
    if amix:
        graph += ";" + "".join(amix) + f"amix=inputs={len(amix)}:normalize=0:duration=longest,atrim=end={total:.4f}[aout]"
        maps += ["-map", "[aout]"]
        maps += {"mp4": ["-c:a", "aac", "-b:a", "192k"], "webm": ["-c:a", "libopus", "-b:a", "160k"],
                 "mov": ["-c:a", "pcm_s16le"]}[fmt]

    crf = int(params.get("crf", 18))
    codec = {
        "mp4": ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        "webm": ["-c:v", "libvpx-vp9", "-crf", str(min(63, crf + 12)), "-b:v", "0", "-row-mt", "1",
                 "-deadline", "good", "-cpu-used", "4", "-pix_fmt", "yuv420p"],
        "mov": ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"],
        "gif": ["-loop", "0"],
        "png": ["-c:v", "png"],
    }[fmt]
    target = out
    if fmt == "png":
        Path(out).mkdir(parents=True, exist_ok=True)
        target = str(Path(out) / "frame_%05d.png")
    args += ["-filter_complex", graph, *maps, *codec, "-t", f"{total:.4f}", "-progress", "pipe:1", "-nostats", target]

    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    # stdin must not be inherited: it is our protocol pipe. cwd holds captions.srt.
    proc = subprocess.Popen(
        args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags, cwd=work
    )
    err_lines: list[str] = []
    threading.Thread(target=lambda: err_lines.extend(proc.stderr), daemon=True).start()
    for line in proc.stdout:
        if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
            try:
                t = int(line.split("=", 1)[1]) / 1_000_000
                event("progress", job=job_id, fraction=min(1.0, t / total) if total else 0)
            except ValueError:
                pass
    code = proc.wait()
    shutil.rmtree(work, ignore_errors=True)
    if code != 0:
        raise RuntimeError("FFmpeg failed:\n" + "".join(err_lines[-20:]))
    srt_path = None
    if captions and params.get("srt") and fmt != "png":
        srt_path = str(Path(out).with_suffix(".srt"))
        Path(srt_path).write_text(srt_text, encoding="utf-8")
    return {"output": out, "duration": total, "srt": srt_path}


def _srt(captions: list[dict]) -> str:
    def ts(t: float) -> str:
        ms = int(round(max(0.0, t) * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

    blocks = []
    for i, c in enumerate(sorted(captions, key=lambda c: c["start"]), 1):
        blocks.append(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text'].strip()}\n")
    return "\n".join(blocks)


# --- Dispatch ----------------------------------------------------------------
QUICK = {"ping": m_ping, "list_scenes": m_list_scenes, "audio_info": m_audio_info}
JOBS = {"render": m_render, "export": m_export}
jobs: "queue.Queue[dict]" = queue.Queue()


def job_loop() -> None:
    while True:
        msg = jobs.get()
        rid, params = msg["id"], msg.get("params") or {}
        try:
            send({"id": rid, "result": JOBS[msg["method"]](params, rid)})
        except BaseException as exc:  # noqa: BLE001 - user code can raise anything
            send({"id": rid, "error": _user_error(exc, params.get("path", ""))})
        finally:
            _current_job["id"] = None


def main() -> None:
    threading.Thread(target=job_loop, daemon=True).start()
    event("ready", manim=manim.__version__)
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        if method in JOBS:
            jobs.put(msg)
        elif method in QUICK:
            try:
                send({"id": msg["id"], "result": QUICK[method](msg.get("params") or {})})
            except Exception as exc:  # noqa: BLE001
                send({"id": msg["id"], "error": {"message": str(exc)}})
        else:
            send({"id": msg.get("id"), "error": {"message": f"Unknown method {method}"}})


if __name__ == "__main__":
    main()
