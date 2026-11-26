import { api, basename, joinPath, type BridgeCall, type RenderResult, type SceneInfo, type WorkerError } from "./api";
import { clamp } from "./time";
import { settings } from "./settings.svelte";

export type Quality = "fast" | "preview" | "draft" | "high" | "1440p" | "4k";

export type ExportFormat = "mp4" | "webm" | "mov" | "gif" | "png";
export const EXPORT_FORMATS: { id: ExportFormat; label: string; ext: string; note: string }[] = [
  { id: "mp4", label: "MP4 (H.264)", ext: "mp4", note: "Plays everywhere: YouTube, social media, slides." },
  { id: "webm", label: "WebM (VP9)", ext: "webm", note: "Smaller files for the web." },
  { id: "mov", label: "MOV (ProRes 422 HQ)", ext: "mov", note: "Large, high-quality master for editing apps." },
  { id: "gif", label: "GIF", ext: "gif", note: "Silent, looping, up to 720 px wide and 15 fps." },
  { id: "png", label: "PNG image sequence", ext: "", note: "One image per frame, in a folder. No sound." },
];

export type ExportOptions = {
  format?: ExportFormat;
  aspect?: Aspect;
  /** Export just one scene (its sceneKey) instead of the timeline. */
  only?: string | null;
  burnCaptions?: boolean;
  srt?: boolean;
};

export type Render = RenderResult & { quality: Quality; version: number };

export type Clip = {
  id: string;
  file: string; // absolute path of the .py file
  scene: string;
  start: number; // seconds on the timeline
  in: number; // seconds into the source render
  out: number;
  /** How this clip comes in from the one before it. */
  transition?: Transition;
};

export type Transition = { kind: "fade" | "crossfade"; duration: number };

/** One subtitle line on the timeline. */
export type Caption = { id: string; start: number; end: number; text: string };

export type AudioClip = {
  id: string;
  path: string; // absolute path (inside <project>/assets)
  name: string;
  start: number;
  in: number;
  out: number;
  duration: number; // full length of the source file
  volume: number; // 0..2
};

export type Track = "video" | "audio";

export type Job = {
  kind: "render" | "export";
  label: string;
  animations?: number;
  time?: number | null;
  fraction?: number;
};

export type ExportPreset = { id: Quality; label: string; width: number; height: number; fps: number };

export const EXPORT_PRESETS: ExportPreset[] = [
  { id: "draft", label: "720p · 30 fps", width: 1280, height: 720, fps: 30 },
  { id: "high", label: "1080p · 60 fps", width: 1920, height: 1080, fps: 60 },
  { id: "1440p", label: "1440p · 60 fps", width: 2560, height: 1440, fps: 60 },
  { id: "4k", label: "4K · 60 fps", width: 3840, height: 2160, fps: 60 },
];

export type Aspect = "16:9" | "9:16" | "1:1" | "4:5" | "4:3" | "21:9";

export const ASPECTS: { id: Aspect; label: string; w: number; h: number }[] = [
  { id: "16:9", label: "Widescreen", w: 16, h: 9 },
  { id: "9:16", label: "Vertical · Shorts, Reels", w: 9, h: 16 },
  { id: "1:1", label: "Square", w: 1, h: 1 },
  { id: "4:5", label: "Portrait · Feed posts", w: 4, h: 5 },
  { id: "4:3", label: "Classic", w: 4, h: 3 },
  { id: "21:9", label: "Cinematic", w: 21, h: 9 },
];

export const aspectOf = (id: Aspect) => ASPECTS.find((a) => a.id === id) ?? ASPECTS[0];

export const sceneKey = (file: string, scene: string) => `${file}::${scene}`;
const MIN_CLIP = 0.1;
const uid = () => Math.random().toString(36).slice(2, 10);
const clipLen = (c: { in: number; out: number }) => c.out - c.in;

class Studio {
  // Project
  dir = $state<string | null>(null);
  mediaDir = $state("");
  files = $state<string[]>([]);
  folders = $state<string[]>([]);
  audioFiles = $state<string[]>([]);
  projectName = $derived(this.dir ? basename(this.dir) : "");

  // Editor
  activeFile = $state<string | null>(null);
  /** True while a file is being read into the editor (the editor shows a skeleton). */
  loadingFile = $state(false);
  code = $state("");
  savedCode = $state("");
  docVersion = $state(0); // bumps when code is replaced from outside the editor
  cursorLine = $state(1);
  reveal = $state<{ line: number; n: number } | null>(null);
  scenes = $state<Record<string, SceneInfo[]>>({});
  syntaxError = $state<{ message: string; line: number } | null>(null);
  dirty = $derived(this.code !== this.savedCode);

  // Rendering
  renders = $state<Record<string, Render>>({});
  captions = $state<Caption[]>([]);
  /** Non-Python files in the project (data, images, notes). */
  others = $state<string[]>([]);
  /** An image shown over the viewer (a picture from the project, or a quick-look frame). */
  stillImage = $state<string | null>(null);
  stillVersion = $state(0);

  // ------------------------------------------------------------ undo / redo
  // Snapshots of the timeline (clips, audio, captions), taken when an edit settles.
  #undo: string[] = [];
  #redo: string[] = [];
  #lastSnap: string | null = null;
  canUndo = $state(false);
  canRedo = $state(false);

