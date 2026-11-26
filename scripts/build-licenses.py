"""Collect the licences of everything ManimPro ships, for Settings > About and THIRD-PARTY-NOTICES.md.

Run with the app's runtime (so the Python packages are the bundled ones):
    src-tauri/runtime/python/python.exe -I scripts/build-licenses.py
Needs pnpm and cargo on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "src" / "lib" / "licenses.json"
OUT_MD = ROOT / "THIRD-PARTY-NOTICES.md"

BUNDLED = [
    {"name": "Python", "version": "3.12", "license": "PSF-2.0", "url": "https://docs.python.org/3/license.html",
     "note": "The embedded interpreter that runs Manim."},
    {"name": "FFmpeg", "version": "(imageio-ffmpeg build)", "license": "GPL-3.0-or-later", "url": "https://ffmpeg.org/legal.html",
     "note": "Used as a separate program for encoding and export. This build includes GPL components (x264); its source is available from ffmpeg.org and the imageio-binaries project."},
    {"name": "TinyTeX / TeX Live", "version": "", "license": "GPL-2.0 and free TeX licences (LPPL and others)", "url": "https://yihui.org/tinytex/",
     "note": "A small LaTeX distribution, run as separate programs for MathTex and Tex. Each TeX package keeps its own free licence."},
    {"name": "Geist", "version": "", "license": "OFL-1.1", "url": "https://github.com/vercel/geist-font", "note": "The heading typeface."},
    {"name": "ManimPro music library", "version": "", "license": "CC0-1.0", "url": "",
     "note": "Original tracks composed by scripts/build-music.py. Free for any use, no credit needed."},
]


def short_license(dist: metadata.Distribution) -> str:
    m = dist.metadata
    expr = m.get("License-Expression")
    if expr:
        return expr
    lic = (m.get("License") or "").strip()
    if lic and "\n" not in lic and len(lic) < 60:
        return lic
    classifiers = [c.split("::")[-1].strip() for c in m.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return " / ".join(classifiers)
    return lic.splitlines()[0][:60] if lic else "See package"


def python_packages() -> list[dict]:
    seen, out = set(), []
    for d in metadata.distributions():
        name = d.metadata.get("Name") or ""
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({"name": name, "version": d.version, "license": short_license(d),
                    "url": d.metadata.get("Home-page") or ""})
    return sorted(out, key=lambda x: x["name"].lower())


def npm_packages() -> list[dict]:
    pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    raw = subprocess.run([pnpm, "licenses", "list", "--prod", "--json"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    out = []
    for lic, pkgs in json.loads(raw).items():
        for p in pkgs:
            out.append({"name": p["name"], "version": ", ".join(p.get("versions", [])), "license": lic, "url": p.get("homepage") or ""})
    return sorted(out, key=lambda x: x["name"].lower())


def rust_crates() -> list[dict]:
    raw = subprocess.run(["cargo", "metadata", "--format-version", "1", "--filter-platform", "x86_64-pc-windows-msvc"],
                         cwd=ROOT / "src-tauri", capture_output=True, text=True, encoding="utf-8", check=True).stdout
    d = json.loads(raw)
    ids = {n["id"] for n in d["resolve"]["nodes"]}
    out = [{"name": p["name"], "version": p["version"], "license": p.get("license") or "See crate",
            "url": p.get("repository") or ""} for p in d["packages"] if p["id"] in ids and p["name"] != "manimpro"]
    return sorted(out, key=lambda x: x["name"].lower())


def main() -> None:
    groups = [
        {"title": "Bundled programs", "items": BUNDLED},
        {"title": "Python packages", "items": python_packages()},
        {"title": "Interface (npm packages)", "items": npm_packages()},
        {"title": "Desktop shell (Rust crates)", "items": rust_crates()},
    ]
    OUT_JSON.write_text(json.dumps({"groups": groups}, indent=1) + "\n", encoding="utf-8")
    lines = ["# Third-party notices", "",
             "ManimPro is built on open-source software. Each component below keeps its own licence; "
             "the full texts ship with the packages themselves (Python packages in their dist-info folders, "
             "npm packages in node_modules, Rust crates on crates.io).", ""]
    for g in groups:
        lines += [f"## {g['title']}", "", "| Component | Version | Licence |", "| --- | --- | --- |"]
        for it in g["items"]:
            name = f"[{it['name']}]({it['url']})" if it.get("url") else it["name"]
            lines.append(f"| {name} | {it.get('version', '')} | {it['license']} |")
        for it in g["items"]:
            if it.get("note"):
                lines.append(f"\n**{it['name']}:** {it['note']}")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"{sum(len(g['items']) for g in groups)} components written")


if __name__ == "__main__":
    main()
