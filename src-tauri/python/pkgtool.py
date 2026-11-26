"""Extra Python packages for ManimPro scenes, kept in their own folder.

usage: python pkgtool.py <dir> list
       python pkgtool.py <dir> install <requirement>
       python pkgtool.py <dir> remove <name>

The folder is added to the END of sys.path by the render worker, so the packages
ManimPro ships (manim, numpy...) always win over anything installed here.
Prints one JSON object.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def installed(target: Path) -> list[metadata.Distribution]:
    return list(metadata.distributions(path=[str(target)])) if target.is_dir() else []


def bundled() -> dict[str, str]:
    """Packages in the runtime itself (not the extra folder)."""
    paths = [p for p in sys.path if "site-packages" in p]
    return {norm(d.metadata["Name"]): d.version for d in metadata.distributions(path=paths) if d.metadata.get("Name")}


def cmd_list(target: Path) -> dict:
    pkgs = [{"name": d.metadata["Name"], "version": d.version, "summary": d.metadata.get("Summary") or ""} for d in installed(target)]
    return {"ok": True, "packages": sorted(pkgs, key=lambda p: p["name"].lower()), "dir": str(target)}


def cmd_install(target: Path, spec: str, pinned: bool = True) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._\-\[\],<>=!~ ]{0,120}", spec):
        return {"ok": False, "error": "Enter a package name, optionally with a version (e.g. networkx or scipy>=1.12)."}
    target.mkdir(parents=True, exist_ok=True)
    # Pin what ManimPro already ships so a new package can't pull in a different numpy or manim.
    skip = {"pip", "setuptools", "wheel"}
    pins = "\n".join(f"{n}=={v}" for n, v in bundled().items() if n not in skip) if pinned else ""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(pins)
        constraints = f.name
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", str(target), "--upgrade", "--no-warn-script-location",
         "--disable-pip-version-check", "--no-input", "-c", constraints, *spec.split()],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=0x08000000 if sys.platform == "win32" else 0,
    )
    Path(constraints).unlink(missing_ok=True)
    log = (proc.stdout + proc.stderr).strip().splitlines()
    if proc.returncode != 0:
        errors = [l for l in log if "ERROR" in l] or log[-6:]
        return {"ok": False, "error": "\n".join(errors[-6:]) or "pip failed."}
    return {"ok": True, "log": "\n".join(log[-4:]), **cmd_list(target)}


MANIMGL_GITHUB = "https://github.com/3b1b/manim/archive/refs/heads/master.zip"


def install_manimgl(target: Path) -> dict:
    """The current ManimGL from GitHub: 3Blue1Brown's recent video code needs features newer than the
    PyPI release. Falls back to PyPI if GitHub can't be reached."""
    target.mkdir(parents=True, exist_ok=True)
    flags = 0x08000000 if sys.platform == "win32" else 0
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", str(target), "--upgrade", "--no-warn-script-location",
         "--disable-pip-version-check", "--no-input", MANIMGL_GITHUB, "setuptools<81"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=flags,
    )
    if proc.returncode != 0:
        fallback = cmd_install(target, "manimgl setuptools<81", pinned=False)
        if fallback.get("ok"):
            fallback["note"] = "Installed the PyPI release; GitHub couldn't be reached."
        return fallback
    return {"ok": True, **cmd_list(target)}


def cmd_remove(target: Path, name: str) -> dict:
    want = norm(name)
    root = target.resolve()
    for d in installed(target):
        if norm(d.metadata["Name"]) != want:
            continue
        for f in d.files or []:
            p = (target / f).resolve()
            if root in p.parents and p.is_file():
                p.unlink(missing_ok=True)
        info = Path(d._path)  # the .dist-info folder  # noqa: SLF001
        for p in sorted(info.rglob("*"), reverse=True):
            p.unlink(missing_ok=True) if p.is_file() else p.rmdir()
        info.rmdir()
        # Drop folders the package left empty.
        for p in sorted((x for x in target.rglob("*") if x.is_dir()), key=lambda x: len(x.parts), reverse=True):
            try:
                p.rmdir()
            except OSError:
                pass
        return {"ok": True, **cmd_list(target)}
    return {"ok": False, "error": f"{name} is not installed."}


def main() -> None:
    target = Path(sys.argv[1])
    action = sys.argv[2]
    arg = sys.argv[3] if len(sys.argv) > 3 else ""
    try:
        out = {
            "list": lambda: cmd_list(target),
            "install": lambda: cmd_install(target, arg),
            # A separate world with its own versions (ManimGL): nothing pinned to ManimPro's.
            "install-free": lambda: cmd_install(target, arg, pinned=False),
            "install-manimgl": lambda: install_manimgl(target),
            "remove": lambda: cmd_remove(target, arg),
        }[action]()
    except Exception as e:  # noqa: BLE001 - report to the UI
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