  #snapshot() {
    return JSON.stringify({ clips: this.clips, audio: this.audio, captions: this.captions });
  }

  #record() {
    const now = this.#snapshot();
    if (this.#lastSnap !== null && now !== this.#lastSnap) {
      this.#undo.push(this.#lastSnap);
      if (this.#undo.length > 200) this.#undo.shift();
      this.#redo = [];
    }
    this.#lastSnap = now;
    this.canUndo = this.#undo.length > 0;
    this.canRedo = this.#redo.length > 0;
  }

  #resetHistory() {
    this.#undo = [];
    this.#redo = [];
    this.#lastSnap = this.#snapshot();
    this.canUndo = this.canRedo = false;
  }

  #restore(snap: string) {
    const s = JSON.parse(snap) as { clips: Clip[]; audio: AudioClip[]; captions: Caption[] };
    this.clips = s.clips;
    this.audio = s.audio;
    this.captions = s.captions ?? [];
    this.selectedClip = null;
    this.#lastSnap = snap;
    this.canUndo = this.#undo.length > 0;
    this.canRedo = this.#redo.length > 0;
    this.persist();
  }

  undo() {
    this.#record(); // an edit made in the last moment counts as its own step
    const prev = this.#undo.pop();
    if (!prev) return;
    this.#redo.push(this.#lastSnap!);
    this.#restore(prev);
  }

  redo() {
    const next = this.#redo.pop();
    if (!next) return;
    this.#undo.push(this.#lastSnap!);
    this.#restore(next);
  }
  /** True while an assistant is working in the project (set by the assistant store). */
  locked = $state(false);
  static readonly LOCKED = "The assistant is working on this project. Wait for it to finish, or stop it, first.";

  #assertUnlocked() {
    if (this.locked) throw new Error(Studio.LOCKED);
  }
  /** The project's frame shape: applies to renders, the viewer and export. */
  aspect = $state<Aspect>("16:9");

  get aspectInfo() {
    return aspectOf(this.aspect);
  }

  /** Pixel size for a given short side (e.g. 1080), rounded to even numbers. */
  frameSize(short: number, aspect: Aspect = this.aspect) {
    const { w, h } = aspectOf(aspect);
    const even = (v: number) => Math.round(v / 2) * 2;
    return w >= h ? { width: even((short * w) / h), height: short } : { width: short, height: even((short * h) / w) };
  }

  /** The visible area in scene units (config.frame_width / frame_height) for this project's frame. */
  frameUnits() {
    const { w, h } = this.aspectInfo;
    const r = w / h;
    const wide = (8 * 16) / 9;
    if (settings.value.frameFit === "fit" && r < 16 / 9) return { width: wide, height: wide / r };
    return w >= h ? { width: 8 * r, height: 8 } : { width: 8, height: 8 / r };
  }

  /** Changes the frame shape and re-renders the scenes in use so previews match. */
  async setAspect(a: Aspect) {
    if (a === this.aspect) return;
    this.aspect = a;
    this.persist();
    await this.rerenderAll();
  }

  /** Re-renders the open scene and every scene on the timeline (after a frame change). */
  async rerenderAll() {
    const keys = new Set(this.clips.map((c) => sceneKey(c.file, c.scene)));
    const current = this.activeFile && this.currentScene ? sceneKey(this.activeFile, this.currentScene.name) : null;
    if (current) keys.delete(current);
    if (current) await this.renderCurrent();
    for (const key of keys) {
      const [file, scene] = key.split("::");
      await this.render(file, scene, this.previewQuality);
    }
  }
  /** Preview quality and render-on-save live in Settings so they persist. */
  get previewQuality(): Quality {
    return settings.value.previewQuality;
  }
  set previewQuality(q: Quality) {
    settings.set("previewQuality", q as typeof settings.value.previewQuality);
  }
  get autoRender() {
    return settings.value.renderOnSave;
  }
  set autoRender(v: boolean) {
    settings.set("renderOnSave", v);
  }
  /** Set by the voice store, so assistants can make voiceovers through the bridge. */
  voiceTools: {
    list: () => Promise<unknown[]>;
    generate: (args: Record<string, any>) => Promise<Record<string, unknown>>;
  } | null = null;
  /** Set by the assistant store: shows an outline_video plan in the chat. */
  onOutline: ((plan: { title: string; scenes: { file: string; scene: string; summary: string; seconds?: number }[] }) => void) | null = null;
  job = $state<Job | null>(null);
  error = $state<(WorkerError & { file?: string }) | null>(null);
  worker = $state<{ status: "starting" | "ready" | "offline"; manim?: string; latex?: boolean }>({ status: "starting" });
  logs = $state<string[]>([]);

  // Viewer & timeline
  viewerMode = $state<"source" | "program">("source");
  sourceKey = $state<string | null>(null);
  clips = $state<Clip[]>([]);
  audio = $state<AudioClip[]>([]);
  waveforms = $state<Record<string, number[]>>({});
  /** Length in seconds of each audio file seen (for the audio library). */
  audioDurations = $state<Record<string, number>>({});
  audioMuted = $state(false);
  selectedClip = $state<string | null>(null);
  playhead = $state(0);
  playing = $state(false);
  zoom = $state(settings.value.defaultZoom); // px per second

  videoDuration = $derived(this.clips.reduce((m, c) => Math.max(m, c.start + clipLen(c)), 0));
  timelineDuration = $derived(
    Math.max(this.videoDuration, this.audio.reduce((m, a) => Math.max(m, a.start + clipLen(a)), 0)),
  );
  activeScenes = $derived(this.activeFile ? (this.scenes[this.activeFile] ?? []) : []);
  /** The scene whose class contains the cursor; what Render acts on. */
  currentScene = $derived.by(() => {
    const list = this.activeScenes;
    if (!list.length) return null;
    let pick = list[0];
    for (const s of list) if (s.line <= this.cursorLine) pick = s;
    return pick;
  });

  #chain: Promise<unknown> = Promise.resolve();
  #saveTimer: ReturnType<typeof setTimeout> | undefined;
  #scanTimer: ReturnType<typeof setTimeout> | undefined;
  #started = false;

  /** Subscribes to backend events once per app run. */
  async init() {
    if (this.#started) return;
    this.#started = true;
    await api.onEvent((e) => {
      if (e.event === "ready") {
        this.worker = { ...this.worker, status: "ready", manim: e.manim };
        this.ping(); // refresh LaTeX status and versions from the fresh engine
      }
      else if (e.event === "exit") this.worker = { ...this.worker, status: "offline" };
      else if (e.event === "progress" && this.job) {
        const { animations, time, fraction } = e;
        this.job = { ...this.job, ...(animations !== undefined && { animations }), ...(time !== undefined && { time }), ...(fraction !== undefined && { fraction }) };
      }
    });
    await api.onLog((line) => {
      this.logs.push(line);
      if (this.logs.length > 800) this.logs.splice(0, this.logs.length - 800);
    });
    await api.onBridgeCall((c) => this.handleBridge(c));
    this.ping();
  }

  ping() {
    api
      .call<{ manim: string; latex: boolean }>("ping")
      .then((r) => (this.worker = { status: "ready", manim: r.manim, latex: r.latex }))
      .catch((e: WorkerError) => {
        this.worker = { status: "offline" };
        this.error = e;
      });
  }

  // ---------------------------------------------------------------- project
  async openProject(path?: string) {
    if (this.dirty) await this.save();
    const info = await api.openProject(path);
    this.dir = info.dir;
    this.mediaDir = info.media_dir;
    this.files = info.files;
    this.folders = info.folders;
    this.others = info.others ?? [];
    this.audioFiles = info.audio;
    this.renders = {};
    this.clips = [];
    this.audio = [];
    this.selectedClip = null;
    this.playhead = 0;
    this.playing = false;
    this.sourceKey = null;
    this.error = null;
    this.activeFile = null;
    this.loadTimeline(info.timeline);
    for (const f of info.files) this.scanFile(f);
    if (info.files.length) await this.openFile(info.files[0]);
  }

  /** Picks up files an assistant created or changed, without touching the timeline. */
  async refreshFromDisk() {
    if (!this.dir) return;
    const info = await api.openProject(this.dir);
    this.files = info.files;
    this.folders = info.folders;
    this.others = info.others ?? [];
    this.audioFiles = info.audio;
    for (const f of info.files) await this.scanFile(f);
    if (this.activeFile && info.files.includes(this.activeFile) && !this.dirty) {
      const text = await api.readText(this.activeFile);
      if (text !== this.code) {
        this.code = text;
        this.savedCode = text;
        this.docVersion++;
      }
    } else if (!this.activeFile && info.files.length) {
      await this.openFile(info.files[0]);
    }
  }

  async newFile(name: string, folder?: string) {
    if (!this.dir) return;
    const path = await api.createSceneFile(folder ?? this.dir, name);
    this.files = [...this.files, path].sort();
    await this.scanFile(path);
    await this.openFile(path);
  }

  // ------------------------------------------------------------ scene classes
  /** A file's source: the editor's copy when it is the open file. */
  async sourceOf(file: string) {
    return file === this.activeFile ? this.code : await api.readText(file);
  }

  async writeSource(file: string, text: string) {
    if (file === this.activeFile) {
      this.code = text;
      this.docVersion++;
      await this.save();
    } else {
      await api.writeText(file, text);
    }
    await this.scanFile(file, text);
  }

  /** Lines [start, end) of a top-level class, with its decorators, without trailing blank lines. */
  static classSpan(lines: string[], name: string) {
    let start = lines.findIndex((l) => new RegExp(`^class\\s+${name}\\b`).test(l));
    if (start < 0) return null;
    while (start > 0 && lines[start - 1].startsWith("@")) start--;
    let end = start + 1;
    while (end < lines.length && (lines[end].trim() === "" || /^\s/.test(lines[end]))) end++;
    while (end > start + 1 && lines[end - 1].trim() === "") end--;
    return { start, end };
  }

  /** Removes a scene class from its file, with its clips and render. */
  async deleteScene(file: string, name: string) {
    this.#assertUnlocked();
    const lines = (await this.sourceOf(file)).split("\n");
    const span = Studio.classSpan(lines, name);
    if (!span) throw new Error(`Couldn't find class ${name} in ${basename(file)}.`);
    let end = span.end;
    while (end < lines.length && lines[end].trim() === "") end++;
    lines.splice(span.start, end - span.start);
    await this.writeSource(file, lines.join("\n"));
    const key = sceneKey(file, name);
    this.clips = this.clips.filter((c) => sceneKey(c.file, c.scene) !== key);
    delete this.renders[key];
    if (this.sourceKey === key) this.sourceKey = null;
    this.persist();
  }

  /** Renames a scene class (every whole-word use in its file) and keeps its clips and render. */
  async renameScene(file: string, from: string, to: string) {
    this.#assertUnlocked();
    if (!/^[A-Za-z_]\w*$/.test(to)) throw new Error("A scene name needs letters, digits or _ and can't start with a digit.");
    if (from === to) return;
    if (this.scenes[file]?.some((s) => s.name === to)) throw new Error(`${to} already exists in this file.`);
    const text = (await this.sourceOf(file)).replace(new RegExp(`\\b${from}\\b`, "g"), to);
    await this.writeSource(file, text);
    const a = sceneKey(file, from);
    const b = sceneKey(file, to);
    for (const c of this.clips) if (sceneKey(c.file, c.scene) === a) c.scene = to;
    if (this.renders[a]) {
      this.renders[b] = this.renders[a];
      delete this.renders[a];
    }
    if (this.sourceKey === a) this.sourceKey = b;
    this.persist();
  }

  /** Copies a scene class to the end of its file under a new name. */
  async duplicateScene(file: string, name: string) {
    const text = await this.sourceOf(file);
    const lines = text.split("\n");
    const span = Studio.classSpan(lines, name);
    if (!span) throw new Error(`Couldn't find class ${name} in ${basename(file)}.`);
    const taken = new Set((this.scenes[file] ?? []).map((s) => s.name));
    let copy = `${name}Copy`;
    for (let i = 2; taken.has(copy); i++) copy = `${name}Copy${i}`;
    const block = lines.slice(span.start, span.end).join("\n").replace(new RegExp(`^(class\\s+)${name}\\b`, "m"), `$1${copy}`);
    await this.writeSource(file, `${text.replace(/\s*$/, "")}\n\n\n${block}\n`);
    return copy;
  }

  /** Copies a scene file next to the original ("name-copy.py"). */
  async duplicateFile(path: string) {
    if (!this.dir) return;
    if (this.dirty) await this.save();
    const text = await api.readText(path);
    const folder = path.slice(0, path.lastIndexOf("\\"));
    const copy = await api.createSceneFile(folder, `${basename(path).replace(/\.py$/i, "")}-copy`);
    await api.writeText(copy, text);
    await this.refreshFromDisk();
    await this.scanFile(copy);
    return copy;
  }

  // ------------------------------------------------------------ file system
  async newFolder(parent: string, name: string) {
    if (!this.dir) return;
    const path = await api.createFolder(this.dir, parent, name);
    this.folders = [...this.folders, path].sort();
    return path;
  }

  async renamePath(path: string, name: string) {
    if (!this.dir) return;
    this.#assertUnlocked();
    if (this.dirty) await this.save();
    const to = await api.renamePath(this.dir, path, name);
    this.pathChanged(path, to);
    await this.refreshFromDisk();
  }

  async movePath(path: string, into: string) {
    if (!this.dir) return;
    this.#assertUnlocked();
    if (this.dirty) await this.save();
    const to = await api.movePath(this.dir, path, into);
    this.pathChanged(path, to);
    await this.refreshFromDisk();
  }

  async trashPath(path: string) {
    if (!this.dir) return;
    this.#assertUnlocked();
    await api.trashPath(this.dir, path);
    const gone = (p: string) => p === path || p.toLowerCase().startsWith(path.toLowerCase() + "\\");
    if (this.activeFile && gone(this.activeFile)) {
      this.activeFile = null;
      this.code = this.savedCode = "";
      this.docVersion++;
    }
    await this.refreshFromDisk();
  }

  /** A file or folder moved: point clips, renders and the editor at the new place. */
  pathChanged(from: string, to: string) {
    const lower = from.toLowerCase();
    const map = (p: string) =>
      p.toLowerCase() === lower || p.toLowerCase().startsWith(lower + "\\") ? to + p.slice(from.length) : p;
    for (const c of this.clips) c.file = map(c.file);
    for (const a of this.audio) a.path = map(a.path);
    this.renders = Object.fromEntries(Object.entries(this.renders).map(([k, r]) => [map(k), r]));
    this.scenes = Object.fromEntries(Object.entries(this.scenes).map(([k, v]) => [map(k), v]));
    if (this.activeFile) this.activeFile = map(this.activeFile);
    if (this.sourceKey) this.sourceKey = map(this.sourceKey);
    this.persist();
  }

  /** Points an audio clip at a new file (e.g. a regenerated voiceover), keeping its position. */
  async replaceAudioSource(clipId: string, path: string) {
    const clip = this.audio.find((a) => a.id === clipId);
    if (!clip) return;
    const info = await api.call<{ duration: number; peaks: number[] }>("audio_info", { path, buckets: 1600 });
    this.waveforms[path] = info.peaks;
    this.audioDurations[path] = info.duration;
    clip.path = path;
    clip.name = basename(path);
    clip.duration = info.duration;
    clip.in = 0;
    clip.out = info.duration;
    this.resolveOverlaps("audio", clip.id);
  }

  /** Adds an audio file that is already in the project (e.g. a generated voiceover). */
  async placeAudio(path: string, at?: number) {
    const info = await api.call<{ duration: number; peaks: number[] }>("audio_info", { path, buckets: 1600 });
    this.waveforms[path] = info.peaks;
    const clip: AudioClip = {
      id: uid(),
      path,
      name: basename(path),
      start: at ?? this.playhead,
      in: 0,
      out: info.duration,
      duration: info.duration,
      volume: 1,
    };
    this.audio.push(clip);
    this.resolveOverlaps("audio", clip.id);
    this.selectedClip = clip.id;
    this.viewerMode = "program";
    this.persist();
    return clip;
  }

  async openFile(path: string) {
    if (this.dirty) await this.save();
    this.loadingFile = true;
    let text: string;
    try {
      text = await api.readText(path);
    } finally {
      this.loadingFile = false;
    }
    this.activeFile = path;
    this.code = text;
    this.savedCode = text;
    this.docVersion++;
    this.syntaxError = null;
    this.cursorLine = 1;
    if (/\.py$/i.test(path)) await this.scanFile(path, text);
  }

  /** Copies files into the project (a folder in it, or its root) and lists them. */
  async importFiles(sources: string[], folder = this.dir!) {
    if (!this.dir) return [];
    const out = await api.importFiles(this.dir, folder, sources);
    await this.refreshFromDisk();
    return out;
  }

  async save() {
    if (!this.activeFile) return;
    const text = this.code;
    await api.writeText(this.activeFile, text);
    this.savedCode = text;
  }

  #autoSaveTimer: ReturnType<typeof setTimeout> | undefined;

  /** Re-reads scene classes as the user types (debounced). */
  codeChanged(text: string) {
    this.code = text;
    if (settings.value.autoSave) {
      clearTimeout(this.#autoSaveTimer);
      this.#autoSaveTimer = setTimeout(() => this.dirty && this.save(), 1000);
    }
    clearTimeout(this.#scanTimer);
    const file = this.activeFile;
    if (file) this.#scanTimer = setTimeout(() => this.scanFile(file, text), 250);
  }

  async scanFile(path: string, source?: string) {
    try {
      const r = await api.call<{ scenes: SceneInfo[]; error?: { message: string; line: number } }>("list_scenes", {
        path,
        source: source ?? null,
      });
      this.scenes[path] = r.scenes.length || !r.error ? r.scenes : (this.scenes[path] ?? []);
      if (path === this.activeFile) this.syntaxError = r.error ?? null;
    } catch {
      /* worker offline; status bar already says so */
    }
  }

  goToLine(line: number) {
    this.reveal = { line, n: (this.reveal?.n ?? 0) + 1 };
  }

  resolveFile(name: string): string | null {
    if (!this.dir) return null;
    const n = name.replace(/\//g, "\\").toLowerCase();
    return (
      this.files.find((f) => f.toLowerCase() === n) ??
      this.files.find((f) => basename(f).toLowerCase() === basename(n)) ??
      null
    );
  }

  // -------------------------------------------------------------- rendering
  /** Save, then render the scene under the cursor (or the given one). */
  async renderCurrent(scene?: string) {
    if (!this.activeFile) return;
    await this.save();
    const name = scene ?? this.currentScene?.name;
    if (!name) {
      this.error = { message: "This file has no Scene classes yet. Add one like `class MyScene(Scene):`." };
      return;
    }
    await this.render(this.activeFile, name, this.previewQuality, true);
  }

  render(file: string, scene: string, quality: Quality, show = false, aspect: Aspect = this.aspect): Promise<Render | null> {
    const run = async () => {
      const key = sceneKey(file, scene);
      const shape = aspectOf(aspect);
      const own = aspect === this.aspect;
      this.job = { kind: "render", label: scene };
      this.error = null;
      try {
        const r = await api.call<RenderResult>("render", {
          path: file,
          scene,
          quality,
          mediaDir: own ? this.mediaDir : joinPath(this.mediaDir, `frame-${shape.w}x${shape.h}`),
          thumb: own && this.dir ? joinPath(this.dir, ".manimpro\\thumb.jpg") : null,
          sceneThumb: own ? joinPath(this.mediaDir, `thumbs\\${basename(file).replace(/\.py$/i, "")}-${scene}.jpg`) : null,
          noCache: settings.value.disableCache,
          aspect: [shape.w, shape.h],
          fit: settings.value.frameFit === "fit",
          background: settings.value.backgroundColor !== "#000000" ? settings.value.backgroundColor : null,
        });
        const render: Render = { ...r, quality, version: Date.now() };
        // Another frame shape (an export) is a one-off: the previews stay as they are.
        if (!own) return render;
        this.renders[key] = render;
        this.fitClipsToRender(key, render.duration);
        if (show) {
          this.sourceKey = key;
          if (!this.playing) this.viewerMode = "source";
        }
        this.persist();
        return render;
      } catch (e) {
        const err = e as WorkerError;
        if (!err.cancelled) this.error = { ...err, file };
        return null;
      } finally {
        this.job = null;
      }
    };
    const p = this.#chain.then(run, run);
    this.#chain = p;
    return p;
  }

  async cancel() {
    this.job = null;
    await api.restartWorker();
    this.worker = { ...this.worker, status: "starting" };
  }

  showSource(key: string) {
    this.stillImage = null;
    this.sourceKey = key;
    this.viewerMode = "source";
    this.playing = false;
  }

  // --------------------------------------------------------------- timeline
  async addToTimeline(file: string, scene: string, at?: number) {
    const key = sceneKey(file, scene);
    let r: Render | null | undefined = this.renders[key];
    if (!r) r = await this.render(file, scene, this.previewQuality);
    if (!r) return null;
    const clip: Clip = { id: uid(), file, scene, start: at ?? this.videoDuration, in: 0, out: r.duration };
    this.clips.push(clip);
    this.resolveOverlaps("video", clip.id);
    this.selectedClip = clip.id;
    this.viewerMode = "program";
    this.persist();
    return clip;
  }

  /** Appends every scene of the project to the video track, file by file, in code order. */
  async addAllScenes() {
    let added = 0;
    for (const file of [...this.files].sort((a, b) => a.localeCompare(b))) {
      for (const s of this.scenes[file] ?? []) {
        if (await this.addToTimeline(file, s.name)) added++;
      }
    }
    return added;
  }

  async addAudio(source: string, at?: number) {
    if (!this.dir) return;
    const path = await api.importMedia(this.dir, source);
    if (!this.audioFiles.includes(path)) this.audioFiles = [...this.audioFiles, path].sort();
    const info = await api.call<{ duration: number; peaks: number[] }>("audio_info", { path, buckets: 1600 });
    this.waveforms[path] = info.peaks;
    const clip: AudioClip = {
      id: uid(),
      path,
      name: basename(path),
      start: at ?? this.playhead,
      in: 0,
      out: info.duration,
      duration: info.duration,
      volume: 1,
    };
    this.audio.push(clip);
    this.resolveOverlaps("audio", clip.id);
    this.selectedClip = clip.id;
    this.viewerMode = "program";
    this.persist();
  }

  async loadWaveform(path: string) {
    if (this.waveforms[path]) return;
    try {
      const info = await api.call<{ duration: number; peaks: number[] }>("audio_info", { path, buckets: 1600 });
      this.waveforms[path] = info.peaks;
      this.audioDurations[path] = info.duration;
    } catch {
      this.waveforms[path] = [];
    }
  }

  track(kind: Track): (Clip | AudioClip)[] {
    return kind === "video" ? this.clips : this.audio;
  }

  find(id: string | null): { clip: Clip | AudioClip; kind: Track } | null {
    if (!id) return null;
    const v = this.clips.find((c) => c.id === id);
    if (v) return { clip: v, kind: "video" };
    const a = this.audio.find((c) => c.id === id);
    return a ? { clip: a, kind: "audio" } : null;
  }

  sourceLength(clip: Clip | AudioClip): number {
    if ("path" in clip) return clip.duration;
    return this.renders[sceneKey(clip.file, clip.scene)]?.duration ?? clip.out;
  }

  moveClip(id: string, start: number) {
    const f = this.find(id);
    if (f) f.clip.start = Math.max(0, start);
  }

  trimClip(id: string, edge: "in" | "out", value: number) {
    const f = this.find(id);
    if (!f) return;
    const c = f.clip;
    if (edge === "in") {
      const next = clamp(value, Math.max(0, c.in - c.start), c.out - MIN_CLIP);
      c.start += next - c.in;
      c.in = next;
    } else {
      c.out = clamp(value, c.in + MIN_CLIP, this.sourceLength(c));
    }
  }

  /** After a drag: keep clip order by start and push later clips so nothing overlaps. */
  resolveOverlaps(kind: Track, priorityId?: string) {
    const list = this.track(kind);
    list.sort((a, b) => a.start - b.start || (a.id === priorityId ? -1 : 1));
    let end = 0;
    for (const c of list) {
      if (c.start < end) c.start = end;
      end = c.start + clipLen(c);
    }
    this.persist();
  }

  splitAtPlayhead() {
    const t = this.playhead;
    const sel = this.find(this.selectedClip);
    const inside = (c: Clip | AudioClip) => t > c.start + MIN_CLIP && t < c.start + clipLen(c) - MIN_CLIP;
    const target =
      sel && inside(sel.clip)
        ? sel
        : (() => {
            const v = this.clips.find(inside);
            if (v) return { clip: v, kind: "video" as Track };
            const a = this.audio.find(inside);
            return a ? { clip: a, kind: "audio" as Track } : null;
          })();
    if (!target) return;
    const c = target.clip;
    const cut = c.in + (t - c.start);
    const right = { ...c, id: uid(), start: t, in: cut };
    c.out = cut;
    const list = this.track(target.kind) as (Clip | AudioClip)[];
    list.splice(list.indexOf(c) + 1, 0, right);
    this.selectedClip = right.id;
    this.persist();
  }

  /** True when the playhead sits inside the clip, away from its edges. */
  playheadInside(id: string) {
    const c = this.find(id)?.clip;
    return !!c && this.playhead > c.start + MIN_CLIP && this.playhead < c.start + clipLen(c) - MIN_CLIP;
  }

  /** Cut away the part of a clip before (start) or after (end) the playhead. */
  trimToPlayhead(id: string, edge: "start" | "end") {
    const c = this.find(id)?.clip;
    if (!c || !this.playheadInside(id)) return;
    const t = this.playhead;
    if (edge === "start") {
      c.in += t - c.start;
      c.start = t;
    } else {
      c.out = c.in + (t - c.start);
    }
    this.persist();
  }

  /** Copy a clip and place the copy right after the original. */
  duplicateClip(id: string) {
    const f = this.find(id);
    if (!f) return;
    const copy = { ...f.clip, id: uid(), start: f.clip.start + clipLen(f.clip) };
    (this.track(f.kind) as (Clip | AudioClip)[]).push(copy);
    this.resolveOverlaps(f.kind, copy.id);
    this.selectedClip = copy.id;
  }

  deleteSelected() {
    if (this.captions.some((c) => c.id === this.selectedClip)) {
      this.removeCaption(this.selectedClip!);
      this.selectedClip = null;
      return;
    }
    for (const list of [this.clips, this.audio] as (Clip | AudioClip)[][]) {
      const i = list.findIndex((c) => c.id === this.selectedClip);
      if (i >= 0) {
        const [gone] = list.splice(i, 1);
        if (settings.value.rippleDelete && list === this.clips) {
          const len = clipLen(gone);
          for (const c of this.clips) if (c.start >= gone.start) c.start = Math.max(0, c.start - len);
        }
        this.selectedClip = null;
        this.persist();
        return;
      }
    }
  }

  // ------------------------------------------------------------ transitions
  setTransition(id: string, t: Transition | null) {
    const c = this.clips.find((x) => x.id === id);
    if (!c) return;
    if (t) c.transition = t;
    else delete c.transition;
    this.persist();
  }

  /** The clip that plays right before this one (by start time), if any. */
  clipBefore(id: string) {
    const sorted = [...this.clips].sort((a, b) => a.start - b.start);
    const i = sorted.findIndex((c) => c.id === id);
    return i > 0 ? sorted[i - 1] : undefined;
  }

  // ------------------------------------------------------------ captions
  captionAt(t: number) {
    return this.captions.find((c) => t >= c.start && t < c.end);
  }

  setCaptions(list: Caption[]) {
    this.captions = [...list].sort((a, b) => a.start - b.start);
    this.persist();
  }

  addCaption(start: number, text = "New caption", length = 2.5) {
    const c: Caption = { id: uid(), start, end: start + length, text };
    this.setCaptions([...this.captions, c]);
    return c;
  }

  updateCaption(id: string, patch: Partial<Omit<Caption, "id">>) {
    const c = this.captions.find((x) => x.id === id);
    if (!c) return;
    Object.assign(c, patch);
    if (c.end < c.start + 0.2) c.end = c.start + 0.2;
    this.setCaptions(this.captions);
  }

  removeCaption(id: string) {
    this.setCaptions(this.captions.filter((c) => c.id !== id));
  }

  // ------------------------------------------------------------ quick look
  /** Renders only the last frame of the scene under the cursor (skips the animation), for a fast check. */
  async quickLook() {
    const file = this.activeFile;
    const scene = this.currentScene?.name;
    if (!file || !scene) return;
    const run = async () => {
      this.job = { kind: "render", label: `${scene} (last frame)` };
      this.error = null;
      try {
        const shape = this.aspectInfo;
        const r = await api.call<{ image: string }>("render", {
          path: file,
          scene,
          quality: "draft",
          still: true,
          mediaDir: this.mediaDir,
          noCache: true,
          aspect: [shape.w, shape.h],
          fit: settings.value.frameFit === "fit",
          background: settings.value.backgroundColor !== "#000000" ? settings.value.backgroundColor : null,
        });
        this.stillImage = r.image;
        this.stillVersion = Date.now();
      } catch (e) {
        const err = e as WorkerError;
        if (!err.cancelled) this.error = { ...err, file };
      } finally {
        this.job = null;
      }
    };
    const p = this.#chain.then(run, run);
    this.#chain = p;
    return p;
  }

  /** Takes every clip of one audio file off the timeline (the file stays). */
  removeAudioClips(path: string) {
    this.audio = this.audio.filter((a) => a.path !== path);
    this.persist();
  }

  setVolume(id: string, volume: number) {
    const a = this.audio.find((c) => c.id === id);
    if (a) {
      a.volume = clamp(volume, 0, 2);
      this.persist();
    }
  }

  clipAt(t: number) {
    return this.clips.find((c) => t >= c.start && t < c.start + clipLen(c));
  }

  fitClipsToRender(key: string, duration: number) {
    for (const c of this.clips) {
      if (sceneKey(c.file, c.scene) !== key) continue;
      c.out = Math.min(c.out, duration);
      c.in = Math.min(c.in, c.out - MIN_CLIP);
    }
  }

  // ----------------------------------------------------------------- export
  async exportVideo(preset: ExportPreset, output: string, onStage: (s: string) => void, opts: ExportOptions = {}) {
    const aspect = opts.aspect ?? this.aspect;
    const only = opts.only ?? null;
    const keys = only ? [only] : [...new Set(this.clips.map((c) => sceneKey(c.file, c.scene)))];
    const finals: Record<string, Render> = {};
    for (const [i, key] of keys.entries()) {
      const [file, scene] = key.split("::");
      onStage(`Rendering ${scene} (${i + 1} of ${keys.length})`);
      const r = await this.render(file, scene, preset.id, false, aspect);
      if (!r) throw new Error(this.error?.message ?? `Rendering ${scene} failed.`);
      finals[key] = r;
    }
    onStage("Encoding video");
    const run = async () => {
      this.job = { kind: "export", label: "Export", fraction: 0 };
      try {
        const single = only ? finals[only] : null;
        return await api.call<{ output: string; srt: string | null }>("export", {
          clips: single
            ? [{ path: single.video, start: 0, in: 0, out: single.duration }]
            : this.clips.map((c) => ({
                path: finals[sceneKey(c.file, c.scene)].video,
                start: c.start,
                in: c.in,
                out: c.out,
                transition: c.transition ?? null,
              })),
          audio:
            single || this.audioMuted
              ? []
              : this.audio.map((a) => ({ path: a.path, start: a.start, in: a.in, out: a.out, volume: a.volume })),
          total: single ? single.duration : this.timelineDuration,
          format: opts.format ?? "mp4",
          captions: single ? [] : this.captions,
          burnCaptions: !!opts.burnCaptions,
          srt: opts.srt ?? true,
          output,
          crf: settings.crf(),
          ...this.frameSize(preset.height, aspect),
          fps: preset.fps,
        });
      } finally {
        this.job = null;
      }
    };
    const p = this.#chain.then(run, run);
    this.#chain = p;
    return p;
  }

  // ------------------------------------------------- assistant tool calls
  async handleBridge(c: BridgeCall) {
    const reply = (result: unknown) => api.bridgeReply(c.call, result);
    try {
      if (!this.dir) return reply({ ok: false, error: "No project is open in ManimPro." });
      if (c.tool !== "get_timeline") await this.refreshFromDisk();
      switch (c.tool) {
        case "list_scenes": {
          return reply({
            ok: true,
            latex_installed: !!this.worker.latex,
            files: this.files.map((f) => ({
              file: basename(f),
              scenes: (this.scenes[f] ?? []).map((s) => {
                const r = this.renders[sceneKey(f, s.name)];
                return { name: s.name, line: s.line, rendered: !!r, duration: r?.duration ?? null };
              }),
            })),
          });
        }
        case "render_scene": {
          const file = this.resolveFile(String(c.args.file ?? ""));
          if (!file) return reply({ ok: false, error: `No file named ${c.args.file} in the project.` });
          const r = await this.render(file, String(c.args.scene), this.previewQuality, true);
          if (r) return reply({ ok: true, duration: r.duration, resolution: `${r.width}x${r.height}` });
          const e = this.error;
          const needsLatex = /latex|dvisvgm/i.test(e?.message ?? "") && !this.worker.latex;
          return reply({
            ok: false,
            error: e?.message ?? "Render failed.",
            line: e?.line ?? null,
            traceback_tail: e?.traceback?.split("\n").slice(-12).join("\n"),
            hint: needsLatex
              ? "LaTeX is not installed. Use Text instead of Tex/MathTex, or ask the user to install LaTeX from ManimPro's status bar."
              : undefined,
          });
        }
        case "view_scene": {
          const file = this.resolveFile(String(c.args.file ?? ""));
          if (!file) return reply({ ok: false, error: `No file named ${c.args.file} in the project.` });
          const scene = String(c.args.scene);
          if (!this.scenes[file]?.some((s) => s.name === scene)) await this.scanFile(file);
          let r: Render | null | undefined = c.args.rerender ? null : this.renders[sceneKey(file, scene)];
          if (!r) r = await this.render(file, scene, this.previewQuality, true);
          if (!r) return reply({ ok: false, error: this.error?.message ?? "Render failed.", line: this.error?.line ?? null });
          return reply({ ok: true, video: r.video, duration: r.duration, resolution: `${r.width}x${r.height}` });
        }
        case "view_timeline": {
          if (!this.clips.length) return reply({ ok: false, error: "The timeline is empty. Call arrange_timeline or add_to_timeline first." });
          const segments = [];
          for (const cl of [...this.clips].sort((a, b) => a.start - b.start)) {
            let r: Render | null | undefined = this.renders[sceneKey(cl.file, cl.scene)];
            if (!r) r = await this.render(cl.file, cl.scene, this.previewQuality);
            if (r) segments.push({ start: cl.start, end: cl.start + clipLen(cl), in: cl.in, video: r.video, scene: cl.scene });
          }
          return reply({ ok: true, duration: this.timelineDuration, segments });
        }
        case "get_timeline":
          return reply({
            ok: true,
            video: this.clips.map((cl, i) => ({ index: i, file: basename(cl.file), scene: cl.scene, start: cl.start, in: cl.in, out: cl.out })),
            audio: this.audio.map((a) => ({ name: a.name, start: a.start, in: a.in, out: a.out, volume: a.volume })),
            duration: this.timelineDuration,
          });
        case "add_to_timeline": {
          const file = this.resolveFile(String(c.args.file ?? ""));
          if (!file) return reply({ ok: false, error: `No file named ${c.args.file} in the project.` });
          const clip = await this.addToTimeline(file, String(c.args.scene), typeof c.args.start === "number" ? c.args.start : undefined);
          if (!clip) return reply({ ok: false, error: this.error?.message ?? "Render failed.", line: this.error?.line ?? null });
          return reply({ ok: true, index: this.clips.indexOf(clip), start: clip.start, duration: clipLen(clip) });
        }
        case "remove_from_timeline": {
          const i = Number(c.args.index);
          if (!(i >= 0 && i < this.clips.length)) return reply({ ok: false, error: "No clip at that index." });
          this.clips.splice(i, 1);
          this.persist();
          return reply({ ok: true });
        }
        case "clear_timeline":
          this.clips = [];
          this.persist();
          return reply({ ok: true });
        case "list_voices":
          if (!this.voiceTools) return reply({ ok: false, error: "Voiceovers are not available." });
          return reply({ ok: true, voices: await this.voiceTools.list() });
        case "generate_voiceover":
          if (!this.voiceTools) return reply({ ok: false, error: "Voiceovers are not available." });
          return reply({ ok: true, ...(await this.voiceTools.generate(c.args)) });
        case "outline_video": {
          const scenes = Array.isArray(c.args.scenes) ? c.args.scenes : [];
          this.onOutline?.({ title: String(c.args.title ?? "Video plan"), scenes });
          return reply({ ok: true, shown_to_user: true, scenes: scenes.length });
        }
        case "arrange_timeline": {
          const list = Array.isArray(c.args.scenes) ? c.args.scenes : [];
          const gap = Math.max(0, Number(c.args.gap) || 0);
          const resolved: { file: string; scene: string }[] = [];
          for (const item of list) {
            const file = this.resolveFile(String(item.file ?? ""));
            if (!file) return reply({ ok: false, error: `No file named ${item.file} in the project.` });
            resolved.push({ file, scene: String(item.scene) });
          }
          // Render everything first so a failure leaves the old timeline alone.
          for (const r of resolved) {
            if (this.renders[sceneKey(r.file, r.scene)]) continue;
            const out = await this.render(r.file, r.scene, this.previewQuality);
            if (!out) {
              return reply({
                ok: false,
                error: `${r.scene}: ${this.error?.message ?? "render failed"}`,
                line: this.error?.line ?? null,
              });
            }
          }
          const clips: Clip[] = [];
          let t = 0;
          for (const r of resolved) {
            const len = this.renders[sceneKey(r.file, r.scene)].duration;
            clips.push({ id: uid(), file: r.file, scene: r.scene, start: t, in: 0, out: len });
            t += len + gap;
          }
          this.clips = clips;
          this.viewerMode = "program";
          this.playhead = 0;
          this.persist();
          return reply({ ok: true, clips: clips.length, duration: Math.max(0, t - gap) });
        }
        default:
          return reply({ ok: false, error: `Unknown tool ${c.tool}` });
      }
    } catch (e) {
      return reply({ ok: false, error: String((e as { message?: string }).message ?? e) });
    }
  }

  // ------------------------------------------------------------ persistence
  persist() {
    clearTimeout(this.#saveTimer);
    const dir = this.dir;
    if (!dir) return;
    this.#saveTimer = setTimeout(() => {
      const rel = (p: string) => (p.toLowerCase().startsWith(dir.toLowerCase()) ? p.slice(dir.length).replace(/^[\\/]+/, "") : p);
      const data = {
        version: 2,
        aspect: this.aspect,
        clips: this.clips.map((c) => ({ ...c, file: rel(c.file) })),
        audio: this.audio.map((a) => ({ ...a, path: rel(a.path) })),
        captions: this.captions,
        renders: Object.fromEntries(Object.entries(this.renders).map(([k, r]) => [rel(k), r])),
      };
      this.#record();
      api.writeText(joinPath(dir, "project.json"), JSON.stringify(data, null, 2));
    }, 400);
  }

  loadTimeline(raw: unknown) {
    const data = raw as {
      clips?: Clip[];
      audio?: AudioClip[];
      captions?: Caption[];
      renders?: Record<string, Render>;
      aspect?: Aspect;
    } | null;
    this.aspect = ASPECTS.some((a) => a.id === data?.aspect) ? data!.aspect! : "16:9";
    this.captions = data?.captions ?? [];
    if (!data || !this.dir) {
      this.#resetHistory();
      return;
    }
    const abs = (name: string) => (/^[a-z]:[\\/]/i.test(name) ? name : joinPath(this.dir!, name));
    this.clips = (data.clips ?? []).map((c) => ({ ...c, file: abs(c.file) }));
    this.audio = (data.audio ?? []).map((a) => ({ ...a, path: abs(a.path) }));
    this.renders = Object.fromEntries(Object.entries(data.renders ?? {}).map(([k, r]) => [abs(k), r]));
    for (const a of this.audio) this.loadWaveform(a.path);
    this.#resetHistory();
  }
}

export const studio = new Studio();
