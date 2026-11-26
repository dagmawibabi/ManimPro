"""Compose ManimPro's royalty-free music library.

Every track is synthesized here from scratch (no samples), so the library is ours to
give away: CC0, free for any video, commercial ones included.

Run with the app's runtime:
    src-tauri/runtime/python/python.exe -I scripts/build-music.py
Writes src-tauri/music/*.mp3 and src-tauri/music/library.json.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src-tauri" / "music"
SR = 44100
rng = np.random.default_rng(1234)


def midi(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    """ADSR envelope over n samples (a, d, r in seconds; s = sustain level)."""
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    S = max(0, n - A - D - R)
    e = np.concatenate([np.linspace(0, 1, A, False), np.linspace(1, s, D, False), np.full(S, s), np.linspace(s, 0, R)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def tone(freq: float, dur: float, harmonics: list[float], detune_cents: float = 0.0) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    f = freq * 2 ** (detune_cents / 1200)
    out = np.zeros_like(t)
    for k, amp in enumerate(harmonics, start=1):
        if amp and f * k < SR / 2.2:
            out += amp * np.sin(2 * np.pi * f * k * t + rng.uniform(0, 2 * np.pi))
    return out


# ---- instruments: each returns a stereo (n, 2) array -------------------------------------------
def pad(freq, dur, bright=0.5):
    h = [1, 0.5 * bright, 0.33 * bright, 0.2 * bright, 0.12 * bright, 0.08 * bright]
    l = tone(freq, dur, h, -6)
    r = tone(freq, dur, h, +6)
    e = env(len(l), min(1.6, dur / 3), 0.5, 0.8, min(1.8, dur / 3))
    return np.stack([l * e, r * e], 1) * 0.16


def epiano(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = tone(freq, dur, [1, 0.35, 0.12, 0.05])
    bell = tone(freq * 4.01, dur, [0.08]) * np.exp(-t * 9)
    trem = 1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)
    e = np.exp(-t * 1.6) * env(n, 0.004, 0.0, 1, min(0.3, dur / 3))
    m = (body + bell) * e * trem
    return np.stack([m, m * 0.92], 1) * 0.22


def pluck(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    m = tone(freq, dur, [1, 0.5, 0.3, 0.18, 0.1, 0.05]) * np.exp(-t * (5 + freq / 220))
    m *= env(n, 0.003, 0, 1, 0.05)
    return np.stack([m * 0.9, m], 1) * 0.2


def bass(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    m = tone(freq, dur, [1, 0.45, 0.15]) * env(n, 0.01, 0.15, 0.7, 0.08)
    return np.stack([m, m], 1) * 0.3


def piano(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    m = tone(freq, dur, [1, 0.6, 0.25, 0.15, 0.08, 0.04]) * np.exp(-t * 2.2) * env(n, 0.003, 0, 1, 0.12)
    return np.stack([m, m * 0.95], 1) * 0.2


def kick(dur=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 45 + 85 * np.exp(-t * 28)
    m = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    return np.stack([m, m], 1) * 0.55


def hat(dur=0.08, level=0.08):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    hp = noise - np.concatenate([[0], noise[:-1]])  # crude high-pass
    m = hp * np.exp(-t * 60) * level
    return np.stack([m * 0.8, m], 1)


def snap(dur=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    m = (rng.standard_normal(n) * 0.6 + np.sin(2 * np.pi * 190 * t) * 0.5) * np.exp(-t * 22)
    return np.stack([m, m * 0.9], 1) * 0.2


# ---- arranging -------------------------------------------------------------------------------
class Song:
    def __init__(self, bpm: float, bars: int):
        self.beat = 60 / bpm
        self.len = int((bars * 4 * self.beat + 4) * SR)
        self.dry = np.zeros((self.len, 2))
        self.wet = np.zeros((self.len, 2))

    def add(self, sig: np.ndarray, at_beat: float, gain=1.0, send=0.3, pan=0.0):
        i = int(at_beat * self.beat * SR)
        if i >= self.len:
            return
        sig = sig[: self.len - i] * gain
        if pan:
            sig = sig * np.array([1 - max(0, pan), 1 + min(0, pan)])
        self.dry[i:i + len(sig)] += sig * (1 - send * 0.5)
        self.wet[i:i + len(sig)] += sig * send

    def render(self, rt=2.2) -> np.ndarray:
        # Reverb: convolve the send bus with a decaying noise burst (different per side).
        n_ir = int(rt * SR)
        t = np.arange(n_ir) / SR
        out = self.dry.copy()
        size = 1 << int(np.ceil(np.log2(self.len + n_ir)))
        for ch in range(2):
            ir = rng.standard_normal(n_ir) * np.exp(-t * 6.9 / rt)
            ir[: int(0.012 * SR)] = 0  # a little pre-delay
            ir /= np.sqrt(np.sum(ir ** 2)) * 1.6
            wet = np.fft.irfft(np.fft.rfft(self.wet[:, ch], size) * np.fft.rfft(ir, size), size)[: self.len]
            out[:, ch] += wet
        # Gentle fade in/out and level.
        f = int(1.5 * SR)
        out[:f] *= np.linspace(0, 1, f)[:, None]
        out[-int(3 * SR):] *= np.linspace(1, 0, int(3 * SR))[:, None]
        peak = np.max(np.abs(out)) or 1
        return np.tanh(out / peak * 1.1) * 0.89


def chord(root: int, kind: str) -> list[int]:
    shapes = {"maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "maj": [0, 4, 7], "min": [0, 3, 7], "sus2": [0, 2, 7], "add9": [0, 4, 7, 14]}
    return [root + i for i in shapes[kind]]


# ---- the tracks --------------------------------------------------------------------------------
def calm_focus():
    s = Song(72, 24)
    prog = [(48, "maj7"), (45, "min7"), (41, "maj7"), (43, "sus2")]
    for bar in range(24):
        root, kind = prog[bar % 4]
        for n in chord(root + 12, kind):
            s.add(pad(midi(n), s.beat * 4.2, 0.4), bar * 4, send=0.6)
        if bar >= 4:
            for k, n in enumerate([0, 7, 12, 16]):
                s.add(epiano(midi(root + 24 + chord(0, kind)[k % len(chord(0, kind))]), s.beat * 1.5), bar * 4 + k, 0.5, send=0.5, pan=0.2 * (k % 2 * 2 - 1))
        s.add(bass(midi(root - 12), s.beat * 3.8), bar * 4, 0.6)
    return s, "Calm focus", "Soft pads and electric piano. Good under explanations.", 72


def curious_mind():
    s = Song(96, 32)
    prog = [(50, "min7"), (55, "maj"), (48, "maj7"), (45, "min7")]
    for bar in range(32):
        root, kind = prog[bar % 4]
        notes = chord(root + 12, kind)
        for step in range(8):
            if bar >= 2:
                s.add(pluck(midi(notes[(step * 3) % len(notes)] + (12 if step % 4 == 3 else 0)), s.beat * 0.6), bar * 4 + step * 0.5, 0.7, send=0.35, pan=0.3 * np.sin(step))
        for n in notes:
            s.add(pad(midi(n), s.beat * 4.1, 0.3), bar * 4, 0.7, send=0.6)
        if bar >= 8:
            s.add(bass(midi(root - 12), s.beat * 1.8), bar * 4, 0.7)
            s.add(bass(midi(root - 12), s.beat * 1.6), bar * 4 + 2.5, 0.6)
    return s, "Curious mind", "Light plucked arpeggios. Questions, setups, first steps.", 96


def discovery():
    s = Song(110, 36)
    prog = [(48, "add9"), (43, "maj"), (45, "min7"), (41, "maj7")]
    for bar in range(36):
        root, kind = prog[bar % 4]
        notes = chord(root + 12, kind)
        for step in range(16):
            s.add(pluck(midi(notes[step % len(notes)] + 12), s.beat * 0.3), bar * 4 + step * 0.25, 0.45 if step % 4 else 0.6, send=0.3)
        for n in notes[:3]:
            s.add(pad(midi(n), s.beat * 4.1, 0.6), bar * 4, 0.6, send=0.5)
        if bar >= 4:
            for b in range(4):
                s.add(kick(), bar * 4 + b, 0.8, send=0.05)
                s.add(hat(), bar * 4 + b + 0.5, 1.0, send=0.1)
            s.add(bass(midi(root - 12), s.beat * 0.9), bar * 4, 0.8)
            s.add(bass(midi(root - 12), s.beat * 0.9), bar * 4 + 1.5, 0.7)
            s.add(bass(midi(root - 5), s.beat * 0.9), bar * 4 + 3, 0.7)
        if bar >= 12 and bar % 2 == 0:
            s.add(snap(), bar * 4 + 1, 0.8, send=0.25)
            s.add(snap(), bar * 4 + 3, 0.8, send=0.25)
    return s, "Discovery", "Upbeat and bright, with a steady beat. Reveals and results.", 110


def deep_thought():
    s = Song(60, 18)
    prog = [(38, "min"), (34, "maj"), (36, "sus2"), (33, "min")]
    for bar in range(18):
        root, kind = prog[bar % 4]
        for n in chord(root + 12, kind):
            s.add(pad(midi(n), s.beat * 4.4, 0.25), bar * 4, 0.9, send=0.7)
        s.add(pad(midi(root), s.beat * 4.4, 0.15), bar * 4, 0.8, send=0.4)
        if bar >= 2:
            line = [7, 3, 5, 2]
            s.add(piano(midi(root + 24 + line[bar % 4]), s.beat * 3), bar * 4 + 1, 0.6, send=0.7)
    return s, "Deep thought", "Slow, minor, spacious. Proofs and big ideas.", 60


def lofi_notes():
    s = Song(84, 28)
    prog = [(53, "maj7"), (52, "min7"), (50, "min7"), (55, "maj")]
    swing = 0.08
    for bar in range(28):
        root, kind = prog[bar % 4]
        for n in chord(root, kind):
            s.add(epiano(midi(n), s.beat * 3.5), bar * 4, 0.55, send=0.35)
            s.add(epiano(midi(n), s.beat * 1.2), bar * 4 + 2.5 + swing, 0.35, send=0.35)
        s.add(bass(midi(root - 24), s.beat * 1.5), bar * 4, 0.8)
        s.add(bass(midi(root - 17), s.beat * 1), bar * 4 + 2.5, 0.6)
        if bar >= 2:
            s.add(kick(), bar * 4, 0.6)
            s.add(kick(), bar * 4 + 2.5, 0.45)
            s.add(snap(), bar * 4 + 1, 0.55, send=0.2)
            s.add(snap(), bar * 4 + 3, 0.55, send=0.2)
            for e in range(8):
                s.add(hat(level=0.06), bar * 4 + e * 0.5 + (swing if e % 2 else 0), 0.9)
    return s, "Lo-fi notes", "Relaxed electric piano with a soft swung beat. Walkthroughs and code.", 84


def bright_idea():
    s = Song(120, 40)
    prog = [(48, "maj"), (55, "maj"), (57, "min"), (53, "maj")]
    melody = [12, 14, 16, 19, 16, 14, 12, 7]
    for bar in range(40):
        root, kind = prog[bar % 4]
        notes = chord(root, kind)
        for b in range(4):
            for n in notes:
                s.add(pluck(midi(n + 12), s.beat * 0.4), bar * 4 + b + 0.5, 0.35, send=0.25)
        if bar >= 8 and bar < 32:
            for i, m in enumerate(melody[:4] if bar % 2 else melody[4:]):
                s.add(piano(midi(48 + m + 12), s.beat * 0.9), bar * 4 + i, 0.5, send=0.4)
        if bar >= 4:
            for b in range(4):
                s.add(kick(), bar * 4 + b, 0.75)
                s.add(hat(), bar * 4 + b + 0.5, 1.1)
            s.add(snap(), bar * 4 + 1, 0.7, send=0.2)
            s.add(snap(), bar * 4 + 3, 0.7, send=0.2)
            s.add(bass(midi(root - 12), s.beat * 0.45), bar * 4, 0.8)
            s.add(bass(midi(root - 12), s.beat * 0.45), bar * 4 + 1.5, 0.7)
            s.add(bass(midi(root - 12), s.beat * 0.45), bar * 4 + 2, 0.7)
            s.add(bass(midi(root), s.beat * 0.45), bar * 4 + 3.5, 0.6)
    return s, "Bright idea", "Cheerful and quick. Intros, titles and endings.", 120


def night_lecture():
    s = Song(66, 20)
    prog = [(45, "min7"), (41, "maj7"), (48, "maj7"), (43, "add9")]
    for bar in range(20):
        root, kind = prog[bar % 4]
        for n in chord(root + 12, kind):
            s.add(pad(midi(n), s.beat * 4.3, 0.2), bar * 4, 0.7, send=0.6)
        notes = chord(root + 24, kind)
        for i, beat in enumerate([0, 1.5, 2.5, 3.25]):
            if (bar + i) % 3 != 2:
                s.add(piano(midi(notes[(bar + i) % len(notes)]), s.beat * 2), bar * 4 + beat, 0.45, send=0.6, pan=0.25 * (i % 2 * 2 - 1))
        s.add(bass(midi(root - 12), s.beat * 3.8), bar * 4, 0.45)
    return s, "Night lecture", "Sparse piano over a warm pad. Calm and thoughtful.", 66


def momentum():
    s = Song(126, 40)
    prog = [(45, "min"), (41, "maj"), (48, "maj"), (43, "maj")]
    for bar in range(40):
        root, kind = prog[bar % 4]
        notes = chord(root + 12, kind)
        for step in range(16):
            s.add(bass(midi(root - 12 + (12 if step % 4 == 2 else 0)), s.beat * 0.22), bar * 4 + step * 0.25, 0.5)
            if bar >= 4:
                s.add(pluck(midi(notes[(step * 2) % len(notes)] + 12), s.beat * 0.25), bar * 4 + step * 0.25, 0.35, send=0.3, pan=0.4 * ((step % 2) * 2 - 1))
        for n in notes:
            s.add(pad(midi(n), s.beat * 4.1, 0.7), bar * 4, 0.55, send=0.5)
        if bar >= 8:
            for b in range(4):
                s.add(kick(), bar * 4 + b, 0.85)
                s.add(hat(level=0.1), bar * 4 + b + 0.5, 1.0)
                s.add(hat(level=0.05), bar * 4 + b + 0.75, 1.0)
            s.add(snap(), bar * 4 + 1, 0.8, send=0.2)
            s.add(snap(), bar * 4 + 3, 0.8, send=0.2)
    return s, "Momentum", "Driving pulse and arpeggios. Montages and fast sequences.", 126


TRACKS = [calm_focus, curious_mind, discovery, deep_thought, lofi_notes, bright_idea, night_lecture, momentum]


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    index = []
    for fn in TRACKS:
        tid = fn.__name__.replace("_", "-")
        song, title, mood, bpm = fn()
        dur = song.len / SR
        index.append({"id": tid, "title": title, "mood": mood, "bpm": bpm, "duration": round(dur, 1), "file": f"{tid}.mp3"})
        if only and tid not in only:
            continue
        audio = song.render()
        pcm = (audio * 32767).astype("<i2").tobytes()
        subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                        "-c:a", "libmp3lame", "-b:a", "160k", "-metadata", f"title={title}", "-metadata", "artist=ManimPro",
                        "-metadata", "copyright=CC0 1.0", str(OUT / f"{tid}.mp3")], input=pcm, check=True)
        print(f"ok  {tid}  {dur:.0f}s")
    (OUT / "library.json").write_text(json.dumps({"license": "CC0 1.0", "tracks": index}, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
