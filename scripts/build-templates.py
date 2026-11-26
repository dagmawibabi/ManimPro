"""Render every template, save gallery thumbnails, and write src/lib/templates.json.

Run with the app's own runtime so results match what users get:
    src-tauri/runtime/python/python.exe -I scripts/build-templates.py [template-id ...]
LaTeX templates are skipped (and keep a placeholder) when LaTeX is not on PATH.
"""

from __future__ import annotations

import ast
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "src-tauri" / "templates"
THUMBS = ROOT / "static" / "templates"
INDEX = ROOT / "src" / "lib" / "templates.json"

# Gallery metadata, in display order. "thumb" names the scene used for the thumbnail.
META = [
    ("blank", "Blank project", "An empty scene to start from.", "Basics", False, None),
    ("calculus-area", "Area under a curve", "Rectangles shrink toward the exact area, then the area function reveals dA/dx = f(x). 3 scenes, inspired by Essence of Calculus.", "Math", False, "RiemannSums"),
    ("fourier-square-wave", "Fourier series: a square wave from sines", "Add sine waves one by one, then watch spinning circles draw the wave. 2 scenes, inspired by \u201cBut what is a Fourier series?\u201d", "Math", False, "AddingSines"),
    ("linear-transform", "Linear transformations", "Basis vectors, a shear, a rotation and the determinant as area. 4 scenes, inspired by Essence of Linear Algebra.", "Math", False, "Determinant"),
    ("euler-formula", "Euler's formula: e^i\u03c0 = \u22121", "Multiplying by i as a quarter turn, then e^i\u03b8 walking the unit circle. 2 scenes.", "Math", False, "AroundTheCircle"),
    ("taylor-series", "Taylor series of sin(x)", "Polynomials of growing degree hug the sine curve over a wider range. 2 scenes.", "Math", False, "Approximations"),
    ("pythagoras", "Pythagorean theorem, by rearrangement", "The same four triangles in one square, arranged two ways. 2 scenes.", "Math", False, "Rearrange"),
    ("bayes-theorem", "Bayes' theorem as areas", "Librarian or farmer? Prior odds and evidence drawn as areas. 4 scenes, inspired by 3Blue1Brown's Bayes video.", "Probability", False, "Evidence"),
    ("central-limit", "Central limit theorem", "Averages of more and more dice pile up into a bell curve. 2 scenes.", "Probability", False, "AddingDice"),
    ("binary-search", "Binary search", "L, M and R pointers halve the range until the target is found. Edit the list and target. 2 scenes.", "Computer science", False, "Search"),
    ("neural-network", "Neural network", "Signals pulse forward through a small network.", "Computer science", False, "NeuralNetwork"),
    ("graph-search", "Breadth-first search", "A search spreads through a graph, layer by layer.", "Computer science", False, "BreadthFirst"),
    ("sorting", "Bubble sort", "Bars compare and swap until the list is sorted.", "Computer science", False, "BubbleSort"),
    ("code-walkthrough", "Code walkthrough", "A code snippet highlighted line by line with notes.", "Computer science", False, "CodeWalkthrough"),
    ("explainer", "Three-part explainer", "Hook, key idea and outro: a ready-made story you can re-word.", "Storytelling", False, "KeyIdea"),
    ("logo-reveal", "Logo reveal", "Tiles fly in, lock into a mark and the brand name writes on.", "Motion design", False, "LogoReveal"),
    ("surface-3d", "3D ripple surface", "A rippling surface with a slowly orbiting camera.", "3D", False, "Ripple3D"),
    ("pendulum", "Damped pendulum", "A simulated pendulum swings down and leaves a fading trail.", "Physics", False, "Pendulum"),
    ("equation-steps", "Solve an equation", "Step-by-step algebra where matching terms glide into place (MathTex).", "Math", True, "SolveEquation"),
]


def scenes_in(path: Path) -> list[str]:
    """Scene classes in file order, including subclasses of other scenes in the file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    names = lambda n: [getattr(b, "id", "") or getattr(b, "attr", "") for b in n.bases]
    found: set[str] = set()
    for _ in range(3):
        for n in classes:
            if any(b.endswith("Scene") or b in found for b in names(n)):
                found.add(n.name)
    return [n.name for n in classes if n.name in found]


def render(path: Path, scene: str, media: Path):
    import importlib.util

    from manim import tempconfig

    spec = importlib.util.spec_from_file_location(f"tpl_{path.parent.name.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempconfig({
        "quality": "low_quality", "media_dir": str(media), "input_file": str(path),
        "progress_bar": "none", "verbosity": "ERROR", "preview": False, "disable_caching": True,
    }):
        s = getattr(module, scene)()
        s.render()
        return Path(s.renderer.file_writer.movie_file_path)


def thumbnail(video: Path, out: Path) -> float:
    import av

    with av.open(str(video)) as c:
        s = c.streams.video[0]
        duration = float(c.duration / 1_000_000)
        target = duration * 0.7
        c.seek(int(target / s.time_base), stream=s, backward=True)
        for frame in c.decode(s):
            # Seeking lands on the keyframe before the target; decode forward to it.
            if frame.time is not None and frame.time < target - 0.05:
                continue
            img = frame.to_image()
            img.thumbnail((640, 360))
            img.save(out, quality=84)
            break
    return duration


def main() -> None:
    only = set(sys.argv[1:])
    has_latex = shutil.which("latex") is not None and shutil.which("dvisvgm") is not None
    THUMBS.mkdir(parents=True, exist_ok=True)
    previous = {t["id"]: t for t in json.loads(INDEX.read_text(encoding="utf-8"))} if INDEX.exists() else {}
    index, failures = [], []
    media = Path(tempfile.mkdtemp(prefix="manimpro-tpl-"))
    for tid, title, desc, category, latex, thumb_scene in META:
        path = TEMPLATES / tid / "scenes.py"
        scenes = scenes_in(path)
        entry = {
            "id": tid, "title": title, "description": desc, "category": category, "latex": latex,
            "scenes": scenes, "thumbnail": previous.get(tid, {}).get("thumbnail"),
            "duration": previous.get(tid, {}).get("duration"),
        }
        index.append(entry)
        if not thumb_scene or (only and tid not in only):
            continue
        if latex and not has_latex:
            print(f"skip  {tid} (needs LaTeX)")
            continue
        try:
            total = 0.0
            for scene in scenes:
                video = render(path, scene, media)
                d = thumbnail(video, THUMBS / f"{tid}.jpg") if scene == thumb_scene else None
                if d is None:
                    import av

                    with av.open(str(video)) as c:
                        d = float(c.duration / 1_000_000)
                total += d
            entry["thumbnail"] = f"/templates/{tid}.jpg"
            entry["duration"] = round(total, 1)
            print(f"ok    {tid}  {total:.1f}s")
        except Exception:  # noqa: BLE001 - report every broken template, keep going
            failures.append(tid)
            print(f"FAIL  {tid}\n{traceback.format_exc()}")
    INDEX.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(media, ignore_errors=True)
    print(f"\n{len(index)} templates indexed; failed: {failures or 'none'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
