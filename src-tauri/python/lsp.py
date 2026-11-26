"""Python help for the code editor: completions, hover docs, signatures, go-to-definition
and warnings, using jedi (static analysis) and pyflakes. Runs in the render worker on its
own thread so a slow first lookup never holds up renders."""

from __future__ import annotations

import os
import sys
from typing import Any

_project_cache: dict[str, Any] = {}


def _script(params: dict):
    import jedi

    path = params.get("path") or "scene.py"
    root = params.get("project") or os.path.dirname(path)
    project = _project_cache.get(root)
    if project is None:
        extra = [p for p in [os.environ.get("MANIMPRO_PACKAGES"), os.environ.get("MANIMPRO_MANIMGL"),
                             os.path.dirname(os.path.abspath(__file__))] if p and os.path.isdir(p)]
        project = jedi.Project(path=root, added_sys_path=extra, smart_sys_path=True)
        _project_cache[root] = project
    return jedi.Script(params.get("source", ""), path=path, project=project)


def _pos(params: dict) -> tuple[int, int]:
    return int(params["line"]), int(params["column"])  # 1-based line, 0-based column


KIND = {"class": "Class", "function": "Function", "instance": "Variable", "module": "Module",
        "keyword": "Keyword", "statement": "Variable", "param": "Variable", "property": "Property", "path": "File"}


def complete(params: dict) -> dict:
    s = _script(params)
    items = []
    for c in s.complete(*_pos(params))[:150]:
        items.append({"label": c.name, "kind": KIND.get(c.type, "Text"), "detail": c.description[:120]})
    return {"items": items}


def complete_resolve(params: dict) -> dict:
    """Docs for one completion item (asked for lazily, when it is highlighted)."""
    s = _script(params)
    for c in s.complete(*_pos(params)):
        if c.name == params.get("name"):
            sigs = c.get_signatures()
            return {"detail": sigs[0].to_string() if sigs else c.description, "doc": c.docstring(raw=True)[:4000]}
    return {}


def hover(params: dict) -> dict:
    s = _script(params)
    names = s.help(*_pos(params)) or s.infer(*_pos(params))
    for n in names:
        if n.type == "keyword":
            continue
        sigs = n.get_signatures()
        head = sigs[0].to_string() if sigs else f"{n.type} {n.full_name or n.name}"
        doc = n.docstring(raw=True)
        return {"signature": head, "doc": doc[:4000], "module": n.module_name or ""}
    return {}


def signature(params: dict) -> dict:
    s = _script(params)
    sigs = s.get_signatures(*_pos(params))
    out = []
    for sig in sigs[:3]:
        out.append({
            "label": sig.to_string(),
            "params": [p.to_string() for p in sig.params],
            "active": sig.index if sig.index is not None else 0,
            "doc": sig.docstring(raw=True)[:2000],
        })
    return {"signatures": out}


def definition(params: dict) -> dict:
    s = _script(params)
    for d in s.goto(*_pos(params), follow_imports=True, follow_builtin_imports=False):
        if d.module_path and d.line:
            return {"path": str(d.module_path), "line": d.line, "column": d.column, "name": d.name,
                    "inProject": str(d.module_path).lower().startswith(str(params.get("project", "")).lower())}
    return {}


def lint(params: dict) -> dict:
    """pyflakes warnings: undefined names, unused imports, redefinitions. `import *` noise is dropped."""
    from pyflakes import api as flakes
    from pyflakes import reporter

    found: list[dict] = []

    class Collect(reporter.Reporter):
        def __init__(self):
            pass

        def unexpectedError(self, filename, msg):
            pass

        def syntaxError(self, filename, msg, lineno, offset, text):
            pass  # syntax errors come from list_scenes already

        def flake(self, message):
            text = message.message % message.message_args
            kind = type(message).__name__
            if kind == "ImportStarUsed":
                return
            if kind == "ImportStarUsage":
                # `from manim import *`: only a name none of the star-imported modules provide is a mistake.
                name = message.message_args[0]
                if name in _star_names(message.message_args[1]):
                    return
                text = f"undefined name '{name}'"
            elif kind == "ImportStarNotPermitted":
                return
            found.append({"line": message.lineno, "column": getattr(message, "col", 0), "message": text,
                          "severity": "warning" if "imported but unused" in text or "redefinition" in text else "error"
                          if "undefined name" in text else "warning"})

    flakes.check(params.get("source", ""), params.get("path") or "scene.py", Collect())
    return {"problems": found[:200]}


_star_cache: dict[str, set[str]] = {}


def _star_names(modules: str) -> set[str]:
    """Names that `from <module> import *` brings in, for each module listed (comma separated)."""
    import importlib

    out: set[str] = set()
    for mod in (m.strip() for m in modules.split(",")):
        if mod not in _star_cache:
            try:
                m = importlib.import_module(mod)
                names = getattr(m, "__all__", None) or [n for n in dir(m) if not n.startswith("_")]
                _star_cache[mod] = set(names)
            except Exception:  # noqa: BLE001 - unknown module: trust it rather than flag everything
                _star_cache[mod] = {"*"}
        if "*" in _star_cache[mod]:
            return {"*"} | out | _ALL
        out |= _star_cache[mod]
    return out


class _Everything(set):
    def __contains__(self, item):  # noqa: D105
        return True


_ALL = _Everything()


METHODS = {"complete": complete, "complete_resolve": complete_resolve, "hover": hover,
           "signature": signature, "definition": definition, "lint": lint}


def warm_up() -> None:
    """Load Manim into jedi's cache so the first real completion is quick."""
    try:
        src = "from manim import *\nCircle().set_color\n"
        _script({"source": src, "path": "warmup.py"}).complete(2, 18)
    except Exception:  # noqa: BLE001
        pass
