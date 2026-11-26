/** User preferences, saved in localStorage and applied live. */

export type Accent = "blue" | "teal" | "green" | "yellow" | "purple" | "red";

export const ACCENTS: Record<Accent, { color: string; ink: string; label: string }> = {
  blue: { color: "#58c4dd", ink: "#0c2a33", label: "Manim blue" },
  teal: { color: "#5cd0b3", ink: "#0b2a22", label: "Teal" },
  green: { color: "#83c167", ink: "#16290d", label: "Green" },
  yellow: { color: "#f4d345", ink: "#2e2604", label: "Yellow" },
  purple: { color: "#b39ddb", ink: "#221a33", label: "Purple" },
  red: { color: "#fc6255", ink: "#330f0c", label: "Red" },
};

export type Settings = {
  // Interface
  uiScale: number; // percent
  /** Which panel sits in the middle of the editor: the code/assistant or the preview. */
  editorLayout: "code-center" | "preview-center";
  /** Where the Project / Chats panel sits. */
  sidebarSide: "left" | "right";
  /** A panel that runs the full height of the window, with the timeline beside it instead of under it. */
  fullHeight: "none" | "project" | "code";
  /** Project tab: scenes and audio each as a grid of previews or a compact list. */
  sceneView: "grid" | "list";
  audioView: "grid" | "list";
  accent: Accent;
  reduceMotion: boolean;
  openLastProject: boolean;
  confirmDelete: boolean;
  showStatusBar: boolean;
  /** Home page: play a project's or template's video after hovering its card. */
  hoverPreviews: boolean;
  // Code editor
  fontSize: number;
  fontFamily: string;
  lineHeight: number;
  tabSize: number;
  wordWrap: boolean;
  minimap: boolean;
  lineNumbers: boolean;
  ligatures: boolean;
  manimCompletions: boolean;
  stickyScroll: boolean;
  bracketColors: boolean;
  showWhitespace: boolean;
  /** Save the open file shortly after typing stops (does not render). */
  autoSave: boolean;
  // Assistant
  autoRenderAfterAssistant: boolean;
  multiSceneByDefault: boolean;
  showToolDetails: boolean;
  extraInstructions: string;
  // Rendering
  previewQuality: "fast" | "preview" | "draft" | "high";
  renderOnSave: boolean;
  disableCache: boolean;
  backgroundColor: string;
  /** Frame shape for new projects. */
  defaultAspect: "16:9" | "9:16" | "1:1" | "4:5" | "4:3" | "21:9";
  /** Non-16:9 frames: keep the whole 16:9 layout visible, or use the frame's own units. */
  frameFit: "fit" | "fill";
  // Export
  exportPreset: "draft" | "high" | "1440p" | "4k";
  exportQuality: "small" | "balanced" | "high";
  exportFolder: string;
  revealAfterExport: boolean;
  // Timeline
  snapping: boolean;
  defaultZoom: number;
  /** Deleting a video clip pulls the clips after it back to close the gap. */
  rippleDelete: boolean;
  followPlayhead: boolean;
  showFilmstrips: boolean;
};

export const DEFAULTS: Settings = {
  uiScale: 100,
  editorLayout: "code-center",
  sidebarSide: "left",
  fullHeight: "none",
  sceneView: "grid",
  audioView: "list",
  accent: "blue",
  reduceMotion: false,
  openLastProject: false,
  confirmDelete: true,
  showStatusBar: true,
  hoverPreviews: true,
  fontSize: 13.5,
  fontFamily: "'Cascadia Code', Consolas, monospace",
  lineHeight: 1.55,
  tabSize: 4,
  wordWrap: false,
  minimap: false,
  lineNumbers: true,
  ligatures: true,
  manimCompletions: true,
  stickyScroll: true,
  bracketColors: true,
  showWhitespace: false,
  autoSave: false,
  autoRenderAfterAssistant: true,
  multiSceneByDefault: true,
  showToolDetails: true,
  extraInstructions: "",
  previewQuality: "preview",
  renderOnSave: true,
  disableCache: false,
  backgroundColor: "#000000",
  defaultAspect: "16:9",
  frameFit: "fit",
  exportPreset: "high",
  exportQuality: "balanced",
  exportFolder: "",
  revealAfterExport: false,
  snapping: true,
  defaultZoom: 48,
  rippleDelete: false,
  followPlayhead: true,
  showFilmstrips: true,
};

export const FONT_FAMILIES = [
  { value: "'Cascadia Code', Consolas, monospace", label: "Cascadia Code" },
  { value: "'Cascadia Mono', Consolas, monospace", label: "Cascadia Mono (no ligatures)" },
  { value: "Consolas, monospace", label: "Consolas" },
  { value: "'JetBrains Mono', 'Cascadia Code', monospace", label: "JetBrains Mono (if installed)" },
  { value: "'Fira Code', 'Cascadia Code', monospace", label: "Fira Code (if installed)" },
];

const KEY = "mp.settings";

class SettingsStore {
  value = $state<Settings>({ ...DEFAULTS });
  open = $state(false);
  section = $state<string>("interface");

  constructor() {
    if (typeof localStorage === "undefined") return;
    try {
      this.value = { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") };
    } catch {
      this.value = { ...DEFAULTS };
    }
  }

  set<K extends keyof Settings>(key: K, v: Settings[K]) {
    this.value[key] = v;
    this.save();
  }

  save() {
    localStorage.setItem(KEY, JSON.stringify(this.value));
    this.apply();
  }

  reset(keys?: (keyof Settings)[]) {
    for (const k of keys ?? (Object.keys(DEFAULTS) as (keyof Settings)[])) {
      (this.value as Record<string, unknown>)[k] = DEFAULTS[k];
    }
    this.save();
  }

  show(section = "interface") {
    this.section = section;
    this.open = true;
  }

  /** Pushes interface settings into CSS. Editor/render settings are read where they are used. */
  apply() {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    const a = ACCENTS[this.value.accent] ?? ACCENTS.blue;
    root.style.setProperty("--accent", a.color);
    root.style.setProperty("--accent-ink", a.ink);
    root.style.setProperty("--accent-soft", hexToRgba(a.color, 0.14));
    root.style.zoom = String(this.value.uiScale / 100);
    root.classList.toggle("reduce-motion", this.value.reduceMotion);
  }

  /** CRF for the final encode (lower = better quality, bigger file). */
  crf() {
    return { small: 26, balanced: 20, high: 16 }[this.value.exportQuality];
  }
}

function hexToRgba(hex: string, alpha: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgb(${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255} / ${alpha})`;
}

export const settings = new SettingsStore();
