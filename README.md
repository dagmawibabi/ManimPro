# ManimPro

A Windows desktop app for making and editing [Manim](https://www.manim.community/) videos.
Write a scene, see it render beside your code, arrange scenes on a timeline, export an MP4.
End users install one `.exe`; Python, Manim and FFmpeg ship inside it.

ManimPro is open source: [github.com/dagmawibabi/ManimPro](https://github.com/dagmawibabi/ManimPro).
Website: [manimpro.dagmawi.dev](https://manimpro.dagmawi.dev).

## How it fits together

```
SvelteKit UI (src/)  ──invoke/events──▶  Rust core (src-tauri/src)  ──JSON lines──▶  Python worker
 editor · viewer · timeline              project files, worker supervisor            (src-tauri/python/worker.py)
                                                                                     manim + ffmpeg, kept warm
```

- **Python worker**: a long-lived process that imports manim once, so previews start in about a second.
  Methods: `ping`, `list_scenes`, `render`, `export`. Cancelling a render restarts the process.
- **Runtime**: `src-tauri/runtime/python`, a relocatable CPython 3.12 with `manim` and `imageio-ffmpeg`.
  Dev builds read it from the source tree. Release builds bundle it as a resource (`tauri.bundle.conf.json`).
- **Projects**: a folder of `.py` scene files plus `project.json` (video + audio timeline, render cache index).
  Renders live in `<project>/.manimpro/media`, imported audio in `<project>/assets`. Projects are created
  under `Documents/ManimPro`; recents are kept in the app config folder.
- **Home page** (`src/routes/+page.svelte`): prompt box, template gallery, recent and all projects.
  The editor lives at `src/routes/editor`.
- **Assistants** (`src-tauri/src/agents.rs`): runs the user's own Claude Code, Codex or OpenCode CLI in the
  project folder and streams its JSON events. ManimPro never handles AI credentials: each CLI is the vendor's
  unmodified program, signed in through the vendor's own flow (Sign in opens it in a console window).
- **ManimPro tools for assistants**: `src-tauri/python/mcp_server.py` is an MCP server (render_scene,
  list_scenes, get/add/remove/clear timeline) that each CLI loads for the run. Calls go over a localhost
  socket with a random token (`bridge.rs`) to the running UI, so renders and timeline edits show up live.
- **Voiceovers** (`voice.rs`, `voice.svelte.ts`): ElevenLabs text to speech into `assets/audio`. The key is
  pasted in Settings → Accounts and kept in Windows Credential Manager; requests pass it to curl via stdin.
  Assistants get `list_voices` and `generate_voiceover` tools.
- **Attachments**: files and images added in the composer are copied to `.manimpro/attachments` and listed in
  the prompt (Codex also gets images via `-i`, OpenCode via `-f`).
- **Project tab**: file tree with folders (create, rename, move by dragging, delete to the Recycle Bin), scenes
  and audio as a grid or list.
- **LaTeX** (`latex.rs`): ships inside the installer (`runtime/TinyTeX`, built by `pnpm setup:latex`), so
  `MathTex`/`Tex` work out of the box. If a build lacks it, Install LaTeX in the app downloads the same thing
  into the app data folder. Either way it goes on the render worker's PATH.
- **Templates**: `src-tauri/templates/<id>/scenes.py`. `scripts/build-templates.py` renders them all, writes
  thumbnails to `static/templates/` and the gallery index to `src/lib/templates.json`:
  `src-tauri/runtime/python/python.exe -I scripts/build-templates.py`

## Develop

```powershell
pnpm install
pnpm setup:runtime     # once: downloads CPython 3.12 + manim into src-tauri/runtime (needs uv)
pnpm setup:latex       # once: TinyTeX + Manim's LaTeX packages into src-tauri/runtime/TinyTeX
pnpm app:dev
```

## Build the installer

```powershell
pnpm app:build         # NSIS installer in src-tauri/target/release/bundle/nsis
```

## Shortcuts

| Key | Action |
| --- | --- |
| Ctrl+Enter | Render the scene under the cursor |
| Ctrl+S | Save (and render, if Render on save is on) |
| Space | Play / pause |
| S | Split clip at playhead |
| Delete | Delete selected clip |
| ← / → | Step one frame (Shift: one second) |
| Ctrl+scroll | Zoom timeline |
| Ctrl+E | Export |

## Not yet built

- Text overlays and transitions between clips.
- Code signing and auto-update.
