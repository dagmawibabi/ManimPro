"""Narration that stays in sync with the animation.

    from manim import *
    from manimpro_voice import VoiceoverScene

    class Intro(VoiceoverScene):
        def construct(self):
            circle = Circle()
            with self.voiceover("This is a circle. <bookmark mark='grow'/> Now it grows.") as v:
                self.play(Create(circle), run_time=v.time_until_bookmark("grow"))
                self.play(circle.animate.scale(2), run_time=v.remaining())

Each `with self.voiceover(...)` block speaks its text (ElevenLabs, through ManimPro), puts the
audio into the rendered video at that moment, and waits at the end of the block until the
line has finished, so the picture never runs ahead of the narration. Lines are generated once
and cached in the project's assets/narration folder; editing the text makes a new one.

Without an ElevenLabs key the scene still renders: each line gets an estimated length and no
sound, so timing can be worked out before paying for speech.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from manim import MovingCameraScene, Scene, ThreeDScene

API = "https://api.elevenlabs.io"
WORDS_PER_SECOND = 2.6
_BOOKMARK = re.compile(r"<bookmark\s+mark\s*=\s*['\"]([^'\"]+)['\"]\s*/>")

# Set by the render worker before each render (see worker.py).
_settings: dict = {"project": None, "key": None, "voice": None, "model": "eleven_multilingual_v2"}
# Lines spoken in the current render, for captions: [{start, end, text}] in scene seconds.
spoken: list[dict] = []
warnings: list[str] = []


def configure(project: str | None, key: str | None, voice: str | None, model: str | None) -> None:
    _settings.update(project=project, key=key, voice=voice, model=model or "eleven_multilingual_v2")
    spoken.clear()
    warnings.clear()


class Tracker:
    """Timing for one spoken line: its length and when each bookmark is reached."""

    def __init__(self, scene: Scene, text: str, duration: float, marks: dict[str, float]):
        self.scene = scene
        self.text = text
        self.duration = duration
        self.marks = marks
        self.start = scene.renderer.time

    def elapsed(self) -> float:
        return self.scene.renderer.time - self.start

    def remaining(self, minimum: float = 0.1) -> float:
        """Seconds left until the line finishes (at least `minimum`, so it works as a run_time)."""
        return max(minimum, self.duration - self.elapsed())

    # manim-voiceover style names, so code written for that plugin mostly works.
    def get_remaining_duration(self, buff: float = 0.0) -> float:
        return max(0.0, self.duration - self.elapsed() + buff)

    def time_until_bookmark(self, mark: str, buff: float = 0.0, limit: float | None = None, minimum: float = 0.1) -> float:
        if mark not in self.marks:
            raise KeyError(f"No bookmark named {mark!r} in: {self.text}")
        t = max(minimum, self.marks[mark] - self.elapsed() + buff)
        return min(t, limit) if limit is not None else t


def _split_marks(text: str) -> tuple[str, list[tuple[str, int]]]:
    """Removes <bookmark mark="x"/> tags; returns the plain text and each mark's character offset."""
    plain, marks, last = "", [], 0
    for m in _BOOKMARK.finditer(text):
        plain += text[last:m.start()]
        marks.append((m.group(1), len(plain)))
        last = m.end()
    plain += text[last:]
    return re.sub(r"\s+", " ", plain).strip(), marks


def _cache_dir() -> Path:
    root = Path(_settings["project"] or os.getcwd())
    d = root / "assets" / "narration"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _speak(plain: str, voice: str | None) -> tuple[str | None, float, list[float]]:
    """Audio path (or None), duration, and the start time of every character."""
    voice = voice or _settings["voice"]
    key = _settings["key"]
    if not key or not voice:
        if not warnings:
            warnings.append("Narration is silent: add an ElevenLabs key in Settings > Accounts and pick a voice to hear it.")
        words = max(1, len(plain.split()))
        duration = words / WORDS_PER_SECOND + 0.3
        return None, duration, [duration * i / max(1, len(plain)) for i in range(len(plain) + 1)]

    digest = hashlib.sha1(f"{voice}|{_settings['model']}|{plain}".encode()).hexdigest()[:16]
    audio = _cache_dir() / f"{digest}.mp3"
    meta = audio.with_suffix(".json")
    if not (audio.exists() and meta.exists()):
        body = json.dumps({"text": plain, "model_id": _settings["model"]}).encode()
        req = urllib.request.Request(
            f"{API}/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128",
            data=body,
            headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"ElevenLabs could not speak this line ({e.code}): {detail}") from None
        audio.write_bytes(base64.b64decode(data["audio_base64"]))
        align = data.get("alignment") or {}
        meta.write_text(json.dumps({"text": plain, "starts": align.get("character_start_times_seconds", [])}), encoding="utf-8")
    info = json.loads(meta.read_text(encoding="utf-8"))
    import av

    with av.open(str(audio)) as c:
        duration = float(c.duration / 1_000_000) if c.duration else 0.0
    starts = info.get("starts") or [duration * i / max(1, len(plain)) for i in range(len(plain))]
    return str(audio), duration, list(starts) + [duration]


class VoiceoverMixin:
    @contextmanager
    def voiceover(self, text: str, voice: str | None = None, subcaption: str | None = None):
        """Speak `text` while the block runs; waits at the end until the line is finished."""
        plain, mark_offsets = _split_marks(text)
        path, duration, starts = _speak(plain, voice)
        marks = {name: starts[min(i, len(starts) - 1)] for name, i in mark_offsets}
        tracker = Tracker(self, plain, duration, marks)
        if path:
            self.add_sound(path)
        yield tracker
        left = duration - tracker.elapsed()
        if left > 1 / 60:
            self.wait(left)
        spoken.append({"start": tracker.start, "end": tracker.start + duration, "text": subcaption or plain})


class VoiceoverScene(VoiceoverMixin, Scene):
    pass


class VoiceoverThreeDScene(VoiceoverMixin, ThreeDScene):
    pass


class VoiceoverMovingCameraScene(VoiceoverMixin, MovingCameraScene):
    pass
